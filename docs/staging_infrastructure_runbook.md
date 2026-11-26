# Michito Staging Infrastructure & Deployment Runbook 🇨🇴

This document contains the complete step-by-step log of commands executed to provision the staging environment for Michito on Google Cloud Platform (GCP). All secrets, passwords, tokens, and sensitive identifiers have been sanitized and obfuscated.

---

## 1. Project Initialization & Billing Setup

### 1.1 Verify Active Authentication
Verify the active GCP identity executing the setup:
```bash
# List authenticated accounts and active credential
gcloud auth list
```

### 1.2 Locate Billing Account
Locate the valid billing account ID linked to your identity:
```bash
# Retrieve available billing accounts
gcloud billing accounts list
```

### 1.3 Create the Staging GCP Project
Create the isolated GCP project for staging workloads:
```bash
# Create project with a human-readable name
gcloud projects create michito-staging --name="Michito Staging"
```

### 1.4 Link Billing Account
Attach billing to enable resource creation (Cloud SQL, Cloud Run, Cloud Build):
```bash
# Link the project to your billing account ID (obfuscated)
gcloud billing projects link michito-staging --billing-account=[REDACTED_BILLING_ACCOUNT_ID]
```

### 1.5 Set Active Project Context
Set the default active project in gcloud CLI configuration:
```bash
# Set default project context
gcloud config set project michito-staging
```

---

## 2. Enable Required Google Cloud APIs

Enable all managed services required for serverless compute, relational storage, secret storage, remote image builds, object storage, and messaging:
```bash
# Enable foundational APIs in a single batch operation
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  storage.googleapis.com \
  pubsub.googleapis.com \
  compute.googleapis.com \
  --project=michito-staging
```

---

## 3. Artifact Registry (Container Storage)

Create an Artifact Registry repository in `us-central1` to store container images built remotely by Cloud Build:
```bash
# Create Docker repository for backend and web containers
gcloud artifacts repositories create michito-repo \
  --repository-format=docker \
  --location=us-central1 \
  --description="Michito Docker Repository" \
  --project=michito-staging
```

---

## 4. Google Cloud Storage Bucket

Create a dedicated bucket for order deliverable files (CSVs, XLSX files, executive teaser PDFs):
```bash
# Create bucket in us-central1 with uniform bucket-level access policy
gcloud storage buckets create gs://michito-staging-deliverables \
  --location=us-central1 \
  --uniform-bucket-level-access \
  --project=michito-staging
```

---

## 5. Google Cloud Pub/Sub Topic

Create the Pub/Sub topic used for asynchronous order fulfillment and queue processing:
```bash
# Create topic for incoming and processed orders
gcloud pubsub topics create michito-orders-staging --project=michito-staging
```

*(Note: The push subscription to the API endpoint is created after the backend Cloud Run service is deployed).*

---

## 6. Google Cloud SQL (PostgreSQL 16)

### 6.1 Provision Cloud SQL Instance
Provision a cost-optimized, persistent PostgreSQL 16 database (`db-f1-micro` Enterprise Edition) to eliminate cold-start latencies on payment webhooks:
```bash
# Provision PostgreSQL 16 micro instance in us-central1
gcloud sql instances create michito-pg-staging \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --edition=ENTERPRISE \
  --region=us-central1 \
  --storage-type=SSD \
  --storage-size=10GB \
  --storage-auto-increase \
  --project=michito-staging
```

### 6.2 Create Database
Create the application database inside the instance:
```bash
# Create logical database 'michito'
gcloud sql databases create michito \
  --instance=michito-pg-staging \
  --project=michito-staging
```

### 6.3 Create Application User (Secure Password Injection)
To avoid exposing plain-text passwords in command history or process inspection tables, inject the password via a temporary JSON flags file:
```bash
# Step 1: Write an ephemeral JSON payload containing the database password
cat <<EOF > /tmp/sql_user_flags.json
{
  "password": "[REDACTED_POSTGRES_APP_PASSWORD]"
}
EOF

# Step 2: Create the database user using the flags file
gcloud sql users create michito_app \
  --instance=michito-pg-staging \
  --flags-file=/tmp/sql_user_flags.json \
  --project=michito-staging

# Step 3: Immediately remove the ephemeral file
rm -f /tmp/sql_user_flags.json
```

---

## 7. Google Secret Manager

Store all sensitive environment variables in Secret Manager. Passing secrets via standard input (`--data-file=-`) prevents secret values from appearing in shell command logs.

### 7.1 Database Connection String
```bash
# Unix socket connection string utilized by Cloud Run Cloud SQL Proxy
echo -n "postgresql+asyncpg://michito_app:[REDACTED_POSTGRES_APP_PASSWORD]@/michito?host=/cloudsql/michito-staging:us-central1:michito-pg-staging" | \
  gcloud secrets create DATABASE_URL --data-file=- --project=michito-staging
```

### 7.2 Payment Gateway Secrets (Wompi 🇨🇴)
```bash
# Wompi sandbox public key
echo -n "[REDACTED_WOMPI_PUBLIC_KEY]" | \
  gcloud secrets create WOMPI_PUBLIC_KEY --data-file=- --project=michito-staging

# Wompi integrity secret used to sign transaction integrity hashes
echo -n "[REDACTED_WOMPI_INTEGRITY_SECRET]" | \
  gcloud secrets create WOMPI_INTEGRITY_SECRET --data-file=- --project=michito-staging

# Wompi event secret used to validate incoming webhook HMAC signatures
echo -n "[REDACTED_WOMPI_EVENTS_SECRET]" | \
  gcloud secrets create WOMPI_EVENTS_SECRET --data-file=- --project=michito-staging
```

### 7.3 Operational Webhooks & AI Services
```bash
# Critical alert webhook (Slack / Discord / Telegram)
echo -n "[REDACTED_ALERT_WEBHOOK_URL]" | \
  gcloud secrets create ALERT_WEBHOOK_URL --data-file=- --project=michito-staging

# Commercial orders feed webhook
echo -n "[REDACTED_ORDERS_FEED_WEBHOOK_URL]" | \
  gcloud secrets create ORDERS_FEED_WEBHOOK_URL --data-file=- --project=michito-staging

# Google Gemini API key for automated lead scoring and copy generation
echo -n "[REDACTED_GEMINI_API_KEY]" | \
  gcloud secrets create GEMINI_API_KEY --data-file=- --project=michito-staging
```

---

## 8. IAM Role Bindings & Permissions

### 8.1 Identify Project Number & Service Accounts
```bash
# Extract numeric project identifier
PROJECT_NUMBER=$(gcloud projects describe michito-staging --format='value(projectNumber)')
```

### 8.2 Grant Permissions to Cloud Run Compute Service Account
Cloud Run executes under the Compute default service account (`${PROJECT_NUMBER}-compute@developer.gserviceaccount.com`). Grant it access to Secret Manager, Cloud SQL, Cloud Storage, and Pub/Sub:
```bash
# Secret Manager Secret Accessor (to read secrets on container startup)
gcloud projects add-iam-policy-binding michito-staging \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Cloud SQL Client (to connect via Cloud SQL Proxy unix socket)
gcloud projects add-iam-policy-binding michito-staging \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/cloudsql.client"

# Storage Object Admin (to write and read deliverables in GCS)
gcloud projects add-iam-policy-binding michito-staging \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

# Pub/Sub Publisher & Subscriber (to publish and consume order messages)
gcloud projects add-iam-policy-binding michito-staging \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/pubsub.publisher"

gcloud projects add-iam-policy-binding michito-staging \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/pubsub.subscriber"
```

### 8.3 Grant Permissions to Cloud Build Service Account
Cloud Build requires permission to push built container images to Artifact Registry:
```bash
# Artifact Registry Writer role for Cloud Build
gcloud projects add-iam-policy-binding michito-staging \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"
```

---

## 9. Remote Container Builds via Cloud Build

Because local Docker was not installed on the development workstation, all container images were built remotely on Google Cloud Build using `gcloud builds submit`.

### 9.1 Build Backend API Container
```bash
# Submit backend context to Cloud Build and tag image in Artifact Registry
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/michito-staging/michito-repo/michito-api:latest \
  -f backend/Dockerfile . \
  --project=michito-staging
```

### 9.2 Build Web Client Container
```bash
# Submit web client context to Cloud Build and tag image in Artifact Registry
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/michito-staging/michito-repo/michito-web:latest \
  -f clients/web/Dockerfile . \
  --project=michito-staging
```

---

## 10. Cloud Run Service Deployment

### 10.1 Deploy Backend API Service
Deploy `michito-api` with Cloud SQL connection socket and secrets mapped to container environment variables:
```bash
gcloud run deploy michito-api \
  --image=us-central1-docker.pkg.dev/michito-staging/michito-repo/michito-api:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=5 \
  --memory=1Gi \
  --cpu=1 \
  --add-cloudsql-instances=michito-staging:us-central1:michito-pg-staging \
  --set-env-vars=ENVIRONMENT=staging,DEFAULT_COUNTRY=CO,DELIVERABLES_BUCKET=michito-staging-deliverables,PUBSUB_ORDER_TOPIC=michito-orders-staging \
  --set-secrets=DATABASE_URL=DATABASE_URL:latest,WOMPI_PUBLIC_KEY=WOMPI_PUBLIC_KEY:latest,WOMPI_INTEGRITY_SECRET=WOMPI_INTEGRITY_SECRET:latest,WOMPI_EVENTS_SECRET=WOMPI_EVENTS_SECRET:latest,ALERT_WEBHOOK_URL=ALERT_WEBHOOK_URL:latest,ORDERS_FEED_WEBHOOK_URL=ORDERS_FEED_WEBHOOK_URL:latest,GEMINI_API_KEY=GEMINI_API_KEY:latest \
  --project=michito-staging
```
*Resulting Endpoint*: `https://michito-api-limgi3puaq-uc.a.run.app`

### 10.2 Deploy Web Client Service
Deploy `michito-web` pointing its Nginx reverse proxy to the backend API URL:
```bash
gcloud run deploy michito-web \
  --image=us-central1-docker.pkg.dev/michito-staging/michito-repo/michito-web:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --min-instances=0 \
  --max-instances=5 \
  --memory=256Mi \
  --cpu=1 \
  --set-env-vars=BACKEND_URL=https://michito-api-limgi3puaq-uc.a.run.app \
  --project=michito-staging
```
*Resulting Endpoint*: `https://michito-web-limgi3puaq-uc.a.run.app`

---

## 11. Wire Pub/Sub Push Subscription

Configure Pub/Sub to push queued order events directly into the backend API webhook:
```bash
# Create push subscription delivering to Cloud Run API endpoint
gcloud pubsub subscriptions create michito-worker-sub-staging \
  --topic=michito-orders-staging \
  --push-endpoint=https://michito-api-limgi3puaq-uc.a.run.app/api/v1/pubsub/orders \
  --ack-deadline=60 \
  --project=michito-staging
```

---

## 12. Automated Deployment Script (`deploy.sh`)

All the build and deployment steps above have been unified into `deploy.sh`. For subsequent staging updates, simply run:

```bash
# Deploy both backend and web to staging
./deploy.sh staging

# Deploy only the backend API
./deploy.sh staging --only-api

# Deploy only the web frontend
./deploy.sh staging --only-web
```

---

## 13. Health & Connectivity Verification

### 13.1 Backend Health & Docs
```bash
# Verify API OpenAPI documentation availability
curl -s -o /dev/null -w "%{http_code}\n" https://michito-api-limgi3puaq-uc.a.run.app/docs
# Expected: 200
```

### 13.2 Web Frontpage & Reverse Proxy Check
```bash
# Verify SPA index delivery
curl -s -o /dev/null -w "%{http_code}\n" https://michito-web-limgi3puaq-uc.a.run.app/
# Expected: 200

# Verify Nginx reverse proxy to database query through Cloud SQL
curl -s https://michito-web-limgi3puaq-uc.a.run.app/api/v1/taxonomy/roles?limit=2
# Expected: JSON response containing role definitions
```

### 13.3 Test Order Creation & Processing
```bash
# Submit sample order to test full quotation, database persistence, and deliverable creation
curl -s -X POST https://michito-api-limgi3puaq-uc.a.run.app/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "client": {
      "name": "Staging Verification Test",
      "email": "test@michito.co",
      "phone": "+573001234567"
    },
    "request": {
      "city": "Medellín",
      "tier": 2,
      "limit": 10
    }
  }'
```
Expected output: JSON containing order ID (e.g. `ord_...`), calculated price, teaser summary, and deliverable file paths.

---

## 14. Decoupled Cloud Run Jobs Operational Commands

### 14.1 Create or Update the Batch Harvesting Job
```bash
# Deploy batch worker container as Cloud Run Job
gcloud run jobs deploy michito-batch-worker \
  --image=us-central1-docker.pkg.dev/michito-staging/michito-repo/backend:staging \
  --region=us-central1 \
  --set-cloudsql-instances=michito-staging:us-central1:michito-pg-staging \
  --set-env-vars=DATABASE_URL="postgresql://michito_user:[DB_PASS]@/michito_db?host=/cloudsql/michito-staging:us-central1:michito-pg-staging",GCS_DELIVERABLES_BUCKET="michito-staging-deliverables",MICHITO_ENV="staging",GOOGLE_CLOUD_PROJECT="michito-staging",GCP_REGION="us-central1" \
  --max-retries=2 \
  --task-timeout=1800s \
  --project=michito-staging
```

### 14.2 Manually Execute Job for an Order
```bash
# Execute harvesting for a specific order ID
gcloud run jobs execute michito-batch-worker \
  --region=us-central1 \
  --project=michito-staging \
  --args="--order-id=ord_staging_test_101"
```

### 14.3 Inspect Job Logs in Real Time
```bash
# Stream execution logs
gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="michito-batch-worker"' \
  --project=michito-staging \
  --limit=50 \
  --format="value(textPayload)"
```

---

## 15. Quality Gate & Automated Test Battery Commands

Run the full testing battery before any promotion to staging or production:

```bash
# 1. Complete Automated Backend Test Battery (321 tests across unit, integration, and e2e)
PYTHONPATH=backend ALLOW_STATUTORY_FALLBACK=true TESTING=1 venv/bin/pytest backend/tests/unit backend/tests/integration backend/tests/e2e -q

# 2. Web Frontend Playwright E2E Suite
cd clients/web && npm run build
```

All 321 backend tests must pass (100% green) before executing `./deploy.sh staging all` or `./deploy.sh prod all`.

---

## 16. Dynamic Relational Taxonomy Migration & Multi-Country Architecture

Michito deploys a normalized 9-table relational taxonomy engine directly in PostgreSQL. It eliminates hardcoded taxonomy catalogs from source code, enabling autonomous agents to learn new economic patterns and buying persona associations at runtime without requiring application re-deployment.

### 16.1 Automated Idempotent Migration
The migration runs automatically inside the FastAPI lifespan handler and the `OrderWorkerDaemon` on startup. To execute it manually against any database:
```bash
# Migrate and seed all 9 taxonomy tables
python backend/scripts/migrate_relational_taxonomy.py --db-url="postgresql+psycopg://user:pass@host:5432/dbname"
```

### 16.2 The 9 Relational Taxonomy Tables
| Table | Rows | Purpose |
| :--- | :---: | :--- |
| `taxonomy_locations` | 23 | Administrative territories, metro clusters & concentric expansion rings |
| `taxonomy_roles` | 34 | Normalized B2B corporate personas and seniority levels |
| `taxonomy_sectors` | 12 | Latin American macro economic sectors (ISIC Section Mappings) |
| `taxonomy_isic_codes` | 247 | Universal UN ISIC Rev. 4 / DANE CIIU economic activities |
| `taxonomy_isic_country_registries` | 739 | Cross-country adaptations (DANE Colombia, DGII DR, SuperCias Ecuador) |
| `taxonomy_isic_role_links` | 3,943 | Country-calibrated buying persona links (typical buyers per activity) |
| `taxonomy_sector_isic_links` | 717 | Sector-to-activity assignments and division memberships |
| `taxonomy_semantic_patterns` | 28+ | Seed & agent-learned regex patterns for sub-millisecond classification |
| `taxonomy_exclusion_rules` | 18 | Bankrupt/liquidator placeholders and cross-sector contamination rules |

### 16.3 Production Live SODA API Configuration
Staging and production containers run with `SODA_USE_LIVE_API=true` injected via `deploy.sh`. This enables live querying against official government SODA endpoints (SECOP II, Supersociedades) with SODA `$offset` pagination ladders and concentric metropolitan valley expansions.


