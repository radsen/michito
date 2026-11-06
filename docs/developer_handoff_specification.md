# Michito Engine — Developer Handoff Specification
**Asynchronous B2B Lead Intelligence & Order Monetization System**  
*Document Version:* 2.0 (Clean Architecture & Multi-Client Edition)  
*Audience:* Frontend Developers, WhatsApp Bot Engineers, Backend Integration Team  
*Status:* Ready for Implementation

---

## 1. Executive Architecture & Division of Labor

Michito is **not** a CRM. It is an **On-Demand B2B Lead Intelligence Engine** operating across Colombia and the Dominican Republic. It harvests public corporate registries (SECOP II, DGCP, RNC, RUES), filters through strict quality/deliverability gates (corporate domains, active websites, zero-bounce DNS MX, verified mobile phones), detects 3 high-intent expansion signals, and compiles personalized 5-touch omnichannel cadences.

To achieve maximum scale, lowest per-operation costs, and prevent database bottlenecking during high-volume spikes, the work is strictly partitioned:

```
┌────────────────────────────────────────────────────────┐
│                   DEV TEAM SCOPE                       │
│  [Client Web Portal]        [WhatsApp Conversational]  │
│          │                              │              │
│          ▼                              ▼              │
│  [Intake API / Webhook] ──► [Redis / Cloud PubSub]     │
│                                    │                   │
└────────────────────────────────────┼───────────────────┘
                                     │ (Job Event)
┌────────────────────────────────────┼───────────────────┐
│          US (ENGINE SCOPE)         ▼                   │
│                       [Order Worker Daemon]            │
│                                │                       │
│                ┌───────────────┴───────────────┐       │
│                ▼                               ▼       │
│     [Registry Harvester]             [Website Auditor] │
│     (SECOP II / DGCP)                (MX & Headless)   │
│                │                               │       │
│                └───────────────┬───────────────┘       │
│                                ▼                       │
│                   [Lead Scoring & Intent Engine]       │
│                   [Ledger Deduplication]               │
│                                │                       │
│                                ▼                       │
│              [Teaser & Deliverables Generated]         │
│          (Stored in Cloud Storage / Secure Volume)     │
└────────────────────────────────────┬───────────────────┘
                                     │ (Quote & Teaser)
┌────────────────────────────────────▼───────────────────┐
│                   DEV TEAM SCOPE                       │
│  [Wompi Payment Gateway] ◄── [Checkout URL Sent]       │
│          │                                             │
│          ▼ (Payment Approved Webhook)                  │
│  [Webhook Delivery Router] ──► [Sends CSV/MD to User]  │
└────────────────────────────────────────────────────────┘
```

### Responsibility Matrix

| Area | Owner | Detailed Deliverables |
| :--- | :--- | :--- |
| **Data & Intent Brain** | **Us** | • Public registry harvesting (SECOP II Colombia, DGCP Dominican Republic)<br>• DNS MX mailbox verification & website live auditing<br>• Intent triggers (Contracts won, hiring footprint, regional expansion)<br>• Deduplication ledger across campaigns<br>• 5-Touch copywriting & Executive dossier compilation<br>• Asynchronous `OrderWorkerDaemon` |
| **Intake Channels** | **Dev Team** | • Web order form (React / Next.js / Vue)<br>• WhatsApp Business Bot (Twilio / Meta Cloud API / Gupshup)<br>• Instant user acknowledgement ("Processing your lead batch...") |
| **Message Broker** | **Dev Team** | • Redis Queue (Celery / BullMQ) or Google Cloud Pub/Sub topic `michito-orders`<br>• Enqueues incoming order payloads without blocking user HTTP threads |
| **Payment & Checkout** | **Dev Team** | • Wompi Colombia widget or checkout redirection<br>• Webhook receiver for `transaction.updated`<br>• Wompi SHA-256 integrity signature validation |
| **Delivery & Notification**| **Dev Team** | • Delivers 3-account sample teaser + price quote<br>• Delivers final signed download links (CSV + Markdown) upon payment confirmation |

---

## 2. Multi-Client Supported Campaigns

The engine natively supports all 7 production campaign profiles. The intake API / WhatsApp bot must provide a selector or detect user intent corresponding to these `campaign_id` values:

| Campaign ID | Target Client / Offering | Target Country | Default Cities | Target B2B Sectors |
| :--- | :--- | :---: | :--- | :--- |
| `tinkko_enterprise_offices` | Tinkko Coworking & Private Enterprise Suites | 🇨🇴 CO | Medellín, Bogotá | Technology, Legal, Finance, Consulting, Shared Services |
| `tinkko_dr_offices` | Tinkko DR Corporate Office Hubs | 🇩🇴 DO | Santo Domingo, Santiago | Tech Providers, Corporate Services, Exporters |
| `hebi` | Hebisend Logistics & E-Commerce Fulfillment | 🇨🇴 CO | Medellín, Bogotá, Cali | E-Commerce, Retail, Cosmetics, Apparel, Consumer Goods |
| `chiketto` | Bespoke Software, Web/Mobile Apps & Agentic AI | 🇨🇴 CO | Medellín, Bogotá | Logistics, Fintech, Healthtech, High-growth Startups |
| `blueoil` | Fuel, Lubricants & Heavy Machinery Fleet Fueling | 🇨🇴 CO | Medellín, Valle de Aburrá | Construction, Transport Fleets, Mining, Heavy Industry |
| `facility_services_b2b` | Facility Management, Corporate Cleaning & Security | 🇨🇴 CO | Medellín, Bogotá | Corporate Buildings, Educational Institutions, Hospitals |
| `warehouse_aburra_norte` | Industrial Parks, Logistics Lots & Warehouses | 🇨🇴 CO | Bello, Girardota, Copacabana | Distribution Hubs, Manufacturing, Import/Export |

---

## 3. Order Lifecycle State Machine

Orders progress through an immutable, event-driven state machine:

```
[queued] ──► [processing] ──► [awaiting_payment] ──► [paid] ──► [completed]
    │                               ▲
    │                               │
    └────── (if processing fails) ──┴──► [failed]
```

### State Definitions

1. **`queued`**:
   - Order created by Web or WhatsApp.
   - Enqueued into Redis / Pub/Sub. No heavy database locks.
2. **`processing`**:
   - Picked up by `OrderWorkerDaemon`.
   - Engine executes registry harvesting, MX verification, and website audit.
3. **`awaiting_payment`**:
   - Lead batch assembled, CSV and Markdown dossier written to disk/GCS.
   - Sample teaser (3 redacted accounts) generated.
   - Quote calculated (e.g., $20.000 COP per verified account).
   - Checkout URL presented to buyer via Web or WhatsApp.
4. **`paid`**:
   - Wompi webhook receives `status: "APPROVED"`.
   - Security integrity checksum verified.
   - System unlocks full download links.
5. **`completed`**:
   - Buyer receives delivery package (email dispatch, WhatsApp file attachment, or direct web download).
6. **`failed`**:
   - If a registry is unreachable or zero leads pass quality gates, error message logged, user alerted.

---

## 4. API & Message Queue Payload Contracts

### 4.1 Order Creation Request (Dev Team -> Engine)

**HTTP POST** `/api/v1/orders`  
*(Or Pub/Sub message pushed to topic `projects/<PROJECT>/topics/michito-orders`)*

```json
{
  "client": {
    "client_id": "cli_98124",
    "name": "Alejandro Restrepo",
    "email": "alejandro@grupoinversion.co",
    "phone": "+573001234567",
    "channel": "whatsapp"
  },
  "request": {
    "campaign_id": "tinkko_enterprise_offices",
    "country": "CO",
    "cities": ["Medellín", "Bogotá"],
    "limit": 50,
    "segment": "enterprise",
    "sector": "Tecnología y Servicios Compartidos",
    "keywords_include": ["software", "cloud", "consultoria"],
    "keywords_exclude": ["alimentos", "construccion"]
  }
}
```

### 4.2 Immediate Response (Synchronous, < 50ms)

```json
{
  "status": "success",
  "order_id": "ord_20261106_a89f3e",
  "order_status": "queued",
  "estimated_processing_seconds": 25,
  "message": "Order successfully queued for asynchronous intelligence extraction."
}
```

### 4.3 Order Document in Storage / Database (After Engine Processing)

```json
{
  "order_id": "ord_20261106_a89f3e",
  "status": "awaiting_payment",
  "client": {
    "name": "Alejandro Restrepo",
    "email": "alejandro@grupoinversion.co",
    "phone": "+573001234567",
    "channel": "whatsapp"
  },
  "request": {
    "campaign_id": "tinkko_enterprise_offices",
    "country": "CO",
    "city": "Medellín",
    "limit": 50
  },
  "payment": {
    "provider": "wompi",
    "status": "pending",
    "currency": "COP",
    "amount_in_cents": 100000000,
    "amount_display": "$1.000.000 COP",
    "checkout_url": "https://checkout.wompi.co/l/michito_ord_20261106_a89f3e",
    "transaction_id": null
  },
  "delivery": {
    "total_qualified": 50,
    "sample_teaser": [
      {
        "company_name": "Soluciones Digitales Avanzadas",
        "city": "Medellín",
        "sector": "Desarrollo de Software y Cloud",
        "decision_maker_title": "Gerente General",
        "has_contracts": true,
        "intent_level": "Alto (Adjudicación SECOP II Reciente)"
      },
      {
        "company_name": "Consultoría Estratégica Andina",
        "city": "Bogotá",
        "sector": "Consultoría de Negocios y Finanzas",
        "decision_maker_title": "Presidente Ejecutivo",
        "has_contracts": false,
        "intent_level": "Estándar"
      }
    ],
    "csv_path": "gs://michito-deliverables/tinkko_enterprise_offices/ord_20261106_a89f3e/prospects.csv",
    "dossier_path": "gs://michito-deliverables/tinkko_enterprise_offices/ord_20261106_a89f3e/executive_dossier.md"
  },
  "metrics": {
    "total_elapsed_seconds": 18.4,
    "candidates_evaluated": 184,
    "qualification_rate_percent": 27.2
  },
  "created_at": "2026-11-06T20:50:00Z",
  "updated_at": "2026-11-06T20:50:18Z"
}
```

---

## 5. Wompi Payment Webhook Contract

When the buyer pays the quote, Wompi sends an HTTP POST event to the Dev Team's webhook URL.

### 5.1 Webhook Payload Example

```json
{
  "event": "transaction.updated",
  "data": {
    "transaction": {
      "id": "129845-169820-29384",
      "amount_in_cents": 100000000,
      "reference": "ord_20261106_a89f3e",
      "currency": "COP",
      "status": "APPROVED",
      "payment_method_type": "PSE"
    }
  },
  "signature": {
    "checksum": "3b29c1d09e8471b6e4...",
    "properties": ["transaction.id", "transaction.status", "transaction.amount_in_cents"]
  },
  "timestamp": 1730926250
}
```

### 5.2 Dev Team Webhook Action Checklist

1. **Verify Integrity Checksum**:
   Compute `SHA-256(transaction.id + transaction.status + transaction.amount_in_cents + WOMPI_EVENTS_SECRET)` and compare with `signature.checksum`.
2. **Confirm Status**: Check `transaction.status == "APPROVED"`.
3. **Transition Order State**:
   Update order status in Firestore / Redis:
   ```python
   adapter.mark_order_paid(
       order_id=data["transaction"]["reference"],
       transaction_id=data["transaction"]["id"],
       amount_in_cents=data["transaction"]["amount_in_cents"]
   )
   ```
4. **Trigger Fulfillment**:
   Generate a pre-signed Cloud Storage URL (valid for 48 hours) or attach the files, and dispatch them to the buyer's WhatsApp or Email.

---

## 6. WhatsApp Conversational Interaction Blueprint

Below is the verbatim script and UX sequence the Dev Team must implement in the WhatsApp Bot:

### Touch 1: Intake & Parameter Confirmation
> **Bot**:  
> "👋 ¡Hola! Bienvenido al motor de Inteligencia B2B de **Michito**.  
> ¿Qué tipo de empresas necesitas prospectar hoy?  
>  
> 1️⃣ Oficinas Corporativas / Coworking (Tinkko)  
> 2️⃣ Logística & Envíos E-Commerce (Hebisend)  
> 3️⃣ Desarrollo de Software & Apps (Chiketto)  
> 4️⃣ Combustible & Lubricantes para Flotas (Blue Oil)  
> 5️⃣ Aseo & Mantenimiento Corporativo (Facility Services)  
> 6️⃣ Bodegas & Parques Industriales (Aburrá Norte)"

### Touch 2: Offloading Notification (Instant Asynchronous Handoff)
> *(User selects 1, City: Medellín, Quantity: 25)*  
>  
> **Bot**:  
> "⚡ **Recibido.** Hemos puesto a trabajar nuestros bots de búsqueda en SECOP II y registros mercantiles de Medellín.  
>  
> 🔍 *Validando sitios web activos, teléfonos de representantes y servidores de correo corporativo...*  
> Te avisaremos en **~30 segundos** con una muestra de tus cuentas listas."

### Touch 3: Teaser Presentation & Price Quote (Awaiting Payment)
> **Bot**:  
> "🎯 **¡Tus 25 cuentas B2B han sido identificadas y verificadas!**  
>  
> Aquí tienes una vista previa confidencial:  
> • **Soluciones Digitales Avanzadas** (Medellín) — *Contrato público reciente de $450M adjudicado*  
> • **Consultoría Financiera Andina** (Medellín) — *Gerente General verificado, MX activo*  
> • **Ingeniería & Proyectos del Café** (Medellín) — *Búsqueda activa de vacantes en LinkedIn*  
>  
> 📦 **Paquete Completo:**  
> • 25 Contactos C-Level (Nombre, Celular directo, Email corporativo validado)  
> • Reporte de Contratos Públicos ganados  
> • Cadencia de 5 mensajes listos para copiar y enviar  
>  
> 💰 **Inversión:** $500.000 COP  
> 💳 **Paga seguro por PSE / Tarjeta aquí:** [https://checkout.wompi.co/l/ord_20261106_a89f3e](https://checkout.wompi.co/l/ord_20261106_a89f3e)"

### Touch 4: Deliverable Dispatch (Upon Wompi Webhook)
> **Bot**:  
> "✅ **¡Pago confirmado! Gracias por tu compra.**  
>  
> Aquí tienes tus archivos listos para importar a tu CRM o outreach masivo:  
> 📥 [Descargar CSV para CRM (25 Leads)](https://storage.googleapis.com/michito-deliverables/prospects.csv)  
> 📄 [Descargar Dossier Ejecutivo y Cadencia de 5 Pasos (Markdown/PDF)](https://storage.googleapis.com/michito-deliverables/dossier.md)  
>  
> ¿Deseas solicitar otro lote para otra ciudad o industria?"

---

## 7. Local Testing & Verification Commands

To verify the pipeline locally before deployment:

```bash
# 1. Start Firebase Local Emulators (Firestore on 8080)
firebase emulators:start --only firestore

# 2. Run All Unit Tests (13 tests across domain, adapters, and use cases)
PYTHONPATH=. venv/bin/python3 -m unittest discover tests/unit

# 3. Run a Dry-Run Prospecting Batch CLI
venv/bin/python3 generate_prospects.py --campaign tinkko_dr_offices --limit 3 --dry-run

# 4. Start the Background Worker Daemon in Run-Once Mode
venv/bin/python3 order_worker.py --once
```

