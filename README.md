# 🎯 Michito (導人) — B2B Lead Intelligence Engine
### High-Precision Prospecting, Official Corporate Registries & Decision-Maker Discovery
*A Chiketto Technologies Product (`chiketto.co`)*

---

## 🏛️ What is Michito?

**Michito (導人 / 道途)** — derived from the Japanese *Michibiku* ("to guide, to lead, to show the path") — is an enterprise B2B Lead Intelligence and Prospecting Engine tailored for high-ticket sales in Latin America (Colombia & Dominican Republic).

Global lead providers (such as Apollo.io, ZoomInfo, or Lusha) suffer from high error rates in Latin America due to stale employee records and nonexistent coverage of middle-market and local contractors. Meanwhile, traditional commercial chambers only sell static contact dumps containing generic legal inboxes (`notificacionesjudiciales@...`) with zero sales utility.

**Michito bridges this gap through the Michito Intent Engine™:**
1. **Official Public Registries Ground Truth**: Queries audited financial statements, active corporate statuses, registered tax IDs (NIT / RNC), and statutory economic activities (CIIU).
2. **Safe, Zero-Ban Decision-Maker Discovery**: Uses pre-computed **Google X-Ray deep links** (`site:co.linkedin.com/in/...`) opening live profiles in your authenticated browser. Zero automated scrapers, zero risk of LinkedIn IP or account bans.
3. **Multi-Step Deliverability Verification**: Analyzes corporate DNS MX configurations and runs socket-level SMTP handshake pings (`RCPT TO`) to guarantee low bounce rates before outreach begins.
4. **Automated Financial Underwriting & Litigation Screening**: Assesses statutory EBITDA margins, revenue brackets, public procurement contract history, and screens against national debtor lists (BDME) and court databases (Rama Judicial).
5. **Decoupled Architecture**: High-performance FastAPI REST API paired with a reactive React 18 + Redux Toolkit SPA and async order execution daemon via Pub/Sub.

---

## 🏗️ Architecture Overview

Michito follows strict **Clean & Onion Architecture** principles with clear separation of concerns:

```
src/
├── domain/                      # Enterprise Business Rules & Core Entities
│   ├── entities/                # Company, LeadOrder, DecisionMaker, FinancialReport, LitigationRecord
│   └── value_objects/           # CIIUCode, EbitdaMargin, ConfidenceScore, EmailAddress, TaxId
├── application/                 # Application Business Rules (Use Cases & Ports)
│   ├── ports/                   # Abstract Interfaces (DB, Queue, Verification, Storage, Payments)
│   ├── dto/                     # LeadDossierDTO, SearchRequestDTO
│   └── use_cases/               # GenerateProspects, UnderwriteLead, CreateOrder, FulfillWebhook, etc.
├── adapters/                    # Interface Adapters (External Services & Infrastructure)
│   ├── db/                      # FirestoreOrderAdapter, SqlOrderAdapter (PostgreSQL / SQLite)
│   ├── queue/                   # PubSubQueueAdapter (GCP Pub/Sub), MemoryQueueAdapter
│   ├── registries/              # Colombia SECOP I/II, SODA Supersociedades, DR DGCP
│   ├── verifiers/               # Socket SMTP Handshake, Google X-Ray, Website Auditor
│   ├── litigation/              # Contraloría BDME, Rama Judicial Court Records
│   ├── payments/                # Wompi Colombia Payment Gateway (Card, PSE, Bancolombia)
│   ├── storage/                 # Google Cloud Storage (GCS), LocalStorage, DeduplicationLedger
│   └── export/                  # Multi-tab Excel Dossiers, HTML One-Pager Teasers
└── entrypoints/                 # System Delivery Mechanisms
    ├── api/                     # FastAPI Application, Webhook Handlers, Static Mounts
    ├── container.py             # Dependency Injection Container
    └── workers/                 # OrderWorkerDaemon (Async Order Fulfillment)

clients/
├── web/                         # React 18 + Redux Toolkit SPA (Vite + Tailwind CSS)
└── whatsapp/                    # WhatsApp Business Cloud API Bot Service
```

---

## 💰 Commercial Pricing Model

| Lead Tier | COP Price | USD Equivalent | Included Deliverables | Target Buyer |
| :--- | :---: | :---: | :--- | :--- |
| **Tier 1: Qualified Account** | **$10.000 COP** | ~$2.50 USD | Verified NIT, active legal name, audited revenue bracket, CIIU sector, domain status, and 1-click Google X-Ray search query. | SDRs and outbound agencies needing validated target accounts. |
| **Tier 2: Decision-Maker Contact** | **$50.000 COP** | ~$12.50 USD | Everything in Tier 1 + confirmed active C-Level / VP contact, direct corporate phone/extension, 0-bounce SMTP verified email, and tailored 5-touch copy. | B2B sales teams running account-based outbound campaigns. |
| **Tier 3: Underwritten & Dossier** | **$120.000 COP** | ~$30.00 USD | Everything in Tier 2 + statutory EBITDA analysis, public procurement contract history, litigation screening (BDME/Rama Judicial), and exportable Excel dossier. | Enterprise closers, credit underwriters, and high-ticket B2B service providers. |

*Volume discounts automatically apply for batches of 25 (10% off), 50 (15% off), 100 (20% off), and 250+ (25% off).*

---

## ⚙️ Environment Configuration

Michito automatically loads environment variables through `src/config.py` following standard stage priority (`.env.local` $\rightarrow$ `.env.stg` $\rightarrow$ `.env`):

```bash
# 1. Copy the committed template to your local environment file
cp .env.example .env.local

# 2. Configure key variables in .env.local as needed
WOMPI_PUBLIC_KEY=pub_test_...
WOMPI_PRIVATE_KEY=prv_test_...
WOMPI_INTEGRITY_SECRET=test_integrity_...
DATABASE_URL=sqlite:///michito_orders.db  # or postgresql://user:pass@localhost:5432/michito
ENABLE_PUBSUB_QUEUE=false               # Set to true when GCP Pub/Sub or emulator is available
GCP_PROJECT_ID=michito-prod
GCS_BUCKET_NAME=michito-dossiers
```

> **Note**: `.env`, `.env.*` (except `.env.example`), and database files (`*.db`, `*.sqlite3`) are strictly `.gitignore`d to prevent credential leakage.

---

## 🚀 Quick Start: Local Development

### Option A: Complete Dev Environment (One-Command)

The repository provides an automated startup script that spins up the full stack:

```bash
./start_dev_env.sh
```

This launches:
- **Firebase Emulators** (Firestore, Storage, Pub/Sub) with Web UI at `http://localhost:4001`
- **FastAPI API Backend** at `http://localhost:8000` (Swagger docs at `/docs`)
- **Vite React Web Client** at `http://localhost:3000`

---

### Option B: Running Services Individually

#### 1. Python Virtual Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Running the FastAPI Backend Server
```bash
uvicorn src.entrypoints.api.main:app --reload --host 0.0.0.0 --port 8000
```
- API Base URL: `http://localhost:8000`
- Swagger UI Documentation: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/api/v1/health`

#### 3. Running the React 18 + Redux Web Client
```bash
cd clients/web

# Install npm dependencies
npm install

# Start Vite dev server with proxy to :8000
npm run dev
```
- Client URL: `http://localhost:3000`

#### 4. Running the Asynchronous Order Worker Daemon
```bash
# Polls Firestore/SQL queue and processes paid orders
python3 order_worker.py --daemon --poll-interval=5
```

---

## 🛠️ CLI Prospecting Tools

Michito includes ready-to-run CLI commands for batch lead generation, campaign dry-runs, and deduplication statistics:

### 1. Generate Leads for a Target Campaign
```bash
# Mid-market leads for Hebi in Bogotá (25 leads)
python3 generate_prospects.py --campaign=hebi --segment=midmarket --city=Bogota --limit=25

# Small business leads for Chiketto Invoicing in Medellín
python3 generate_prospects.py --campaign=chiketto --segment=small --city=Medellin --limit=25

# Facility Services B2B in Cali
python3 generate_prospects.py --campaign=facility_services_b2b --segment=enterprise --city=Cali --limit=15
```

### 2. Dry-Run Mode (Preview Without Modifying Deduplication Ledger)
```bash
python3 generate_prospects.py --campaign=hebi --limit=5 --dry-run
```

### 3. Check Deduplication Ledger Statistics
```bash
python3 generate_prospects.py --stats
```

### 4. Run Commercial Pilot Batch Generator
```bash
python3 scripts/generate_tinkko_pilot_batch.py
```

---

## 🧪 Testing Suite

Michito maintains **100% passing automated test coverage** across domain logic, adapters, external APIs, and webhooks:

### Run Full Test Suite
```bash
./venv/bin/pytest -v
```
*(131 tests complete in ~0.70s)*

### Run by Test Category
```bash
# Unit Tests (Domain Entities, Value Objects, Adapters, Use Cases)
./venv/bin/pytest tests/unit/

# Integration Tests (SODA API, Repository fallbacks, GCS Storage)
./venv/bin/pytest tests/integration/

# End-to-End Tests (FastAPI endpoints, Wompi webhooks, WhatsApp webhooks)
./venv/bin/pytest tests/e2e/

# Run a specific test file
./venv/bin/pytest tests/unit/test_bot_service.py

# Run with test coverage report
./venv/bin/pytest --cov=src tests/
```

---

## 📦 Production Build & Containerization

### 1. Build Frontend Client
```bash
cd clients/web
npm run build
```
Builds the optimized production bundle to `clients/web/dist/`. FastAPI serves this static bundle directly at `/` and `/assets`.

### 2. Docker Container Build
```bash
# Build Docker image
docker build -t michito-api:latest .

# Run container with docker-compose
docker compose up -d
```

---

## 📁 Repository Directory Structure

```
michito/
├── clients/
│   ├── web/                          # React 18 + Redux SPA
│   │   ├── src/
│   │   │   ├── components/           # UI, Landing, Order & Tracker components
│   │   │   ├── store/                # Redux Toolkit store, slices, RTK Query API
│   │   │   └── locales/              # es_CO and en_US localization dictionaries
│   │   ├── package.json
│   │   └── vite.config.ts
│   └── whatsapp/                     # WhatsApp Cloud API bot service
├── campaigns/                        # Target campaign YAML profiles
│   ├── chiketto.yaml                 # Electronic invoicing ICP profile
│   ├── hebi.yaml                     # B2B SaaS Triad OS profile
│   ├── facility_services_b2b.yaml    # Facility management profile
│   └── warehouse_aburra_norte.yaml   # Logistics & industrial warehouse profile
├── data/                             # Deduplication ledger tracking
│   ├── .gitkeep
│   └── prospects_ledger.example.json # Template ledger file
├── docs/                             # Architecture specifications & financial models
│   ├── developer_handoff_specification.md
│   └── strategy/financial_model_unit_economics.md
├── outputs/                          # Generated lead batches & Excel dossiers (gitignored)
│   └── .gitkeep
├── reports/                          # QA & security audit logs
│   └── .gitkeep
├── scripts/                          # Batch generation & automation utilities
│   └── generate_tinkko_pilot_batch.py
├── src/                              # Core Clean Architecture source tree
│   ├── domain/                       # Pure business models & value objects
│   ├── application/                  # Ports, DTOs & Use Cases
│   ├── adapters/                     # Registries, DBs, Queues, Payments, Verifiers
│   ├── entrypoints/                  # FastAPI app & background workers
│   └── config.py                     # Centralized environment loader
├── templates/                        # HTML one-pager teaser templates
├── tests/                            # Unit, Integration, and E2E test suite (131 tests)
├── .env.example                      # Committed configuration template
├── .gitignore                        # Git exclusion rules
├── Dockerfile                        # Multi-stage production container
├── docker-compose.yml                # Multi-service container orchestration
├── generate_prospects.py             # Root CLI entrypoint for prospecting
├── order_worker.py                   # Root CLI entrypoint for background worker
├── pytest.ini                        # Pytest configuration
├── requirements.txt                  # Python dependencies
└── start_dev_env.sh                  # One-click local development stack launcher
```

---

## ⚖️ Legal, Compliance & Privacy

- **Habeas Data Compliance (Ley 1581 de 2012)**: All corporate records, company representations, and financials originate from statutory transparency registries (**Ley 1712 de 2014**) and public administrative databases.
- **Strict Anti-Bot & Anti-Scraping Policy**: Michito never deploys headless scrapers against LinkedIn or social networks. Decision-maker discovery generates compliant search queries directly accessible by authenticated human operators.
- **Enterprise Trade Secret Protection**: Internal harvester algorithms, endpoint definitions, and registry parsers operate under the proprietary **Michito Intent Engine™** trademark.

---
*© 2026 Chiketto Technologies S.A.S. • Bogotá & Medellín, Colombia • All Rights Reserved.*
