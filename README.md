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

## 🏗️ Monorepo Architecture Overview

Michito is organized as a clean **polyglot monorepo** with strict separation between backend engine logic and consumer clients:

```
michito/
├── backend/                       # Python Engine, API, & CLI Prospector
│   ├── src/
│   │   ├── domain/                # Pure Business Entities & Value Objects
│   │   ├── application/           # Ports, DTOs & Use Cases
│   │   ├── adapters/              # Registries, DBs, Queues, Payments, Verifiers
│   │   ├── entrypoints/           # FastAPI Web API & Background Workers
│   │   └── config.py              # Environment configuration loader
│   ├── tests/                     # Unit, Integration, and E2E test suite (131 tests)
│   ├── campaigns/                 # Target ICP YAML profiles (Hebi, Chiketto, etc.)
│   ├── data/                      # Deduplication ledger tracking
│   ├── templates/                 # HTML one-pager teaser templates
│   ├── outputs/                   # Generated batch deliverables (gitignored)
│   ├── reports/                   # QA & security audit logs
│   ├── scripts/                   # Commercial batch generator scripts
│   ├── requirements.txt           # Python backend dependencies
│   ├── pytest.ini                 # Backend test runner configuration
│   ├── Dockerfile                 # Production multi-stage Docker build
│   ├── generate_prospects.py      # CLI runner for lead generation
│   └── order_worker.py            # Async order worker daemon
├── clients/                       # Consumer Clients
│   ├── web/                       # React 18 + Redux Toolkit SPA (Vite + Tailwind CSS)
│   │   ├── src/                   # Components, Slices, RTK Query API, Locales
│   │   ├── package.json           # Frontend package dependencies
│   │   └── vite.config.ts         # Vite bundler & reverse proxy configuration
│   └── whatsapp/                  # WhatsApp Business Cloud API Bot Service
├── package.json                   # Root monorepo workspace orchestrator (npm workspaces)
├── Makefile                       # Unified developer task runner
├── docker-compose.yml             # Local PostgreSQL & container orchestration
├── start_dev_env.sh               # One-click tabbed TMUX development stack launcher
├── .env.example                   # Committed environment variable template
├── .gitignore                     # Monorepo-wide git exclusion rules
└── README.md                      # Primary project documentation
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

Michito automatically loads environment variables through `backend/src/config.py` following standard stage priority (`.env.local` $\rightarrow$ `.env.stg` $\rightarrow$ `.env`):

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

The repository provides an automated startup script that spins up the full stack in dedicated TMUX tabs:

```bash
make dev
# or: ./start_dev_env.sh
```

This launches:
- **Tab 1: [api]** -> FastAPI Backend at `http://localhost:8000` (Swagger docs at `/docs`)
- **Tab 2: [web]** -> Vite React SPA at `http://localhost:3000`
- **Tab 3: [firebase]** -> Firebase Emulators (Hosting, Storage, Pub/Sub, Web UI at `:4001`)
- **Tab 4: [worker]** -> Asynchronous Order Worker Daemon
- **Tab 5: [dev]** -> Interactive Dev Shell & Test Runner

*Stop all services anytime with: `./start_dev_env.sh --stop`*

---

### Option B: Running Services via Unified Makefile / npm Scripts

From the repository root:

```bash
# Install all dependencies (Python venv + Node npm)
make install
# or: npm run install:all

# Run FastAPI backend directly
make dev-api
# or: npm run dev:api

# Run Vite React web client directly
make dev-web
# or: npm run dev:web

# Run background order worker daemon
make dev-worker
# or: npm run dev:worker
```

---

## 🛠️ CLI Prospecting Tools

Michito includes ready-to-run CLI commands for batch lead generation, campaign dry-runs, and deduplication statistics:

### 1. Generate Leads for a Target Campaign
```bash
# Mid-market leads for Hebi in Bogotá (25 leads)
make prospects ARGS="--campaign=hebi --segment=midmarket --city=Bogota --limit=25"

# Small business leads for Chiketto Invoicing in Medellín
make prospects ARGS="--campaign=chiketto --segment=small --city=Medellin --limit=25"

# Directly via python
./venv/bin/python backend/generate_prospects.py --campaign=hebi --segment=midmarket --city=Bogota --limit=25
```

### 2. Dry-Run Mode (Preview Without Modifying Deduplication Ledger)
```bash
make prospects ARGS="--campaign=hebi --limit=5 --dry-run"
```

### 3. Check Deduplication Ledger Statistics
```bash
make stats
# or: ./venv/bin/python backend/generate_prospects.py --stats
```

### 4. Run Commercial Pilot Batch Generator
```bash
make pilot
# or: ./venv/bin/python backend/scripts/generate_tinkko_pilot_batch.py
```

---

## 🧪 Testing Suite

Michito maintains **100% passing automated test coverage** across domain logic, adapters, external APIs, and webhooks:

### Run Full Test Suite
```bash
make test
# or: npm test
# or: ./venv/bin/pytest -v
```
*(131 tests complete in ~0.70s)*

### Run by Category
```bash
# Unit Tests (Domain Entities, Value Objects, Adapters, Use Cases)
make test-unit

# Integration Tests (SODA API, Repository fallbacks, GCS Storage)
make test-integration

# End-to-End Tests (FastAPI endpoints, Wompi webhooks, WhatsApp webhooks)
make test-e2e

# Run with test coverage report
make test-cov
```

---

## 📦 Production Build & Containerization

### 1. Build Frontend Client
```bash
make build
# or: npm run build
```
Builds the optimized production bundle to `clients/web/dist/`. FastAPI serves this static bundle directly at `/` and `/assets`.

### 2. Docker Container Build
```bash
# Build Docker image
docker build -f backend/Dockerfile -t michito-api:latest .

# Run with docker-compose
docker compose up -d
```

---

## ⚖️ Legal, Compliance & Privacy

- **Habeas Data Compliance (Ley 1581 de 2012)**: All corporate records, company representations, and financials originate from statutory transparency registries (**Ley 1712 de 2014**) and public administrative databases.
- **Strict Anti-Bot & Anti-Scraping Policy**: Michito never deploys headless scrapers against LinkedIn or social networks. Decision-maker discovery generates compliant search queries directly accessible by authenticated human operators.
- **Enterprise Trade Secret Protection**: Internal harvester algorithms, endpoint definitions, and registry parsers operate under the proprietary **Michito Intent Engine™** trademark.

---
*© 2026 Chiketto Technologies S.A.S. • Bogotá & Medellín, Colombia • All Rights Reserved.*
