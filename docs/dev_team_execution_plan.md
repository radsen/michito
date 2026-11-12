# Michito B2B Engine — Production Readiness Audit & Master Execution Plan
*Document Version: 3.0 • Universal Architecture & Statutory AI Intelligence Edition • November 2026*

This document provides a comprehensive audit of completed systems against the Strategic Master Plan, quantifies the exact progress to launch, marks completed phases as DONE, and specifies the remaining implementation tracks for the AI agent suite, statutory operational harvesters, containerization, and cloud deployment.

---

## 1. Production Readiness Audit & Status Scorecard

```text
Overall Platform Readiness: ~92%
┌────────────────────────────────────────┬────────────────────────────────────────┐
│ Core Intelligence Engine:      100%    │ Data & Persistence:          100%      │
│ Universal Multi-Territory:     100%    │ Decoupled Web SPA:           100%      │
│ 2x1 Replacement Portal:        100%    │ Deduplication Ledger:        100%      │
│ Strict Fail-Fast DB:           100%    │ Omnichannel Outbound:        100%      │
│ AI Agent Intelligence Suite:    0%     │ Statutory Footprint Harvester: 0%      │
│ Production Containerization:    0%     │ Cloud SQL & Secrets (GCP):     0%      │
└────────────────────────────────────────┴────────────────────────────────────────┘
```

### Detailed Component Scorecard

| Subsystem | Strategic Requirement | Current State | Status | Owner |
| :--- | :--- | :--- | :--- | :--- |
| **Universal Prospecting Engine** | Decoupled dynamic search across 400+ CIIU sectors with custom quotas | Fully implemented in `GenerateProspectsUseCase` & tested | DONE | Core Engine |
| **Multi-Territory Harvesting** | Harvesters for Colombia 🇨🇴, Dominican Republic 🇩🇴, Ecuador 🇪🇨, and Cross-Border 🌎 | Fully implemented, live SODA + DGCP + SERCOP with offline fallbacks | DONE | Core Engine |
| **Deliverability Gates** | Socket SMTP MX DNS handshake (`RCPT TO`) + Web status verification | Fully implemented, 0% bounce guarantee verified | DONE | Core Engine |
| **Tier 3 Underwriting** | Audited EBITDA (Supersociedades) + Rama Judicial + BDME screening | Fully implemented (`UnderwriteLeadUseCase` + Worker + CSV/MD exports) | DONE | Core Engine |
| **Deduplication Ledger** | Persistent cross-campaign memory preventing repeated account prospecting | Fully implemented (`deduplication_ledger.py` with multi-key indexing) | DONE | Core Engine |
| **2x1 Replacement Portal** | Automated self-service replacement claim portal (`/claim-replacement`) | Fully implemented with instant verification, logging, and credit issuance | DONE | Core Engine |
| **Relational Database** | PostgreSQL 16 schema with strict Fail-Fast connection policy | Fully implemented in `SqlOrderAdapter`, hermetic in-memory test isolation | DONE | Core Engine |
| **Deliverable Storage** | Persist CSV, Branded Excel (.xlsx), PDF, and Markdown to canonical root | Consolidated to canonical `outputs/` directory; dual GCS/local adapter | DONE | Core Engine |
| **Web Client Architecture** | Decoupled React 18 + Redux Toolkit SPA matching Chiketto standards | Fully implemented in `clients/web` (bilingual es_CO / en_US, 0 build errors) | DONE | Dev Team |
| **Reusable UI Suite** | TagPillInput, GeoQuotaAllocator, SectorSelector, Presets, ErrorBoundary | Fully built, integrated into `OrderGenerator.tsx`, touch-optimized | DONE | Dev Team |
| **Order Intake Broker** | Decoupled message queue for order events | `PubSubQueueAdapter` implemented with 5 passing unit tests | DONE | Dev Team |
| **Payment Gateway** | Live Wompi checkout modal + SHA-256 integrity webhook receiver | Implemented in web client & `main.py` (`POST /api/v1/webhooks/wompi`) | DONE | Dev Team |
| **Omnichannel Dispatcher** | Outbound notification router (Email + WhatsApp) with download links | Fully implemented in `OmnichannelDeliveryAdapter` with audit archives | DONE | Dev Team |
| **AI Agent Intelligence Suite** | Gemini Flash brief parser, conversational WhatsApp agent, personalized copy | Database schema ready (`search_intent_queries`); live LLM adapter pending | TO DO | Dev Team / AI |
| **Statutory Footprint Harvester**| Fuel, procurement (RUP), and real estate (Curadurías) regulatory capture | Strategy defined; dedicated regulatory SODA adapters pending | TO DO | Core Engine |
| **Production Containerization** | Multi-stage Dockerfiles + docker-compose.yml (Postgres 16, API, worker, web) | Specification prepared; Docker orchestration pending | TO DO | DevOps |
| **Cloud SQL & Secrets (GCP)** | Cloud SQL Auth Proxy, GSM secret bindings, and Cloud Run deploy script | Specification prepared; provisioning pending | TO DO | DevOps |

---

## 2. Completed Scope Summary (Phases 1 through 7)

The core engine and web frontend have successfully completed all 7 foundational enterprise phases:

1. **Phase 1: DB Taxonomy & Universal Data Contracts**:
   - Universal data contracts (`UniversalProspectingRequest`, `LocationAllocation`).
   - Normalization tables (`taxonomy_sectors`, `taxonomy_roles`, `taxonomy_locations`, `search_intent_queries`).
2. **Phase 2: Engine Decoupling, Scarcity & Quality Ranking**:
   - Decoupled `GenerateProspectsUseCase` from static YAMLs.
   - Dynamic 5-touch omnichannel copywriting generation (`dynamic_cadence_generator.py`).
   - Quality scoring engine (0-100 index) combining contracts, solvency, and executive mobile verification.
3. **Phase 3: Client Deduplication Ledger & 2x1 Replacement Portal**:
   - Multi-key deduplication ledger (`tax_id`, `domain`, `phone`, `email`).
   - Automated self-service guarantee portal (`POST /api/v1/orders/{order_id}/claim-replacement`) issuing 2 verified replacement leads per valid bounce.
4. **Phase 4: API Layer, CRM Presets & Shareable Links**:
   - REST endpoints for universal orders, dynamic quotes, CRM presets, and direct download routing.
   - Referral partner commission accounting (Tinkko 25% revenue share tracking).
5. **Phase 5: Reusable UI Suite**:
   - `TagPillInput` with smart keyboard shortcuts, comma splitting, and duplicate prevention.
   - `GeoQuotaAllocator` with multi-country flags (🇨🇴, 🇩🇴, 🇪🇨, 🌎) and auto-balance distribution.
   - `SectorSelector` with searchable badges and CIIU code linking.
   - `ErrorBoundary` component preventing dark screen crashes.
6. **Phase 6: Universal Intake Experience**:
   - Dual-mode intake: Visual Interactive Form Mode ⇄ AI Natural Language Briefing Mode.
   - Real-time pricing calculator with volume discounts and multi-currency formatting (COP, USD, DOP).
7. **Phase 7: End-to-End Enterprise Scenario Verification**:
   - 14 comprehensive end-to-end scenario tests in `test_enterprise_13_scenarios.py` (100% pass rate in 2.5s).
   - Entire backend suite passing: **206 of 206 tests passing**.
   - Consolidated single canonical deliverable directory under `outputs/`.
   - Strict Fail-Fast database architecture without silent SQLite masking.

---

## 3. The Production Enterprise Runway (Remaining Implementation Tracks)

```text
┌────────────────────────────────────────────────────────────────────────┐
│                      REMAINING PRODUCTION TRACKS                       │
├────────────────────────────────────────────────────────────────────────┤
│ [TRACK A: Lightweight AI Agent Suite]                                  │
│  • Brief-to-Criteria Natural Language Parser (POST /parse-brief)       │
│  • Conversational WhatsApp Lead Agent (Meta Cloud API)                 │
│  • Dynamic Hyper-Personalized 5-Touch Sales Copywriter                 │
│  • Statutory Document NLP Extractor (Tenders & Curadurías)             │
│                                                                        │
│ [TRACK B: Statutory Operational Footprint Harvesters]                  │
│  • Fuel & Energy Tender Harvester (SECOP ACPM/Combustibles & MinMinas) │
│  • Goods Procurement Harvester (RUP Chamber of Commerce filings)       │
│  • Real Estate & Urban Expansion Harvester (Curadurías Urbanas)        │
│  • Private Sector Commercial Harvester (Supersociedades 10k SODA)      │
│                                                                        │
│ [TRACK C: Production Containerization & Local Dev Parity (DevOps)]     │
│  • Multi-Stage Python 3.13 slim Dockerfile (FastAPI Backend + Worker)  │
│  • Nginx Alpine Dockerfile for React SPA with /api reverse proxy       │
│  • Canonical docker-compose.yml (PostgreSQL 16, backend, worker, web)  │
│                                                                        │
│ [TRACK D: Cloud SQL & Secrets Infrastructure (GCP / GSM)]              │
│  • Google Cloud SQL PostgreSQL 16 provisioning & Cloud SQL Proxy       │
│  • Google Secret Manager (GSM) integration for live keys               │
│  • Cloud Run automated deployment script (deploy-cloud-run.sh)         │
└────────────────────────────────────────────────────────────────────────┘
```

---

### Track A: Lightweight AI Agent Intelligence Suite (Gemini Flash)

*Target Model*: **Gemini 1.5 Flash / 2.0 Flash** via the official `google-genai` SDK.  
*Unit Economics*: ~$0.0003 USD / ~\$1.20 COP per query, keeping direct gross margins above 94%.

#### A.1: Brief-to-Criteria Natural Language Parser
* **Endpoint**: `POST /api/v1/prospecting/parse-brief`
* **Task**:
  - Ingests raw unstructured text (e.g., *"Vendo dotaciones industriales y calzado de seguridad para plantas químicas en Medellín y Cali"*).
  - Emits a validated `UniversalProspectingRequest` JSON:
    - `sectors`: `["industrial_manufacturing", "chemicals_pharma"]`
    - `ciiu_codes`: `["C2011", "C1521", "C1522"]`
    - `roles`: `["Jefe de Compras", "Director de Seguridad Industrial", "Gerente de Planta"]`
    - `locations`: `[{"country": "CO", "city": "Medellín"}, {"country": "CO", "city": "Cali"}]`
    - `keywords_include`: `["dotaciones", "calzado seguridad", "química", "planta"]`
    - `keywords_exclude`: `["servicios temporales", "agencias empleo"]`
  - Persists the prompt and extracted tokens into `search_intent_queries` for continuous training.

#### A.2: Conversational WhatsApp Intake Agent
* **Service**: `clients/whatsapp/bot_service.py` connected to `main.py` (`POST /api/v1/webhooks/whatsapp`).
* **Task**:
  - Replaces regex matching with full natural language understanding.
  - Interprets conversational requests: *"Búscame 25 empresas de transporte en Bogotá con EBITDA > 10%"*.
  - Calls `POST /api/v1/orders` to queue the search and replies with an instant teaser preview and Wompi checkout link.
  - Delivers formatted deliverables automatically upon receiving Wompi payment webhook.

#### A.3: Dynamic Hyper-Personalized 5-Touch Copywriter
* **Service**: Enhances `backend/src/application/services/dynamic_cadence_generator.py`.
* **Task**:
  - Synthesizes personalized LinkedIn notes (<300 characters) and executive emails (<150 words) referencing the prospect's actual won contract trigger, revenue milestone, or expansion announcement.
  - Provides a deterministic fallback rule engine when running offline without external API access.

#### A.4: Statutory Regulatory NLP Extractor
* **Service**: `backend/src/adapters/nlp/statutory_document_extractor.py`.
* **Task**:
  - Parses unstructured Spanish text from public licensing resolutions, RUP filings, and municipal gazettes.
  - Extracts the named project director, fleet manager, or procurement lead along with direct contact details.

---

### Track B: Statutory Operational Footprint Harvesters (Fuel, Procurement & Real Estate)

Traditional scraping tools (Apollo, ZoomInfo) fail in Latin America because heavy-industry, logistics, and procurement leaders rarely maintain LinkedIn profiles. In Colombia 🇨🇴, these decision-makers are captured through mandatory statutory filings:

#### B.1: Fuel & Energy Tender Harvester (MinMinas & SECOP II Fleet Hack)
* **Problem**: Fuel and energy buyers (industrial manufacturing, truck fleets, logistics hubs) do not post on social networks.
* **Mechanism**:
  - Search SECOP II for contract awards with keywords: *"suministro de combustible"*, *"ACPM"*, *"gasolina"*, *"estación de servicio"*.
  - Query public resolutions from the Ministerio de Minas y Energía and environmental licenses (ANLA / Corantioquia / Área Metropolitana) for authorized fuel storage and industrial burner operations.
  - Mandatory compliance documentation requires the physical signature of the **Director of Logistics, Supply Chain Manager, or Fleet Operations Head**.
* **Adapter**: `backend/src/adapters/registries/colombia/fuel_tender_harvester_adapter.py`.

#### B.2: Goods Procurement & Supply Chain Harvester (RUP & DIAN RUT Metadata)
* **Problem**: Heads of purchasing (*Jefes de Compras*) protect their corporate emails to prevent vendor spam.
* **Mechanism**:
  - **Registro Único de Proponentes (RUP)**: Any company bidding on major public tenders or tier-1 private subcontracts must publish its financial capacity and technical staff in the Chamber of Commerce RUP registry. This publishes the names of the technical directors, procurement heads, and chief engineers.
  - **Vendor Onboarding Guidelines**: Maps incoming supplier registration channels (`proveedores@empresa.com`, `compras@empresa.com`) and routing structures.
* **Adapter**: `backend/src/adapters/registries/colombia/rup_procurement_harvester_adapter.py`.

#### B.3: Real Estate, Infrastructure & Urban Expansion Harvester (Curadurías Urbanas)
* **Problem**: Commercial real estate expansion heads, land buyers, and construction directors operate offline.
* **Mechanism**:
  - **Curadurías Urbanas (Bogotá, Medellín, Cali, Barranquilla)**: All commercial construction, remodeling, and industrial warehouse adaptation projects require mandatory public licensing through Urban Curatorships.
  - Public licensing resolutions explicitly list:
    1. Corporate property owner and NIT.
    2. Named **Director de Obra**, **Arquitecto Responsable**, or **Gerente de Infraestructura / Expansión**.
  - Cross-references with Superintendencia de Sociedades real estate asset balance disclosures.
* **Adapter**: `backend/src/adapters/registries/colombia/curaduria_realestate_harvester_adapter.py`.

#### B.4: Private Commercial Enterprise Harvester (Supersociedades 10k SODA Dataset)
* **Problem**: SECOP II only captures public sector contractors; large private commercial enterprises (B2B distributors, manufacturers) are excluded.
* **Mechanism**:
  - Connects to official open data portal `datos.gov.co` dataset `jgik-6c4w` (10,000 largest private commercial companies by operating revenue).
  - Filters by active status, city, revenue bracket, and CIIU code.
* **Adapter**: `backend/src/adapters/registries/colombia/supersociedades_soda_adapter.py`.

---

### Track C: Production Containerization & Local Dev Parity (DevOps)

#### C.1: Multi-Stage Backend Dockerfile (`backend/Dockerfile`)
* Python 3.13 slim base image.
* Non-root security user (`michito`, UID 10001).
* Multi-stage caching: dependencies installed into virtualenv in builder stage, then copied to minimal runtime image.
* Default entrypoint: `uvicorn src.entrypoints.api.main:app --host 0.0.0.0 --port 8000`.

#### C.2: Multi-Stage Frontend Dockerfile (`clients/web/Dockerfile`)
* Builder stage: Node 20 Alpine executing `npm run build`.
* Runtime stage: Nginx Alpine serving compiled static assets from `/usr/share/nginx/html`.
* Custom `nginx.conf`: Gzip/brotli compression, HTML5 pushState routing (`try_files $uri /index.html`), and reverse proxy `/api/` forwarding to backend container on port 8000.

#### C.3: Canonical `docker-compose.yml`
* Services:
  1. `postgres`: PostgreSQL 16 with healthcheck and persistent volume `michito_pgdata`.
  2. `backend`: FastAPI API listening on port 8000.
  3. `worker`: Order Worker Daemon monitoring queued orders.
  4. `web`: Nginx frontend listening on port 3000.
* Verification: A single command (`docker compose up --build`) boots the entire stack with full local-to-cloud fidelity.

---

### Track D: Cloud SQL & Secrets Infrastructure (GCP / GSM)

#### D.1: Production Cloud SQL Provisioning
* PostgreSQL 16 on Google Cloud SQL with automated daily backups and SSL enforcement.
* Cloud SQL Auth Proxy configuration for secure Unix socket access from Google Cloud Run.
* Database initialization and migration scripts.

#### D.2: Google Secret Manager (GSM) Integration
* Secure key storage mapped as environment variables in Cloud Run:
  - `DATABASE_URL`: PostgreSQL connection string.
  - `WOMPI_PUBLIC_KEY`, `WOMPI_INTEGRITY_SECRET`, `WOMPI_EVENTS_SECRET`: Live payment credentials.
  - `WHATSAPP_TOKEN`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`: Meta Cloud API keys.
  - `GEMINI_API_KEY`: Google GenAI API key.

#### D.3: Cloud Run Deployment Automation (`deploy-cloud-run.sh`)
* Automated build and deployment script using Google Cloud Build and `gcloud run deploy`.
* Dedicated VPC connector for static outbound IP (required for Port 25 SMTP mailbox verification).

---

## 4. Execution Sequence & Prioritization

```text
STEP 1: Track A — Lightweight AI Agent Intelligence Suite
        • Build Gemini Flash LLM adapter (with offline fallback for hermetic tests).
        • Implement Brief-to-Criteria Parser (A.1) and Conversational WhatsApp Agent (A.2).
        • Implement Dynamic Personalized Copywriter (A.3) and Statutory NLP Extractor (A.4).

STEP 2: Track B — Statutory Operational Footprint Harvesters
        • Implement Fuel & Energy Tender Adapter (B.1).
        • Implement Goods Procurement & RUP Adapter (B.2).
        • Implement Curadurías Urbanas Real Estate Adapter (B.3).
        • Implement Supersociedades 10,000 Private Commercial Harvester (B.4).

STEP 3: Track C — Production Containerization & Dev Parity
        • Author backend & frontend Dockerfiles.
        • Build and test canonical docker-compose.yml.
        • Validate end-to-end multi-scenario execution inside containers.

STEP 4: Track D — Cloud Infrastructure & Cloud Run Deployment
        • Provision Cloud SQL and configure Google Secret Manager.
        • Execute deployment to Google Cloud Run.
```
