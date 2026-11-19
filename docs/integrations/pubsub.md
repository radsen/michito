# Google Cloud Pub/Sub Integration Runbook
*Document Version: 1.0 • Decoupled Queue Protocol • November 2026*

This guide details how Google Cloud Pub/Sub decouples client order submissions from the heavy background harvesting, SMTP verification, and financial underwriting pipeline.

---

## 1. Overview & Architecture

When a client submits an order via the web portal or API, the HTTP request immediately returns an estimated completion time and order ID in **under 200ms**. The payload is published to Google Cloud Pub/Sub, which asynchronously invokes the worker via a push subscription.

### Topology

```text
[ Web Client / API ]
         │
         │  POST /api/v1/orders/prospecting
         ▼
[ FastAPI Container (Cloud Run) ]
         │
         │  Publishes JSON envelope
         ▼
[ Pub/Sub Topic: michito-orders-staging ]
         │
         │  Push Subscription (Ack Deadline: 600 seconds)
         ▼
[ Push Endpoint: POST /api/v1/pubsub/orders ]
         │
         │  Validates envelope & decodes order_id
         ▼
[ OrderWorkerDaemon / GenerateProspectsUseCase ]
   ├── Step 1: Harvest official public registries (SECOP II, SERCOP, DGCP)
   ├── Step 2: Socket SMTP MX DNS handshake (RCPT TO) on port 25
   ├── Step 3: Tier 3 legal & financial underwriting
   ├── Step 4: Package XLSX, PDF Dossier, and CRM CSV
   └── Step 5: Upload deliverables to Google Cloud Storage (gs://...)
```

---

## 2. Pub/Sub Resources & Configuration

### Resource Names by Environment

| Resource | Staging (`michito-staging`) | Production (`michito-prod`) |
| :--- | :--- | :--- |
| **Topic Name** | `michito-orders-staging` | `michito-orders-prod` |
| **Subscription Name**| `michito-worker-sub-staging` | `michito-worker-sub-prod` |
| **Push Endpoint** | `https://michito-api-limgi3puaq-uc.a.run.app/api/v1/pubsub/orders` | `https://api.michito.co/api/v1/pubsub/orders` |
| **Ack Deadline** | **600 seconds** (10 minutes) | **600 seconds** (10 minutes) |
| **Retry Policy** | Immediate exponential backoff | Immediate exponential backoff |
| **Dead-Letter Topic**| `michito-orders-staging-dlq` | `michito-orders-prod-dlq` |

### Why the 600s Ack Deadline is Critical

A 100-lead Tier 2 order performs 100+ live network queries (SECOP SODA API lookups, DNS MX checks, SMTP socket handshakes, and GCS uploads) which typically complete in **3 to 5 minutes**. 

Google Cloud Pub/Sub's default ack deadline is only **10 seconds**. If the deadline is not extended to 600s, Pub/Sub will assume the worker died, re-deliver the message to another container instance, and trigger duplicate parallel processing.

---

## 3. Order Message Schema

Messages published to the topic contain a base64-encoded JSON payload matching `CreateOrderRequest`:

```json
{
  "order_id": "ord_20261117_cd80b8",
  "client": {
    "name": "Andrés Londoño",
    "email": "auxiliar.operativo@tinkko.com",
    "phone": "+573102106958",
    "channel": "web_portal"
  },
  "request": {
    "campaign_id": "universal_prospecting",
    "city": "Medellín",
    "country": "CO",
    "limit": 100,
    "tier": 2,
    "offer_description": "Dame espacios de coworkings en Colombia con teléfonos y correos",
    "target_roles": ["Gerente General", "Director Comercial"],
    "target_ciiu_codes": ["6820", "5121"]
  },
  "created_at": "2026-11-18T10:30:00Z"
}
```

---

## 4. Manual Order Re-Run via CLI

If an order ever encounters a network timeout or needs to be re-run manually:

```bash
# Push directly to the staging topic
gcloud pubsub topics publish michito-orders-staging \
  --project=michito-staging \
  --message='{"order_id": "ord_20261117_cd80b8"}'
```

Alternatively, use the repository script:
```bash
./scripts/rerun_order.sh ord_20261117_cd80b8
```

---

## 5. Security: Pub/Sub Push Authentication (Track E)

Before public launch, the push subscription should be secured with Google OIDC Service Account tokens:
1. Create a dedicated service account: `pubsub-invoker@michito-staging.iam.gserviceaccount.com`.
2. Grant `roles/run.invoker` on the Cloud Run API service.
3. Configure the push subscription to attach an OIDC token matching the service account email.
4. Verify the Bearer token in `/api/v1/pubsub/orders`.
