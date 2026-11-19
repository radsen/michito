# Cloud Run Jobs: Decoupled Batch Prospecting & Harvesting Architecture
*Document Version: 1.0 • Decoupled Worker Execution • November 2026*

This runbook documents the architecture, lifecycle, dispatch mechanics, and operational procedures for **Michito's Decoupled Cloud Run Job (`michito-batch-worker`)**.

---

## 1. Overview & Architectural Motivation

In previous iterations, background harvesting was executed inside the interactive Cloud Run API instance or via an always-on Pub/Sub subscriber worker. 

### Why Decoupled Cloud Run Jobs?
1. **Cost Minimization ($0 Idle Cost)**: Unlike continuous services, Cloud Run Jobs only incur compute costs during execution. When no orders are being processed, cost is exactly $0.
2. **Extended Execution Window (Up to 24 Hours)**: Interactive Cloud Run API requests have a maximum 60-minute timeout. Cloud Run Jobs can execute for up to 24 hours per task, accommodating large enterprise batches (1,000+ accounts across multiple territories).
3. **Resilience & Task Isolation**: Failures or memory pressure during heavy headless scraping or live MX verification cannot crash the public API or interrupt customer checkout.
4. **Immediate Client Response (2-Second Radar Scan)**: The API executes an instant 2-second pre-scan to present verified sample accounts, handles payment authorization, and delegates deep batch harvesting to the Cloud Run Job.

---

## 2. Execution Flow Diagram

```text
[ Buyer Submits Order ]
         │
         │  1. POST /api/v1/orders
         ▼
[ Michito Cloud Run API ]
         │
         │  2. Instant 2-second Radar Scan (3 live masked samples)
         │  3. Order created in PostgreSQL ('awaiting_payment')
         ▼
[ Wompi Payment Gateway ]
         │
         │  4. Webhook POST /api/v1/webhooks/wompi
         ▼
[ Michito Cloud Run API ]
         │
         │  5. Validates SHA-256 HMAC signature
         │  6. Updates order status to 'paid'
         │  7. Dispatches Cloud Run Job via GCP API:
         │     gcloud run jobs execute michito-batch-worker --args="--order-id=<id>"
         ▼
[ Cloud Run Job: michito-batch-worker ]
         │
         │  8. Fetches order parameters from PostgreSQL
         │  9. Executes Adaptive Live Harvesters (SECOP, RUES, DGCP, SERCOP)
         │ 10. Multi-threaded HTTP web presence audit
         │ 11. Direct Socket MX mailbox handshake verification
         │ 12. Generates commercial deliverables (XLSX, PDF Dossier, CRM CSV)
         │ 13. Uploads deliverables to Cloud Storage (gs://michito-<env>-deliverables/)
         │ 14. Updates order status to 'completed' in PostgreSQL
         │ 15. Dispatches omnichannel delivery (Email & WhatsApp)
         ▼
[ Order Delivered to Buyer ]
```

---

## 3. Configuration & Environment Variables

The Cloud Run Job uses the same Docker container image as the backend API (`backend/Dockerfile`), executing with the entrypoint:

```bash
python3 -m src.entrypoints.workers.job_runner --order-id=<ORDER_ID>
```

### Required Job Environment Variables

| Variable | Description | Example (Staging) | Example (Production) |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://michito_user:...@/michito_db?host=/cloudsql/...` | `postgresql://michito_user:...@/michito_db?host=/cloudsql/...` |
| `GCS_DELIVERABLES_BUCKET`| Deliverables bucket name | `michito-staging-deliverables` | `michito-prod-deliverables` |
| `MICHITO_ENV` | Environment identifier | `staging` | `prod` |
| `GOOGLE_CLOUD_PROJECT` | GCP Project ID | `michito-staging` | `michito-prod` |
| `GCP_REGION` | Compute region | `us-central1` | `us-central1` |
| `CLOUD_RUN_JOB_NAME` | Job identifier | `michito-batch-worker` | `michito-batch-worker` |
| `MAX_RETRIES` | Task retry attempts | `2` | `2` |
| `TASK_TIMEOUT` | Maximum execution duration | `1800s` (30 mins) | `3600s` (1 hour) |

---

## 4. Operational CLI Commands (Staging & Production)

### 1. View Job Configuration
```bash
# Staging
gcloud run jobs describe michito-batch-worker \
    --project=michito-staging \
    --region=us-central1

# Production
gcloud run jobs describe michito-batch-worker \
    --project=michito-prod \
    --region=us-central1
```

### 2. Manually Trigger a Job for an Order
```bash
# Staging manual trigger
gcloud run jobs execute michito-batch-worker \
    --project=michito-staging \
    --region=us-central1 \
    --args="--order-id=ord_test_staging_123"

# Production manual trigger
gcloud run jobs execute michito-batch-worker \
    --project=michito-prod \
    --region=us-central1 \
    --args="--order-id=ord_prod_live_456"
```

### 3. List Recent Job Executions
```bash
gcloud run jobs executions list \
    --job=michito-batch-worker \
    --project=michito-staging \
    --region=us-central1 \
    --limit=10
```

### 4. Stream Logs for an Active Execution
```bash
# Stream latest execution logs
gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="michito-batch-worker"' \
    --project=michito-staging \
    --limit=50 \
    --format="value(textPayload)"
```

---

## 5. Local Development & Emulator Simulation

When testing locally without Cloud Run:

1. **Direct CLI Invocations**:
   ```bash
   export DATABASE_URL="sqlite:///michito_dev.db"
   python3 -m src.entrypoints.workers.job_runner --order-id=ord_local_test_1
   ```

2. **Automated Fallback**:
   The adapter `CloudRunJobAdapter` automatically detects local development when `MICHITO_ENV=local` or when Google Application Default Credentials (`ADC`) are absent, invoking the worker synchronously or via thread fallback for rapid iteration without hitting GCP.
