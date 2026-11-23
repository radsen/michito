"""
Michito Watchdog & Operator Alert Dispatcher.
Dispatches critical operational alerts (Dead-Lettered Orders, SECOP API outages,
Payment reconciliation failures) to #michito-alerts, and business activity
(new orders, lead delivery, approved payments) to #michito-orders-feed.
Supports Discord, Slack, and generic HTTP Webhooks.
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

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        feed_webhook_url: Optional[str] = None,
    ):
        self.webhook_url = webhook_url or os.environ.get("ALERT_WEBHOOK_URL", "")
        self.feed_webhook_url = feed_webhook_url or os.environ.get("ORDERS_FEED_WEBHOOK_URL", "")

    def send_alert(
        self,
        title: str,
        message: str,
        level: str = "error",
        details: Optional[Dict[str, Any]] = None,
        target_url: Optional[str] = None,
    ) -> bool:
        """
        Dispatches a high-priority operational alert (defaults to ALERT_WEBHOOK_URL / #michito-alerts).
        Logs to system logger and stdout in all cases.
        """
        dest_url = target_url or self.webhook_url
        now = datetime.now(timezone.utc)
        payload_details = details or {}
        order_id = payload_details.get("order_id", "N/A")
        client_email = payload_details.get("client_email", "N/A")
        error_info = payload_details.get("error", "No additional details")

        # 1. Always log locally for cloud observability (Cloud Logging / stdout)
        log_line = f"[WatchdogAlert] [{level.upper()}] {title} | Order: {order_id} | Client: {client_email} | Message: {message} | Error: {error_info}"
        if level.lower() in ("critical", "error"):
            logger.error(log_line)
        else:
            logger.warning(log_line)

        if not dest_url:
            return False

        # 2. Format payload for destination provider with explicit Environment & Priority classification
        raw_env = (os.environ.get("ENVIRONMENT") or "development").upper()
        if raw_env in ("PROD", "PRODUCTION"):
            env_tag = "[PROD • SUPER HIGH PRIORITY]"
            priority_tag = "P0 - CRITICAL" if level.lower() in ("critical", "error") else "P1 - HIGH"
        elif raw_env == "STAGING":
            env_tag = "[STAGING • TEST/QA]"
            priority_tag = "P2 - STAGING"
        else:
            env_tag = "[DEV • LOCAL WORKSTATION]"
            priority_tag = "P3 - DEV TEST"

        try:
            if "discord.com" in dest_url:
                color_code = 15158332 if level.lower() in ("critical", "error") else 16753920
                payload = {
                    "username": "Michito Watchdog",
                    "embeds": [
                        {
                            "title": f"[{raw_env}] [ALERT] {title}",
                            "description": message,
                            "color": color_code,
                            "fields": [
                                {"name": "Environment", "value": raw_env, "inline": True},
                                {"name": "Priority", "value": priority_tag, "inline": True},
                                {"name": "Order ID", "value": str(order_id), "inline": True},
                                {"name": "Client", "value": str(client_email), "inline": True},
                                {"name": "Retries", "value": str(payload_details.get("retry_count", 0)), "inline": True},
                                {"name": "Error Details", "value": str(error_info)[:800], "inline": False},
                            ],
                            "footer": {"text": f"Michito B2B Reliability Engine • {raw_env}"},
                            "timestamp": now.isoformat(),
                        }
                    ],
                }
            elif "slack.com" in dest_url:
                payload = {
                    "text": (
                        f"*{env_tag} [{priority_tag}] {title}*\n"
                        f"*Environment*: `{raw_env}` | *Level*: `{level.upper()}`\n"
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
                    "environment": raw_env,
                    "priority": priority_tag,
                    "level": level,
                    "title": title,
                    "message": message,
                    "details": payload_details,
                }

            # 3. Fire HTTP POST with short timeout
            res = requests.post(
                dest_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=3.5,
            )
            return res.status_code in (200, 201, 204)
        except Exception as e:
            logger.warning(f"[WatchdogAlert] Failed to dispatch webhook alert to {dest_url}: {e}")
            return False

    def send_feed_event(
        self,
        title: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Dispatches commercial order milestone events (New Order, Leads Delivered, Payment Approved)
        to the #michito-orders-feed channel (or fallback to ALERT_WEBHOOK_URL).
        """
        dest_url = self.feed_webhook_url or self.webhook_url
        now = datetime.now(timezone.utc)
        payload_details = details or {}
        order_id = payload_details.get("order_id", "N/A")

        raw_env = (os.environ.get("ENVIRONMENT") or "development").upper()
        if raw_env in ("PROD", "PRODUCTION"):
            env_badge = "[PROD]"
            env_label = "Production"
        elif raw_env == "STAGING":
            env_badge = "[STAGING]"
            env_label = "Staging / QA"
        else:
            env_badge = "[DEV]"
            env_label = "Local / Development"

        log_line = f"[OrdersFeed] [{raw_env}] {title} | Order: {order_id} | Message: {message}"
        logger.info(log_line)

        if not dest_url or os.environ.get("ENVIRONMENT") == "test" or os.environ.get("TESTING") == "1":
            return False

        try:
            if "slack.com" in dest_url:
                # Clean, rich Slack formatting for business events
                fields_str = f"• *Environment*: `{raw_env}` ({env_label})\n"
                if payload_details:
                    for k, v in payload_details.items():
                        if k != "raw" and v is not None:
                            k_clean = k.replace("_", " ").title()
                            fields_str += f"• *{k_clean}*: {v}\n"

                body_text = f"*{env_badge} {title}*\n{message}"
                if fields_str:
                    body_text += f"\n{fields_str.strip()}"

                payload = {"text": body_text}
            elif "discord.com" in dest_url:
                color_code = 3066993 if raw_env in ("PROD", "PRODUCTION") else 3447003
                payload = {
                    "username": "Michito Orders Feed",
                    "embeds": [
                        {
                            "title": f"[{raw_env}] {title}",
                            "description": message,
                            "color": color_code,
                            "fields": [
                                {"name": "Environment", "value": f"`{raw_env}`", "inline": True},
                                *[
                                    {"name": k.replace("_", " ").title(), "value": str(v), "inline": True}
                                    for k, v in payload_details.items()
                                    if k != "raw" and v is not None
                                ],
                            ],
                            "footer": {"text": f"Michito Feed • {raw_env}"},
                            "timestamp": now.isoformat(),
                        }
                    ],
                }
            else:
                payload = {
                    "event": "michito.orders.feed",
                    "timestamp": now.isoformat(),
                    "environment": raw_env,
                    "title": f"[{raw_env}] {title}",
                    "message": message,
                    "details": payload_details,
                }

            res = requests.post(
                dest_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=3.5,
            )
            return res.status_code in (200, 201, 204)
        except Exception as e:
            logger.warning(f"[OrdersFeed] Failed to dispatch feed event to {dest_url}: {e}")
            return False

    def send_financial_alert(
        self,
        order_id: str,
        client_email: str,
        query: str,
        location_display: str,
        status: str,
        gross_revenue_cop: float,
        variable_costs: Dict[str, float],
        yield_count: int,
        audit_rating: str,
        token_counts: Optional[Dict[str, int]] = None,
        currency: str = "COP",
    ) -> bool:
        """
        Dispatches unit economics and profitability audit events to #michito-alerts.
        Calculates: Gross Revenue - Total Variable Cost = Net Contribution Margin.
        """
        dest_url = self.webhook_url
        now = datetime.now(timezone.utc)
        raw_env = (os.environ.get("ENVIRONMENT") or "development").upper()

        total_variable_cost_cop = sum(variable_costs.values())
        net_margin_cop = gross_revenue_cop - total_variable_cost_cop
        margin_pct = (net_margin_cop / gross_revenue_cop * 100) if gross_revenue_cop > 0 else (0.0 if total_variable_cost_cop == 0 else -100.0)

        # Country flag mapping
        c_flag = "🇨🇴"
        if "republica dominicana" in location_display.lower() or "santo domingo" in location_display.lower() or " DO" in location_display:
            c_flag = "🇩🇴"
        elif "ecuador" in location_display.lower() or "quito" in location_display.lower() or "guayaquil" in location_display.lower() or " EC" in location_display:
            c_flag = "🇪🇨"

        cost_breakdown_lines = []
        for cost_key, cost_val in variable_costs.items():
            label = cost_key.replace("_cop", "").replace("_", " ").title()
            cost_breakdown_lines.append(f"• {label}: ${cost_val:,.2f} COP")

        cost_breakdown_text = "\n".join(cost_breakdown_lines)

        summary_text = (
            f"[{raw_env}] [FINANCIAL AUDIT] Order `{order_id}` {c_flag}\n"
            f"• Query: \"{query}\"\n"
            f"• Location: {location_display}\n"
            f"• Verified Yield: {yield_count} qualified leads\n"
            f"• Order Status: {status}\n\n"
            f"FINANCIAL BREAKDOWN ({currency}):\n"
            f"• Gross Revenue: ${gross_revenue_cop:,.0f} COP\n"
            f"{cost_breakdown_text}\n"
            f"----------------------------------------\n"
            f"• Total Variable Cost: ${total_variable_cost_cop:,.2f} COP\n"
            f"• Net Margin: ${net_margin_cop:,.2f} COP ({margin_pct:.1f}%)\n"
            f"• Audit Rating: {audit_rating}"
        )

        logger.info(f"[FinancialAlert] [{audit_rating}] Order: {order_id} | Revenue: ${gross_revenue_cop:,.0f} | Cost: ${total_variable_cost_cop:,.2f} | Margin: ${net_margin_cop:,.2f} ({margin_pct:.1f}%)")

        if not dest_url or os.environ.get("ENVIRONMENT") == "test" or os.environ.get("TESTING") == "1":
            return False

        try:
            if "discord.com" in dest_url:
                color_code = 3066993 if "PROFITABLE" in audit_rating else (16753920 if "LOW MARGIN" in audit_rating else 15158332)
                payload = {
                    "username": "Michito Financial Watchdog",
                    "embeds": [
                        {
                            "title": f"[{raw_env}] [FINANCIAL AUDIT] {audit_rating} {c_flag}",
                            "description": f"Order `{order_id}` • {client_email}",
                            "color": color_code,
                            "fields": [
                                {"name": "Query", "value": (query)[:250], "inline": False},
                                {"name": "Location / Yield", "value": f"{location_display} ({yield_count} leads)", "inline": True},
                                {"name": "Status", "value": status, "inline": True},
                                {"name": "Gross Revenue", "value": f"${gross_revenue_cop:,.0f} COP", "inline": True},
                                {"name": "Total Variable Cost", "value": f"${total_variable_cost_cop:,.2f} COP", "inline": True},
                                {"name": "Net Contribution Margin", "value": f"${net_margin_cop:,.2f} COP ({margin_pct:.1f}%)", "inline": True},
                                {"name": "Cost Detail", "value": cost_breakdown_text[:1000] if cost_breakdown_text else "None", "inline": False},
                            ],
                            "footer": {"text": f"Michito Unit Economics • {raw_env}"},
                            "timestamp": now.isoformat(),
                        }
                    ],
                }
            elif "slack.com" in dest_url:
                payload = {"text": summary_text}
            else:
                payload = {
                    "event": "michito.financial.audit",
                    "timestamp": now.isoformat(),
                    "environment": raw_env,
                    "order_id": order_id,
                    "client_email": client_email,
                    "query": query,
                    "location": location_display,
                    "yield_count": yield_count,
                    "gross_revenue_cop": gross_revenue_cop,
                    "variable_costs": variable_costs,
                    "total_variable_cost_cop": total_variable_cost_cop,
                    "net_margin_cop": net_margin_cop,
                    "margin_percentage": margin_pct,
                    "audit_rating": audit_rating,
                }

            res = requests.post(
                dest_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=3.5,
            )
            return res.status_code in (200, 201, 204)
        except Exception as e:
            logger.warning(f"[FinancialAlert] Failed to dispatch financial alert: {e}")
            return False
