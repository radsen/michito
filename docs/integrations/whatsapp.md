# Meta WhatsApp Cloud API Integration Runbook
*Document Version: 1.0 • Omnichannel Outbound & Webhook Protocol • November 2026*

This guide details how Michito connects to the Meta WhatsApp Cloud API for conversational lead generation, delivery dispatches, and 1-click RFQ quote generation.

---

## 1. Overview & Endpoints

Michito exposes two endpoints to interface with Meta's WhatsApp Cloud API:

- **`GET /api/v1/webhooks/whatsapp`**: Webhook verification challenge (Hub verification).
- **`POST /api/v1/webhooks/whatsapp`**: Inbound message intake, brief parsing, and status notifications.

---

## 2. Inbound Message Intake & Auto-Quoting

When a prospective buyer sends a WhatsApp message (e.g. *"Necesito 50 contactos de empresas de logística en Bogotá"*):

1. Meta posts the payload to `POST /api/v1/webhooks/whatsapp`.
2. The endpoint decodes the sender phone number and message text.
3. The `BriefParserService` extracts target CIIU codes, city, tier, and requested leads.
4. Generates an instant prospecting order and returns a quote summary.

---

## 3. Configuration & Webhook Verification

```bash
# Verification token configured in Meta App Dashboard
WHATSAPP_VERIFY_TOKEN="michito_wa_token"

# Meta App Secret for SHA-256 HMAC signature verification (Track E)
WHATSAPP_APP_SECRET="YOUR_META_APP_SECRET"

# Outbound sender phone ID and bearer token
WHATSAPP_PHONE_NUMBER_ID="100000000000000"
WHATSAPP_API_TOKEN="EAA..."
```

### Verification Challenge (GET)

When configuring the webhook in the Meta Developer Portal, Meta sends:
`GET /api/v1/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=michito_wa_token&hub.challenge=1158201444`

The endpoint validates `hub.verify_token` against `WHATSAPP_VERIFY_TOKEN` and responds with the `hub.challenge` string in plain text with HTTP 200.

---

## 4. Security: HMAC SHA-256 Verification (Track E)

Before production launch, all incoming `POST` requests from Meta must be validated against the `X-Hub-Signature-256` header:

$$\text{signature} = \text{HMAC-SHA256}(\text{raw\_body}, \text{WHATSAPP\_APP\_SECRET})$$

Requests failing signature verification are rejected with `401 Unauthorized` to prevent spoofed message injection.
