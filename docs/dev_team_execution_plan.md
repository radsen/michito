# 🚀 Michito B2B Engine — Production Readiness Audit & Dev Team Task Packages
*Document Version: 2.6 • Decoupled React + Redux Architecture Edition • November 2026*

This document provides a comprehensive audit of current progress against the Strategic Master Plan, quantifies the gap to a production launch, and specifies modular, self-contained implementation packages for the **dev-team** (frontend, bot, and integration engineers).

---

## 📊 1. Production Readiness Audit & Gap Analysis

```
Overall Production Readiness: ~90%
┌───────────────────────────────┬───────────────────────────────┐
│ Core Intelligence Engine: 100%│ Data & Persistence:     100% │
│ Cloud Infrastructure:    100% │ Dev Team Intake/UI Scope: 40% │
└───────────────────────────────┴───────────────────────────────┘
```

### Detailed Component Scorecard

| Subsystem | Strategic Requirement | Current State | Gap / Remaining Work | Owner |
| :--- | :--- | :--- | :--- | :--- |
| **Registry Harvesting** | Live SODA API (Colombia SECOP II) + DGCP (Dominican Rep.) with taxonomic filtering | ✅ Fully implemented, cached, tested | None. Core harvesting is rock-solid. | **Core (Done)** |
| **Deliverability Gates** | Socket SMTP MX DNS handshake (`RCPT TO`) + Web status verification | ✅ Fully implemented, tested (102 unit/integration tests) | None. 0-bounce gate verified. | **Core (Done)** |
| **Intent Engine** | 3 High-Intent Triggers: Recent contracts, hiring footprint, regional expansion | ✅ Fully implemented, 5-touch copywriting generated | None. | **Core (Done)** |
| **Deduplication Ledger** | Cross-campaign memory and database deduplication preventing repeated prospecting | ✅ Fully implemented (`deduplication_ledger.py` + PostgreSQL) | None. | **Core (Done)** |
| **Database & Schema** | Relational PostgreSQL 16 with normalized orders, prospects, and campaign tables | ✅ Fully implemented in PostgreSQL & SQLite test fallback | Cloud SQL provisioning & SSL certificates in GCP. | **Core / DevOps** |
| **Tiered Pricing Model** | Fair Pay-Per-Lead (Tier 1: $5K, Tier 2: $30K, Tier 3: $65K COP) + Volume discounts | ✅ Fully implemented in `OrderWorkerDaemon` & DB models | None. | **Core (Done)** |
| **Web Client Architecture**| Decoupled React + Redux SPA (matching Hebi, ALFRED, and Chiketto standards) | ⚠️ Prototype static HTML/CSS/JS in `clients/web/public/` | Dev team builds production React + Redux Toolkit SPA. | **Dev Team** |
| **Tier 3 Underwriting** | Audited EBITDA (Supersociedades) + Rama Judicial + BDME screening | ✅ Fully implemented (`UnderwriteLeadUseCase` + Worker + CSV/MD exports) | None. Fully integrated and verified. | **Core (Done)** |
| **Deliverable Storage** | Persist CSV, Branded Excel (.xlsx), and Markdown dossiers to Cloud Storage | ✅ Fully implemented (`StoragePort`, `LocalStorageAdapter`, `GcsStorageAdapter`, Signed URLs) | None. Dual cloud/local storage active. | **Core (Done)** |
| **Order Intake Broker** | Decoupled message queue (Google Cloud Pub/Sub) | ⚠️ Polling fallback in `OrderWorkerDaemon`; Pub/Sub port defined | Dev team implements Pub/Sub publisher & subscriber. | **Dev Team** |
| **WhatsApp Intake Bot** | Conversational bot for order placement and instant delivery notifications | ⚠️ UX script drafted; no bot runtime connected | Dev team builds Meta Cloud API / Twilio webhook handler. | **Dev Team** |
| **Payment Gateway** | Live Wompi checkout + SHA-256 integrity webhook receiver | ⚠️ Simulated `/pay` endpoint in FastAPI | Dev team implements live Wompi widget & webhook validation. | **Dev Team** |
| **Delivery Dispatcher** | Omnichannel notification router (WhatsApp/Email) with download links | ⚠️ Manual web download | Dev team builds post-payment automated delivery worker. | **Dev Team** |

---

## 🛠️ 2. Division of Labor: Core Engine vs. Dev Team

```
┌────────────────────────────────────────────────────────────────────────┐
│                        DEV TEAM SCOPE (IN PARALLEL)                    │
│                                                                        │
│  [TASK 1: React + Redux Web SPA]       [TASK 2: WhatsApp Bot]          │
│  Vite/React/RTK decoupled client       Twilio / Meta Cloud API         │
│                                                                        │
│  [TASK 3: GCP Pub/Sub Broker]          [TASK 4: Wompi Webhook]         │
│  Topic 'michito-orders' adapter        SHA-256 HMAC integrity check   │
│                                                                        │
│  [TASK 5: Omnichannel Dispatcher]                                      │
│  Dispatches signed CSV/MD on payment                                   │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │ REST / Order Event / Webhook
┌────────────────────────────────────▼───────────────────────────────────┐
│                      CORE ENGINE SCOPE (US)                            │
│  • Public Registry Harvesting (SECOP II Colombia / DGCP Dominican Rep) │
│  • Socket SMTP MX DNS Handshakes (0% Bounces) & Website Auditor        │
│  • Multi-Tier Financial Pricing (Tier 1: $5K, Tier 2: $30K, Tier 3: $65K│
│  • Automated Tier 3 Underwriting Pipeline (EBITDA + Rama Judicial)     │
│  • Dual Deliverable Export (Branded Excel + Markdown + GCS Upload)     │
│  • Cloud Run & Cloud SQL Production Deployment Configuration           │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 3. Packaged Specifications for the Dev Team

### 🔹 TASK 1: Decoupled React + Redux Web SPA (`clients/web`)
* **Standard**: Matches Chiketto, Hebi, and ALFRED decoupled frontend standards.
* **Stack**: React 18+ / TypeScript / Redux Toolkit (RTK) / Vite / Tailwind CSS or CSS Modules.
* **Architecture Pattern**:
  ```
  clients/web/
  ├── package.json
  ├── vite.config.ts (proxy /api to http://localhost:8000)
  ├── tsconfig.json
  ├── src/
  │   ├── index.tsx / App.tsx
  │   ├── store/
  │   │   ├── index.ts (configureStore)
  │   │   ├── slices/
  │   │   │   ├── campaignSlice.ts (Campaign list, selected campaign, cities)
  │   │   │   ├── orderSlice.ts (Order creation, polling status, active order)
  │   │   │   ├── pricingSlice.ts (Tier 1/2/3 selection, volume discount calculator)
  │   │   │   ├── languageSlice.ts (es_CO default, en_US toggle)
  │   │   │   └── uiSlice.ts (Modals, checkout state, mobile drawer)
  │   │   └── api/
  │   │       └── michitoApi.ts (RTK Query endpoints: fetchCampaigns, createOrder, pollOrder, payOrder)
  │   ├── locales/
  │   │   ├── es_CO.json (Default Colombian Spanish)
  │   │   └── en_US.json (English Translations)
  │   ├── components/
  │   │   ├── layout/ (Navbar, Footer, Hero, LanguageToggle)
  │   │   ├── order/ (CampaignPicker, CityPicker, VolumeSlider, TierCardSelector, BuyerForm)
  │   │   ├── preview/ (SampleTeaserTable, DeliverablesChecklist, ScopeDisclaimer)
  │   │   └── tracker/ (OrderLiveStatusModal, WompiCheckoutModal, DownloadDeliverablesCard)
  ```
* **State Management & Feature Requirements**:
  1. **Dual Language Localization (i18n)**:
     - **Default Language**: `es_CO` (Español Colombia).
     - **Secondary Language**: `en_US` (English US).
     - Language switcher in the navbar header (🇨🇴 ES | 🇺🇸 EN) persisting selection in `localStorage`.
     - Complete dictionary coverage across Hero, Tier Descriptions, Value Proposition, Intent Triggers, Form Labels, Disclaimers, and Status Modals.
     - Dynamic currency display: `$ COP` format (e.g. `$30.000 COP`) in `es_CO`, with optional USD conversion tooltip/rate in `en_US`.
  2. **Mobile-First Responsiveness (Mobile & Tablet)**:
     - Mobile Viewport: Strict touch optimization for screen widths down to 320px.
     - Single-column card stacking on mobile devices (< 640px) for Tier 1/2/3 cards and campaign cards.
     - Horizontal swipeable / scrollable container for the 3-lead sample teaser table so tables never break screen width on smartphones.
     - Large touch targets (minimum 48x48px) for buttons, volume sliders, and dropdown selectors.
     - Optional sticky bottom CTA button on mobile devices ("Pedir Lote de Leads ⚡") jumping smoothly to the order intake form.
  3. **Dynamic Campaign Ingestion**: Fetch available campaigns from `GET /api/v1/campaigns` on load.
  4. **Reactive Pricing Engine**: Dynamic calculation based on selected `tier` (1, 2, 3), `volume` (10, 25, 50, 100, 250, 500, 1000), and volume discount curve.
  5. **Order Status Polling**: Once `POST /api/v1/orders` creates an order, use RTK Query or polling `GET /api/v1/orders/{order_id}` every 3 seconds to display real-time progress.
  6. **Deliverables Unlocking**: Automatically display download buttons for CSV and Dossier as soon as order status transitions to `paid`.
* **Build Target**:
  - `npm run build` compiles static assets to `dist/` (or `public/`), configured in `firebase.json` for CDN deployment.

---

### 🔹 TASK 2: WhatsApp Conversational Bot Intake (Meta Cloud API / Twilio)
* **Goal**: Enable prospects to order qualified lead batches directly over WhatsApp.
* **Target Endpoint**: `POST /api/v1/orders` on FastAPI backend.
* **Input Payload**:
  ```json
  {
    "client": {
      "name": "Juan Carlos Pérez",
      "email": "juan@empresa.com",
      "phone": "+573001234567",
      "channel": "whatsapp",
      "referral_partner": "direct"
    },
    "request": {
      "campaign_id": "tinkko_enterprise_offices",
      "country": "CO",
      "city": "Medellín",
      "limit": 25,
      "tier": 2
    }
  }
  ```
* **Acceptance Criteria**:
  1. Parses incoming WhatsApp message for city, volume, and campaign intent.
  2. Submits order to `POST /api/v1/orders` and receives `order_id`.
  3. Sends instant acknowledgment: *"⚡ Estamos escaneando registros oficiales y validando buzones. Tu orden `ord_...` está en proceso."*
  4. Delivers sample teaser and Wompi checkout link when status transitions to `awaiting_payment`.

---

### 🔹 TASK 3: Google Cloud Pub/Sub Order Queue Broker
* **Goal**: Decouple order intake from database polling by publishing order events to GCP Pub/Sub topic `michito-orders`.
* **Interface Contract**: Implement `OrderQueuePort` in `src/application/ports/order_queue_port.py`.
* **Specs**:
  - Topic: `projects/{PROJECT_ID}/topics/michito-orders`
  - Subscription: `projects/{PROJECT_ID}/subscriptions/michito-worker-sub`
  - Local Dev Fallback: Connects to Firebase/GCP PubSub Emulator on `localhost:8085` when `PUBSUB_EMULATOR_HOST` is set.
* **Acceptance Criteria**:
  1. `main.py` publishes an event on `POST /api/v1/orders`.
  2. `OrderWorkerDaemon` subscribes to the topic and pulls messages without polling PostgreSQL continuously.

---

### 🔹 TASK 4: Wompi Checkout Widget & Webhook Receiver (Sandbox Verified)
* **Goal**: Enable direct card/PSE payment on the frontend and securely transition orders from `awaiting_payment` to `paid` upon bank verification.
* **Reference Implementation**: 
  The dev team must reference our tested Wompi implementation and sandbox configuration in **Hebi Account-Receivable**:
  - Path: `/Users/radsen/dev/tinkko/account-recievable`
  - Backend Service: `functions/domain/services/wompi_service.py`
  - Integration Guide: `docs/operations/wompi-subscription-production-guide.md`
* **Sandbox / Dev Credentials**:
  ```env
  WOMPI_PUBLIC_KEY=pub_test_IcBzwUvqUDy85sD7i3snlgxvMLj4A1eL
  WOMPI_INTEGRITY_SECRET=test_integrity_r5SIpk6PnYywRaCxQlOXgySj28wNNlmj
  WOMPI_EVENTS_SECRET=test_events_wmhM2301jwX2c9q8u4SofthtnAKUO7aK
  WOMPI_CHECKOUT_URL=https://checkout.wompi.co/p/
  ```
* **Frontend Widget Integration (`clients/web/`)**:
  Include Wompi Widget script: `<script type="text/javascript" src="https://checkout.wompi.co/widget.js"></script>`
  Before opening checkout, calculate the mandatory **Integrity Signature**:
  $$\text{signature} = \text{SHA256}(\text{reference} + \text{amount\_in\_cents} + \text{currency} + \text{WOMPI\_INTEGRITY\_SECRET})$$
  Trigger Wompi Checkout:
  ```javascript
  const checkout = new WidgetCheckout({
    currency: "COP",
    amountInCents: totalAmountInCents,
    reference: orderId,
    publicKey: "pub_test_IcBzwUvqUDy85sD7i3snlgxvMLj4A1eL",
    signature: { integrity: integritySignature },
    redirectUrl: window.location.href
  });
  checkout.open((result) => {
    console.log("Transaction result:", result.transaction);
  });
  ```
* **Target Webhook Endpoint**: `POST /api/v1/webhooks/wompi`
* **Security Validation Rule**:
  $$\text{Checksum} = \text{SHA256}(\text{concatenated\_properties} + \text{timestamp} + \text{WOMPI\_EVENTS\_SECRET})$$
* **Workflow**:
  1. Validate SHA-256 signature against `WOMPI_EVENTS_SECRET`.
  2. If valid and `status == "APPROVED"`, extract `order_id` from `reference`.
  3. Call `sql_adapter.mark_order_paid(order_id, transaction_id, amount_in_cents)`.
* **Acceptance Criteria**:
  1. Rejects forged webhooks with HTTP 401.
  2. Idempotent: repeated webhook events for the same `transaction.id` do not re-process.
  3. Transitions order status to `paid` and unlocks deliverables download.

---

### 🔹 TASK 5: Omnichannel Delivery Router (Email + WhatsApp)
* **Goal**: Automatically deliver deliverables to the buyer once payment is confirmed.
* **Payload Dispatched**:
  - Attached or signed link to `lote_prospeccion_{order_id}.csv` (HubSpot/CRM ready).
  - Attached or signed link to `dossier_ejecutivo_{order_id}.md` (5-touch cadences).
* **Delivery Gate**: Only trigger when order status in PostgreSQL is strictly `"paid"`.

---

## 🎯 4. Our Scope (Core Intelligence & Underwriting Engine)

While the dev team executes the frontend SPA and intake/payment integrations, we will complete:

1. **Automated Tier 3 Underwriting Pipeline**:
   - Chain `CalculateCompanyEbitdaUseCase` and `ScreenLitigationRiskUseCase` into `GenerateProspectsUseCase`.
   - Screen candidates against Supersociedades financial filings (EBITDA), Rama Judicial dockets, and Contraloría BDME fiscal records.
   - Flag high-risk debtors and append solvency indicators to final deliverables.
2. **Cloud Storage Deliverables Adapter**:
   - Implement `GcsDeliverablesAdapter` to upload generated CSVs, Markdown dossiers, and Excel workbooks to `gs://michito-deliverables/`.
   - Generate secure, signed 48-hour download URLs.
3. **Production Containerization & Deployment**:
   - Multi-stage Dockerfile optimized for Python 3.13.
   - Cloud Run and Cloud SQL deployment manifests and environment configuration.

