"""
Michito Watchdog & Operator Alert Dispatcher.
Dispatches critical operational alerts (Dead-Lettered Orders, SECOP API outages,
Payment reconciliation failures) to Discord, Slack, or generic HTTP Webhooks.
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)


class WebhookAlertAdapter:
    """
    Outbound Alert Dispatcher supporting Discord, Slack, and generic webhook endpoints.
    Fails safely without raising exceptions to protect pipeline continuity.
    """

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.environ.get("ALERT_WEBHOOK_URL", "")

    def send_alert(
        self,
        title: str,
        message: str,
        level: str = "error",
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Dispatches an alert to the configured webhook URL.
        Logs to system logger and stdout in all cases.
        """
        now = datetime.now(timezone.utc)
        payload_details = details or {}
        order_id = payload_details.get("order_id", "N/A")
        client_email = payload_details.get("client_email", "N/A")
        error_info = payload_details.get("error", "No additional details")

        # 1. Always log locally for cloud observability (Cloud Logging / stdout)
        log_line = f"🚨 [WatchdogAlert] [{level.upper()}] {title} | Order: {order_id} | Client: {client_email} | Message: {message} | Error: {error_info}"
        if level.lower() in ("critical", "error"):
            logger.error(log_line)
        else:
            logger.warning(log_line)

        if not self.webhook_url:
            return False

        # 2. Format payload for destination provider
        try:
            if "discord.com" in self.webhook_url:
                color_code = 15158332 if level.lower() in ("critical", "error") else 16753920
                payload = {
                    "username": "Michito Watchdog",
                    "embeds": [
                        {
                            "title": f"🚨 {title}",
                            "description": message,
                            "color": color_code,
                            "fields": [
                                {"name": "Order ID", "value": str(order_id), "inline": True},
                                {"name": "Client", "value": str(client_email), "inline": True},
                                {"name": "Retries", "value": str(payload_details.get("retry_count", 0)), "inline": True},
                                {"name": "Error Details", "value": str(error_info)[:800], "inline": False},
                            ],
                            "footer": {"text": "Michito B2B Reliability Engine • Cloud Run"},
                            "timestamp": now.isoformat(),
                        }
                    ],
                }
            elif "slack.com" in self.webhook_url:
                payload = {
                    "text": (
                        f"🚨 *[{level.upper()}] {title}*\n"
                        f"*Order*: `{order_id}` | *Client*: `{client_email}`\n"
                        f"*Summary*: {message}\n"
                        f"```{str(error_info)[:500]}```"
                    )
                }
            else:
                # Generic JSON Webhook (Zapier, Make, Telegram forwarder, custom API)
                payload = {
                    "event": "michito.watchdog.alert",
                    "timestamp": now.isoformat(),
                    "level": level,
                    "title": title,
                    "message": message,
                    "details": payload_details,
                }

            # 3. Fire HTTP POST with short timeout
            res = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=3.5,
            )
            return res.status_code in (200, 201, 204)
        except Exception as e:
            logger.warning(f"[WatchdogAlert] Failed to dispatch webhook alert to {self.webhook_url}: {e}")
            return False
