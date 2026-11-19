# Public Registry Harvesters Runbook (Colombia, Ecuador, Dominican Republic)
*Document Version: 1.0 • Statutory Registry Harvesting Protocol • November 2026*

This guide details how Michito connects to official open data government portals across Colombia 🇨🇴, Ecuador 🇪🇨, and the Dominican Republic 🇩🇴 to harvest public contracts, tax identifiers, and official company records.

---

## 1. Registry Architecture & Endpoints

| Country | Agency / Registry | Protocol / API | Endpoint | Authentication | Rate Limits |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Colombia 🇨🇴** | **SECOP II (Colombia Compra Eficiente)** | SODA REST API (JSON) | `https://www.datos.gov.co/resource/jbjy-vk9h.json` | `X-App-Token` (Optional but recommended) | 1,000 req/hr unauthenticated; 50,000 req/hr with App Token |
| **Dominican Republic 🇩🇴** | **DGCP (Compras Dominicanas)** | Open Data Portal API | `https://datos.gob.do/api/action/datastore_search` | Public Open Data | 100 req/min |
| **Ecuador 🇪🇨** | **SERCOP (Compras Públicas Ecuador)** | Open Contracting REST | `https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/api/` | Public Open Contracting | 120 req/min |

---

## 2. In-Memory Caching & SODA Performance

Direct SODA Socrata API queries can take 2 to 4 seconds if unindexed fields are queried. To maintain high-speed engine performance:

1. **In-Memory TTL Cache**:
   The `SecopHarvesterAdapter` caches SODA responses in memory for **1 hour** (`_soda_cache`). Repeated searches across the same city and CIIU code resolve in **under 3 milliseconds**.
2. **Offline Fallback Rosters**:
   If an external government portal experiences downtime (e.g. `datos.gov.co` HTTP 503 maintenance), the harvester automatically falls back to statutory regional rosters stored in `backend/src/adapters/registries/colombia/statutory_roster.py`.
3. **Zero-Token Harvesting**:
   Registry harvesting uses strictly deterministic database queries and SODA filters (`$where`, `$limit`, `orden_compra`), consuming **0 LLM tokens**.

---

## 3. Configuration & Tokens

```bash
# Colombia SECOP II SODA App Token (Generatable at datos.gov.co)
SECOP_APP_TOKEN="YOUR_SOCRATA_APP_TOKEN"

# Rate Limit & Timeout Guards
REGISTRY_HTTP_TIMEOUT_SECONDS=8
REGISTRY_CACHE_TTL_SECONDS=3600
```
