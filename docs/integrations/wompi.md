# Wompi Gateway Integration & Testing Runbook
*Document Version: 1.0 • Payment Gateway Protocol • November 2026*

This guide details how Wompi is integrated into the Michito B2B Engine, how to configure sandbox and production merchant accounts, and how to execute end-to-end payment testing across Development, Staging, and Production environments.

---

## 1. Overview & Architecture

Wompi (Bancolombia) serves as the primary payment gateway for Colombia 🇨🇴, processing credit cards, debit cards, PSE (online bank transfers), and Bancolombia accounts.

### Payment Flow Diagram

```text
[ Buyer in Web App ]
         │
         │  1. Clicks "Pay with Wompi Gateway"
         ▼
[ WompiCheckoutModal.tsx ]
         │
         │  2. Calculates SHA-256 integrity signature:
         │     hash(reference + amountInCents + currency + integritySecret)
         │  3. Opens window.WidgetCheckout(checkoutConfig)
         ▼
[ Wompi Hosted Widget (Iframe) ]
         │
         │  4. Buyer completes payment (Card, PSE, Bancolombia, Nequi)
         │  5. Wompi backend processes transaction
         ▼
[ Wompi Payment Cloud ] ─────────── 6. Webhook POST /api/v1/webhooks/wompi ──────────┐
         │                                                                           │
         │ (Optional client callback)                                                ▼
         ▼                                                             [ Michito Cloud Run API ]
[ Web App (Staging/Prod) ]                                                           │
   • Transitions status to "paid"                                             7. Validates SHA-256 HMAC checksum
   • Unlocks 3 commercial deliverables                                        8. Marks order as 'paid' in PostgreSQL
     (XLSX, PDF Dossier, CRM CSV)                                             9. Dispatches omnichannel delivery
                                                                             10. Sends Watchdog alert to #michito-orders-feed
```

---

## 2. Sandbox Testing Matrix (Modo Pruebas)

When testing in **Development** or **Staging**, ensure your Wompi merchant portal ([https://comercios.wompi.co/](https://comercios.wompi.co/)) is toggled to **"Modo Pruebas"**.

### Test Cards & Bank Accounts

| Payment Method | Test Number / Details | Expiration & CVC | Expected Result | What Happens in Michito |
| :--- | :--- | :--- | :--- | :--- |
| **Visa / Mastercard (Approved)** | `4242 4242 4242 4242` | Expiry: Any future date (e.g. `12/28`)<br>CVC: `123`<br>Cuotas: `1`<br>Name: Any (e.g. Andrés Londoño) | **APPROVED** | Order status changes to `paid`. All 3 download buttons (XLSX, PDF, CSV) unlock instantly. Watchdog announces payment in Slack. |
| **Visa / Mastercard (Declined)** | `4242 4242 4242 4241` | Expiry: Future date<br>CVC: `123` | **DECLINED** | Widget displays card declined. Order remains in `awaiting_payment`. Deliverables stay locked. |
| **Visa / Mastercard (Insufficient Funds)** | `4000 0000 0000 0002` | Expiry: Future date<br>CVC: `123` | **DECLINED** | Widget displays insufficient funds. Order remains in `awaiting_payment`. |
| **Visa / Mastercard (Expired Card)** | `4000 0000 0000 0001` | Expiry: Any past date (e.g. `01/22`)<br>CVC: `123` | **DECLINED** | Widget prompts for a valid expiration date before submitting. |
| **Visa / Mastercard (High Risk / Fraud)** | `4000 0000 0000 0005` | Expiry: Future date<br>CVC: `123` | **ERROR** | Gateway rejects transaction due to risk score. |
| **PSE (Bank Debit / Transfer)** | Select bank: **"Banco Unión Colombiano"** (Sandbox bank) | Document Type: `CC`<br>Document: `1234567890`<br>Phone: Any 10-digit mobile<br>Email: Client email | **APPROVED** | Redirects to Wompi mock banking portal. Click **"Aprobar"** to simulate bank debit. Webhook arrives and unlocks files. |
| **Bancolombia Transfer (Botón)** | Select Bancolombia Sandbox Simulator | Follow on-screen sandbox instructions | **APPROVED** | Redirects to mock Bancolombia approval page. |
| **Nequi (Sandbox)** | Phone: `3991111111` | N/A | **APPROVED** | Simulates Nequi push notification approval. |

---

## 3. Environment Configuration

Wompi requires three environment keys plus the webhook configuration:

```bash
# Public Key (Safe for frontend bundle)
WOMPI_PUBLIC_KEY="pub_test_..."          # (In Prod: pub_prod_...)

# Integrity Secret (Used by frontend to sign transaction amount + reference)
WOMPI_INTEGRITY_SECRET="test_integrity_..." # (In Prod: prod_integrity_...)

# Events Secret (Used exclusively by backend API to verify webhook authenticity)
WOMPI_EVENTS_SECRET="test_events_..."       # (In Prod: prod_events_...)
```

### Environment Comparison

| Setting | Local / Development | Staging (`michito-staging`) | Production (`michito-prod`) |
| :--- | :--- | :--- | :--- |
| **Wompi Portal Mode** | Modo Pruebas | **Modo Pruebas** | **Modo Producción** |
| **Key Prefixes** | `pub_test_` / `test_...` | `pub_test_` / `test_...` | `pub_prod_` / `prod_...` |
| **Webhook URL** | `http://localhost:8000/api/v1/webhooks/wompi` (or ngrok) | `https://michito-api-limgi3puaq-uc.a.run.app/api/v1/webhooks/wompi` | `https://api.michito.co/api/v1/webhooks/wompi` |
| **Direct Dev Approval** | Enabled via `POST /api/v1/orders/{id}/pay` | **Disabled** (Blocked with `403 Forbidden`) | **Disabled** (Blocked with `403 Forbidden`) |
| **Real Money Charged** | No ($0) | No ($0) | **Yes (Real Bancolombia / PSE Funds)** |

---

## 4. Webhook Signature Verification Protocol

When Wompi confirms a payment, it sends an HTTP POST event to `/api/v1/webhooks/wompi`. 

### The Checksum Formula

To verify the event was genuinely sent by Wompi and not spoofed by an external actor, the backend computes the SHA-256 hash:

$$\text{raw\_string} = \text{tx\_id} + \text{status} + \text{amount\_in\_cents} + \text{timestamp} + \text{WOMPI\_EVENTS\_SECRET}$$

$$\text{expected\_checksum} = \text{SHA-256}(\text{raw\_string})$$

The backend checks this checksum against `event_data["signature"]["checksum"]` using constant-time comparison (`hmac.compare_digest`). If they do not match, the request is rejected with `401 Unauthorized`.

### Testing the Webhook via cURL (Developer Simulation)

You can simulate a verified Wompi webhook locally or against staging without using a credit card:

```bash
# 1. Define order parameters
ORDER_ID="ord_20261117_cd80b8"
AMOUNT_CENTS="240000000"
TX_ID="sim_tx_123456"
STATUS="APPROVED"
TIMESTAMP="1763484000"
EVENTS_SECRET="test_events_wmhM2301jwX2c9q8u4SofthtnAKUO7aK"

# 2. Compute SHA-256 checksum
RAW="${TX_ID}${STATUS}${AMOUNT_CENTS}${TIMESTAMP}${EVENTS_SECRET}"
CHECKSUM=$(echo -n "$RAW" | shasum -a 256 | awk '{print $1}')

# 3. Dispatch simulated webhook
curl -X POST "https://michito-api-limgi3puaq-uc.a.run.app/api/v1/webhooks/wompi" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "transaction.updated",
    "data": {
      "transaction": {
        "id": "'"$TX_ID"'",
        "amount_in_cents": '"$AMOUNT_CENTS"',
        "reference": "'"$ORDER_ID"'",
        "status": "'"$STATUS"'",
        "currency": "COP"
      }
    },
    "timestamp": '"$TIMESTAMP"',
    "signature": {
      "checksum": "'"$CHECKSUM"'"
    }
  }'
```

Expected response: `{"status": "received"}`.

---

## 5. Common Issues & Troubleshooting

### Issue 1: "Wompi Widget Error: Los siguientes parámetros obligatorios no están presentes: phoneNumberPrefix"
- **Cause**: Wompi requires `phoneNumberPrefix` (e.g. `"+57"`) whenever `phoneNumber` is supplied in `customerData`. If `phoneNumber` contains non-digit characters (e.g. `+57310...`), Wompi's validator rejects initialization.
- **Fix**: The frontend (`WompiCheckoutModal.tsx`) strips non-digits, extracts the prefix into `customerData.phoneNumberPrefix: "+57"`, and passes the 10-digit number in `customerData.phoneNumber`.

### Issue 2: "Signature integrity error" or Widget refuses to open
- **Cause**: Mismatch between `WOMPI_PUBLIC_KEY` and `WOMPI_INTEGRITY_SECRET`. The integrity secret used to hash the reference must belong to the exact merchant account owning the public key.
- **Fix**: Verify both keys match under **Desarrolladores** in the Wompi merchant portal.

### Issue 3: Order does not unlock after sandbox payment
- **Cause 1**: The Sandbox **URL de Eventos** in Wompi is empty or misconfigured.
  - **Resolution**: In [https://comercios.wompi.co/](https://comercios.wompi.co/) under **Desarrolladores**, ensure the URL de Eventos is set to:
    `https://michito-api-limgi3puaq-uc.a.run.app/api/v1/webhooks/wompi`.
- **Cause 2**: `WOMPI_EVENTS_SECRET` in Google Secret Manager does not match the merchant dashboard.
  - **Resolution**: Update the secret in Google Secret Manager and redeploy the API.
