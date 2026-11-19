# Michito Integrations Catalog & External Services Runbook
*Document Version: 1.0 • Universal Architecture & Cloud Integrations • November 2026*

This directory houses official integration specifications, sandbox testing guides, credential configurations, failure modes, and Watchdog runbooks for all third-party services powering the Michito B2B Engine.

---

## 1. External Integrations Matrix

| Service | Category | Territory / Scope | Dev / Local | Staging (`michito-staging`) | Production (`michito-prod`) | Status | Documentation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Wompi Gateway** | Payments & Checkout | Colombia 🇨🇴 | Sandbox / Direct Dev | Sandbox (Test Mode) | Live Commercial Gateway | Active | [wompi.md](file:///Users/radsen/dev/chiketto/michito/docs/integrations/wompi.md) |
| **Google Cloud Pub/Sub** | Asynchronous Broker | Global / Engine | In-Memory / PubSub Emulator | Cloud Run Push (`michito-orders-staging`) | Cloud Run Push (`michito-orders-prod`) | Active | [pubsub.md](file:///Users/radsen/dev/chiketto/michito/docs/integrations/pubsub.md) |
| **Google Cloud Storage** | Deliverable Artifacts | Global / Multi-Region | Local Disk / Emulator | `gs://michito-staging-deliverables` | `gs://michito-prod-deliverables` | Active | [gcs.md](file:///Users/radsen/dev/chiketto/michito/docs/integrations/gcs.md) |
| **Michito Watchdog (Slack)**| Observability & Alerts | Global / Operations | Standard Console / Stdout | Live Webhook (`#michito-alerts` / Feed) | Live Webhook (`#michito-alerts` / Feed) | Active | [watchdog.md](file:///Users/radsen/dev/chiketto/michito/docs/integrations/watchdog.md) |
| **Meta WhatsApp Cloud API** | Conversational Outbound | Colombia 🇨🇴 / Latin America | Local JSON simulation | Cloud Run Webhook (`/webhooks/whatsapp`)| Verified Meta Business Phone | Active | [whatsapp.md](file:///Users/radsen/dev/chiketto/michito/docs/integrations/whatsapp.md) |
| **SECOP II / SODA API** | Public Registry Harvester| Colombia 🇨🇴 | SODA Socrata API + Offline Fallback| Live SODA API with app token | Live SODA API with app token | Active | [secop_colombia.md](file:///Users/radsen/dev/chiketto/michito/docs/integrations/secop_colombia.md) |
| **DGCP Open Data** | Procurement Harvester | Dominican Republic 🇩🇴 | Portal API + Statutory Roster | Live DGCP Portal Harvester | Live DGCP Portal Harvester | Active | [secop_colombia.md](file:///Users/radsen/dev/chiketto/michito/docs/integrations/secop_colombia.md) |
| **SERCOP Open Data** | Public Registry Harvester| Ecuador 🇪🇨 | Portal API + Statutory Roster | Live SERCOP Portal Harvester | Live SERCOP Portal Harvester | Active | [secop_colombia.md](file:///Users/radsen/dev/chiketto/michito/docs/integrations/secop_colombia.md) |
| **Stripe / dLocal** | International Payments | Global (USD / EUR) | N/A (Planned) | N/A (Planned) | N/A (Planned) | Roadmap | [international_payments.md](file:///Users/radsen/dev/chiketto/michito/docs/integrations/international_payments.md) |

---

## 2. Standard Integration Architecture Principles

All external integrations in Michito strictly adhere to the following architecture standards:

1. **Clean Architecture Ports & Adapters**:
   - Every external third-party SDK or network client is isolated behind an application port interface in `backend/src/application/ports/` (e.g. `PaymentGatewayPort`, `OrderQueuePort`, `StoragePort`, `AlertDispatcherPort`).
   - Adapters in `backend/src/adapters/` provide concrete implementations. Business use cases never import third-party client libraries directly.
2. **Stateless Fail-Fast Decoupling**:
   - Heavy network operations (harvesting public registries, SMTP socket handshakes, file packaging) run asynchronously inside background workers, never on user-facing HTTP request threads.
   - If an external upstream API fails (e.g. SECOP II temporary maintenance), the engine gracefully degrades to internal verified statutory rosters without crashing or stalling client orders.
3. **Observability via Watchdog**:
   - Critical failures (e.g. invalid payment webhook signatures, missing deliverables on paid orders, upstream harvester outages) automatically alert the operations team in `#michito-alerts` before clients report an issue.
4. **Secret Management & Zero Hardcoding**:
   - No production API keys, event secrets, or credentials may be stored in source code.
   - In Google Cloud, secrets are mounted from Google Secret Manager (`SECRET_NAME:latest`) directly into Cloud Run container environment variables.

---

## 3. Directory Index

- [wompi.md](file:///Users/radsen/dev/chiketto/michito/docs/integrations/wompi.md) — Comprehensive guide to testing Wompi Sandbox, Cards, PSE, Bancolombia, and Webhook signatures.
- [pubsub.md](file:///Users/radsen/dev/chiketto/michito/docs/integrations/pubsub.md) — Pub/Sub push subscription topology, ack deadlines, order message schemas, and retry policies.
- [gcs.md](file:///Users/radsen/dev/chiketto/michito/docs/integrations/gcs.md) — Google Cloud Storage hierarchy, signed downloads, direct byte streaming, and file naming conventions.
- [watchdog.md](file:///Users/radsen/dev/chiketto/michito/docs/integrations/watchdog.md) — Watchdog alert dispatcher, Slack webhook structure, event severity levels, and orders feed.
- [whatsapp.md](file:///Users/radsen/dev/chiketto/michito/docs/integrations/whatsapp.md) — WhatsApp Meta Cloud API webhook verification, message intake, and automated RFQ quote parsing.
- [secop_colombia.md](file:///Users/radsen/dev/chiketto/michito/docs/integrations/secop_colombia.md) — Colombia SECOP II / SODA API configuration, caching, rate limiting, and statutory rosters.
- [international_payments.md](file:///Users/radsen/dev/chiketto/michito/docs/integrations/international_payments.md) — Strategic roadmap and planned technical architecture for Stripe / dLocal international billing.
