# Michito Watchdog Alert Dispatcher Runbook
*Document Version: 1.0 • Operations & Observability Protocol • November 2026*

This guide details how the Michito Watchdog system monitors pipeline events, alerts operations teams on critical errors, and announces business milestones in real time.

---

## 1. Overview & Channels

The Watchdog system (`WebhookAlertAdapter`) operates across two distinct Slack/Discord channels to separate high-priority operational emergencies from commercial business activity:

```text
                                 [ Michito Engine ]
                                          │
            ┌─────────────────────────────┴─────────────────────────────┐
            ▼                                                           ▼
[ Operational Events & Failures ]                           [ Commercial Milestones ]
  • Missing Deliverables on Paid Orders                       • New Order Placed
  • Zero Qualified Leads / Registry Outages                   • Leads Ready & Awaiting Payment
  • Dead-Lettered Queue Retries (DLQ)                         • Wompi Payment Confirmed
  • Webhook Signature Tampering                               • 2x1 Replacement Lead Issued
            │                                                           │
            ▼                                                           ▼
[ ALERT_WEBHOOK_URL ]                                       [ ORDERS_FEED_WEBHOOK_URL ]
Channel: #michito-alerts                                    Channel: #michito-orders-feed
Severity: CRITICAL / WARNING                                Severity: INFO / SUCCESS
```

---

## 2. Event Types & Triggers

### Channel: `#michito-alerts` (Operational Emergencies)

| Event Trigger | Severity | Message Format | Operator Action |
| :--- | :--- | :--- | :--- |
| **Missing Deliverable on Download** | `ERROR` | `[ERROR] MISSING DELIVERABLE DOWNLOAD ATTEMPT: Buyer attempted to download {file_type} for paid order {order_id}, but file was not found in bucket.` | Immediate: Check worker logs, inspect Cloud Storage folder, run `./scripts/rerun_order.sh {order_id}` if needed. |
| **0 Qualified Leads Generated** | `WARNING` | `[WARNING] Order Failed - 0 Qualified Leads: Order {order_id} yielded 0 leads: No se encontraron prospectos que superaran los filtros.` | Investigate if SECOP II or SODA Socrata API was unreachable or if CIIU filter was overly restrictive. |
| **Invalid Payment Webhook Signature** | `WARNING` | `[WARNING] Invalid Wompi webhook signature received.` | Check if `WOMPI_EVENTS_SECRET` is out of sync or if unauthorized entity is probing the webhook. |
| **Database Pool Exhaustion** | `CRITICAL` | `[CRITICAL] OperationalError: too many connections.` | Increase PostgreSQL instance sizing or check for leaked SQLAlchemy sessions. |

### Channel: `#michito-orders-feed` (Business Milestones)

| Event Trigger | Format in Slack | Purpose |
| :--- | :--- | :--- |
| **New Order Placed** | `New Order Placed: Order {order_id} placed by {name} ({email}). Limit: {limit}, Tier: {tier}` | Real-time commercial pipeline visibility. |
| **Leads Ready & Awaiting Payment** | `Leads Ready & Awaiting Payment: Order {order_id} finished processing in {elapsed}s. {qualified} qualified leads generated. Total Quote: ${quote} COP` | Sales team alert to follow up with buyer if unpaid after 2 hours. |
| **Wompi Payment Confirmed** | `Wompi Payment Confirmed: Webhook verified! Order {order_id} paid. Deliverables unlocked for {name}.` | Instant payment notification; confirms revenue collection. |
| **2x1 Lead Replacement Claimed** | `Replacement Lead Issued: Buyer claimed 1 hard bounce on {order_id}. 2 replacement leads generated and added to manifest.` | Customer service assurance. |

---

## 3. Configuration & Secrets

Watchdog webhooks are configured via environment variables or mounted from Google Secret Manager:

```bash
# Critical operational alerts
ALERT_WEBHOOK_URL="https://hooks.slack.com/services/T00/B00/XXXXX"

# Commercial order feed
ORDERS_FEED_WEBHOOK_URL="https://hooks.slack.com/services/T00/B00/YYYYY"
```

If `ORDERS_FEED_WEBHOOK_URL` is omitted, commercial feed events automatically fall back to `ALERT_WEBHOOK_URL` so no events are lost.

---

## 4. Fail-Safe Principle

The Watchdog adapter wraps all network operations in broad exception handlers. If Slack or Discord is experiencing downtime, **the core prospecting engine and payment processing will never fail or raise an unhandled exception**. All events are simultaneously written to container `stdout` for permanent capture in Google Cloud Logging.
