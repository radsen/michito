# International Payments Architecture & Roadmap (Stripe / dLocal)
*Document Version: 1.0 • Cross-Border Monetization Strategy • November 2026*

This specification outlines the technical roadmap for adding international payment processing (USD, EUR) alongside Wompi (COP) to support buyers across Latin America, the United States, and Europe.

---

## 1. Business Context & Currency Routing

While Wompi is the premier gateway for Colombia 🇨🇴 (handling COP transactions with Bancolombia, PSE, and local credit cards with zero cross-border FX fees), buyers from Ecuador 🇪🇨 (USD economy), the Dominican Republic 🇩🇴 (DOP / USD), and international corporate clients require standard international processing.

### Dynamic Gateway Routing Strategy

```text
[ Client Checkout ]
         │
         │ Evaluates Order Currency & Country Code
         ▼
 ┌───────────────────────┬───────────────────────┐
 │ Country == "CO"       │ Country in ("EC",     │
 │ or Currency == "COP"  │ "DO", "US", "GLOBAL") │
 │                       │ or Currency in        │
 │                       │ ("USD", "EUR")        │
 ▼                       ▼
[ Wompi Gateway ]       [ Stripe / dLocal ]
 • Bancolombia Transfer  • Visa / Mastercard (Intl)
 • PSE Bank Debit        • American Express
 • Nequi                 • Apple Pay / Google Pay
 • Local Cards (COP)     • Local LatAm Rails (dLocal)
```

---

## 2. Planned Architecture (Clean Architecture Ports)

To maintain clean separation of concerns, the existing `PaymentGatewayPort` interface will be implemented by a unified `MultiGatewayPaymentAdapter`:

```python
# backend/src/application/ports/payment_gateway_port.py

class PaymentGatewayPort(ABC):
    @abstractmethod
    def create_checkout_session(self, order_id: str, amount_cents: int, currency: str, client: Dict) -> Dict:
        pass

    @abstractmethod
    def verify_webhook_signature(self, payload: bytes, signature_header: str) -> bool:
        pass
```

### Planned Gateways

1. **Stripe Checkout**:
   - Primary gateway for international credit cards (USD, EUR).
   - Enables Apple Pay, Google Pay, and Link with 1-click checkout.
   - Webhook endpoint: `POST /api/v1/webhooks/stripe`.
2. **dLocal Go / Enterprise**:
   - Secondary gateway for alternative local payment rails across Latin America (Ecuador Banco Pichincha, Dominican Republic Pagos Móviles).
   - Webhook endpoint: `POST /api/v1/webhooks/dlocal`.

---

## 3. Implementation Checklist for Launch

- [ ] Create Stripe merchant account under Chiketto corporate legal entity.
- [ ] Implement `StripePaymentAdapter` adhering to `PaymentGatewayPort`.
- [ ] Add `STRIPE_PUBLIC_KEY`, `STRIPE_SECRET_KEY`, and `STRIPE_WEBHOOK_SECRET` to Google Secret Manager.
- [ ] Implement `POST /api/v1/webhooks/stripe` with `stripe.Webhook.construct_event`.
- [ ] Update `WompiCheckoutModal.tsx` into a universal `PaymentCheckoutModal.tsx` that dynamically mounts the Stripe Elements SDK when USD is selected.
- [ ] Test sandbox card numbers (`4242 4242 4242 4242`) on international orders.
