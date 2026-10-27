# 🎯 Michito (導人) — Colombian B2B Lead Intelligence Engine
### High-Precision Prospecting, Official Corporate Registries & Decision-Maker Discovery
*A Chiketto Technologies Product (`chiketto.co`)*

---

## 🏛️ What is Michito?

**Michito (導人 / 道途)** — derived from the Japanese *Michibiku* ("to guide, to lead, to show the path") — is a dedicated B2B Lead Intelligence Engine built specifically for the **Colombian market**.

Global lead databases (Apollo.io, ZoomInfo, Lusha) suffer from a **27%–30% error rate** in Latin America due to stale employee records and nonexistent coverage of middle-market companies. Meanwhile, local registry lists (Cámaras de Comercio / RUES) sell expensive, static dumps that only contain legal representatives and legal inboxes (`notificacionesjudiciales@...`), offering zero sales utility.

**Michito bridges this gap:**
1. **100% Colombian Ground Truth**: Integrates with official audited financial statements from **Supersociedades (`datos.gov.co`)** and **RUES** for verified operating revenues, active statuses, registered NITs, and CIIU economic activity codes.
2. **Safe, Zero-Ban Decision-Maker Discovery**: Uses pre-computed **Google X-Ray deep links** (`site:co.linkedin.com/in/...`) opening live profiles in your authenticated browser. Zero bot scraping, zero risk of LinkedIn IP or account bans.
3. **Deliverability Verification**: Checks corporate DNS MX records (Google Workspace vs Microsoft 365) and performs silent socket-level SMTP handshake pings (`RCPT TO`) to confirm the target inbox physically exists before sending.
4. **Full 5-Touch Outreach Sequences**: Generates complete, context-aware 5-touch sales sequences (LinkedIn invite, value emails, objection breakers, breakups) tailored by business segment.

---

## 💰 Commercial Pricing Model

| Lead Tier | Price (COP) | Value Delivered | Target Buyer |
| :--- | :---: | :--- | :--- |
| **Tier A: Qualified Account** | **$10.000 COP** (~$2.50 USD) | Verified NIT, legal name, audited revenue bracket, CIIU sector, domain, and 1-click Google X-Ray search link. | SDRs, sales reps, and outbound agencies needing qualified target lists. |
| **Tier B: Verified Decision-Maker** | **$50.000 COP** (~$12.50 USD) | Everything in Tier A + confirmed active decision-maker (CFO, COO, etc.), 0-bounce SMTP verified email, and corporate phone. | High-ticket B2B closers where a single deal is worth $5M–$50M+ COP. |

---

## 🚀 Quick Start & CLI Usage

### 1. Requirements
Ensure Python 3.10+ is installed:
```bash
pip install -r requirements.txt
```

### 2. Run Prospecting Batches

#### Example A: Generate Mid-Market Leads for Hebisend
```bash
python3 generate_colombian_prospects.py --campaign=hebi --segment=midmarket --city=Bogota --limit=25
```

#### Example B: Generate Leads for Electronic Invoicing (Chiketto)
```bash
python3 generate_colombian_prospects.py --campaign=chiketto --segment=small --city=Medellin --limit=25
```

#### Example C: Dry-Run (Preview without modifying deduplication ledger)
```bash
python3 generate_colombian_prospects.py --campaign=hebi --limit=5 --dry-run
```

#### Example D: View Ledger Statistics
```bash
python3 generate_colombian_prospects.py --stats
```

---

## 📁 Project Structure

```
michito/
├── generate_colombian_prospects.py   # Master CLI runner & orchestrator
├── colombia_registry_client.py       # Colombian corporate registry & SODA client
├── apollo_client.py                  # Contact enrichment & CSV importer
├── deduplication_ledger.py           # Persistent deduplication tracker (zero duplicates)
├── outreach_generator.py             # 5-touch copy generation & Google X-Ray queries
├── segments.py                       # Colombian corporate size definitions (Enterprise to Micro)
├── campaign_loader.py                # YAML campaign profile parser
├── campaigns/                        # Target campaign profiles (.yaml)
│   ├── hebi.yaml                     # Hebi Triad OS campaign
│   ├── chiketto.yaml                 # Chiketto Invoicing campaign
│   ├── facility_services_b2b.yaml    # Facility management campaign
│   └── warehouse_aburra_norte.yaml   # Real estate & warehouse campaign
├── templates/                        # Visual teaser & dossier HTML templates
├── data/
│   └── prospects_ledger.json         # Master ledger tracking prospected NITs
├── outputs/                          # Timestamped output folders (CSV, Markdown, HTML)
├── requirements.txt
└── .gitignore
```

---

## 🛡️ Deduplication & Permanent Protection
* Automatically tracks all generated NITs in `data/prospects_ledger.json` so no prospect is ever duplicated across runs or campaigns.
* Existing clients and partner entities (such as **Tinkko Coworking**) are permanently excluded by NIT and keyword.

---

## ⚖️ Compliance & Privacy
* Complies with **Ley 1581 de 2012 (Habeas Data)**: All corporate records originate from public transparency registries (Ley 1712 de 2014) and public commercial registers.
* **LinkedIn Safe**: Does not employ illegal web scrapers or unauthorized automated bots.

---
*© 2026 Chiketto Technologies S.A.S. • Bogotá & Medellín, Colombia*
