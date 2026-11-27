#!/usr/bin/env bash
# ==============================================================================
# Michito B2B Engine — Unified Cloud Deployment Script
# Supports Google Cloud Platform Staging and Production Environments
# ==============================================================================

set -euo pipefail

ENV="${1:-staging}"
TARGET="${2:-all}"
ENV_UPPER="$(echo "${ENV}" | tr '[:lower:]' '[:upper:]')"

# Locate gcloud binary
if command -v gcloud >/dev/null 2>&1; then
    GCLOUD="gcloud"
elif [ -x "/Users/radsen/google-cloud-sdk/bin/gcloud" ]; then
    GCLOUD="/Users/radsen/google-cloud-sdk/bin/gcloud"
else
    echo "ERROR: gcloud CLI not found in PATH or standard installation directory."
    exit 1
fi

case "${ENV}" in
    staging)
        PROJECT_ID="michito-staging"
        REGION="us-central1"
        CLOUDSQL_INSTANCE="${PROJECT_ID}:${REGION}:michito-pg-staging"
        REPO_NAME="michito-repo"
        GCS_BUCKET="michito-staging-deliverables"
        PUBSUB_TOPIC="michito-orders-staging"
        PUBSUB_SUBSCRIPTION="michito-worker-sub-staging"
        API_SERVICE_NAME="michito-api"
        JOB_NAME="michito-batch-worker"
        WEB_SERVICE_NAME="michito-web"
        IMAGE_TAG="staging"
        ;;
    prod|production)
        PROJECT_ID="michito-prod"
        REGION="us-central1"
        CLOUDSQL_INSTANCE="${PROJECT_ID}:${REGION}:michito-pg-prod"
        REPO_NAME="michito-repo"
        GCS_BUCKET="michito-prod-deliverables"
        PUBSUB_TOPIC="michito-orders-prod"
        PUBSUB_SUBSCRIPTION="michito-worker-sub-prod"
        API_SERVICE_NAME="michito-api"
        JOB_NAME="michito-batch-worker"
        WEB_SERVICE_NAME="michito-web"
        IMAGE_TAG="prod"
        ;;
    *)
        echo "Usage: $0 [staging|prod]"
        exit 1
        ;;
esac

REGISTRY_BASE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}"
API_IMAGE="${REGISTRY_BASE}/backend:${IMAGE_TAG}"
WEB_IMAGE="${REGISTRY_BASE}/web:${IMAGE_TAG}"

echo "=============================================================================="
echo " Deploying Michito Engine to [${ENV_UPPER}]"
echo " Project:     ${PROJECT_ID}"
echo " Region:      ${REGION}"
echo " Cloud SQL:   ${CLOUDSQL_INSTANCE}"
echo " Bucket:      gs://${GCS_BUCKET}"
echo " Pub/Sub:     ${PUBSUB_TOPIC} -> ${PUBSUB_SUBSCRIPTION}"
echo "=============================================================================="

# ------------------------------------------------------------------------------
# Load Optional SMTP & Service Overrides from .env.${ENV} / .env.stg
# ------------------------------------------------------------------------------
ENV_OVERRIDE_FILE=".env.${ENV}"
if [ ! -f "${ENV_OVERRIDE_FILE}" ] && [ "${ENV}" = "staging" ] && [ -f ".env.stg" ]; then
    ENV_OVERRIDE_FILE=".env.stg"
fi

EXTRA_ENV_VARS=""
if [ -f "${ENV_OVERRIDE_FILE}" ]; then
    echo "--> Reading environment configurations from ${ENV_OVERRIDE_FILE}..."
    while IFS='=' read -r key val || [ -n "$key" ]; do
        clean_key=$(echo "$key" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
        clean_val=$(echo "$val" | sed -e 's/[[:space:]]*#.*//' -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
        case "$clean_key" in
            SMTP_HOST|SMTP_PORT|SMTP_USER|SMTP_PASSWORD|SMTP_FROM|SMTP_USE_TLS|SMTP_USE_SSL|FRONTEND_URL|DEV_DELIVERY_EMAIL|SECOP_APP_TOKEN|DGCP_API_KEY|ADMIN_API_KEY|STREAM_SECRET_KEY|SLACK_SIGNING_SECRET)
                if [ -n "$clean_val" ]; then
                    EXTRA_ENV_VARS="${EXTRA_ENV_VARS},${clean_key}=${clean_val}"
                fi
                ;;
        esac
    done < "${ENV_OVERRIDE_FILE}"
fi

# ------------------------------------------------------------------------------
# Pre-Deploy Automated Quality Gate
# ------------------------------------------------------------------------------
if [ "${SKIP_TESTS:-false}" != "true" ]; then
    echo ""
    echo "--> Running Pre-Deploy Automated Quality Gate (Unit, Integration & E2E)..."
    PYTEST_BIN="pytest"
    if [ -x "./venv/bin/pytest" ]; then
        PYTEST_BIN="./venv/bin/pytest"
    fi
    TESTING=1 ALLOW_STATUTORY_FALLBACK=true $PYTEST_BIN backend/tests/unit backend/tests/integration backend/tests/e2e -q || {
        echo "ERROR: Quality Gate Failed! Aborting deployment to [${ENV_UPPER}]."
        exit 1
    }
    echo "--> Quality Gate Passed: 100% regression and integrity battery verified."
else
    echo "--> WARNING: Pre-deploy quality gate skipped via SKIP_TESTS=true."
fi

# 1. Ensure project configuration is active
$GCLOUD config set project "${PROJECT_ID}" --quiet

API_URL=""

if [ "${TARGET}" != "--only-web" ] && [ "${TARGET}" != "--only-web-deploy" ]; then
    # 2. Build Backend Docker Image using Cloud Build (No local Docker needed)
    echo ""
    echo "--> [1/4] Building Backend container with Cloud Build..."
    $GCLOUD builds submit . \
        --project="${PROJECT_ID}" \
        --config=/dev/stdin <<EOF
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-t', '${API_IMAGE}', '-f', 'backend/Dockerfile', '.']
images:
- '${API_IMAGE}'
EOF

    # 3. Deploy Backend API to Cloud Run
    echo ""
    echo "--> [2/4] Deploying API service to Cloud Run (${API_SERVICE_NAME})..."
    $GCLOUD run deploy "${API_SERVICE_NAME}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --image="${API_IMAGE}" \
        --platform=managed \
        --allow-unauthenticated \
        --set-cloudsql-instances="${CLOUDSQL_INSTANCE}" \
        --port=8000 \
        --min-instances=0 \
        --max-instances=5 \
        --concurrency=80 \
        --cpu=1 \
        --memory=1Gi \
        --timeout=600s \
        --set-env-vars="ENVIRONMENT=${ENV},GCP_PROJECT_ID=${PROJECT_ID},GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GCS_BUCKET_NAME=${GCS_BUCKET},CLOUD_RUN_JOB_NAME=${JOB_NAME},ENABLE_PUBSUB_QUEUE=true,PUBSUB_TOPIC_ORDERS=${PUBSUB_TOPIC},PUBSUB_SUBSCRIPTION_WORKER=${PUBSUB_SUBSCRIPTION},SODA_USE_LIVE_API=true${EXTRA_ENV_VARS}" \
        --set-secrets="DATABASE_URL=DATABASE_URL:latest,WOMPI_PUBLIC_KEY=WOMPI_PUBLIC_KEY:latest,WOMPI_INTEGRITY_SECRET=WOMPI_INTEGRITY_SECRET:latest,WOMPI_EVENTS_SECRET=WOMPI_EVENTS_SECRET:latest,ALERT_WEBHOOK_URL=ALERT_WEBHOOK_URL:latest,ORDERS_FEED_WEBHOOK_URL=ORDERS_FEED_WEBHOOK_URL:latest,GEMINI_API_KEY=GEMINI_API_KEY:latest" \
        --quiet

    API_URL="$($GCLOUD run services describe "${API_SERVICE_NAME}" --project="${PROJECT_ID}" --region="${REGION}" --format="value(status.url)")"
    echo "Backend API live at: ${API_URL}"

    # 3.1 Deploy Decoupled Ephemeral Batch Harvesting Job
    echo ""
    echo "--> [2b/4] Deploying Decoupled Cloud Run Job (${JOB_NAME})..."
    $GCLOUD run jobs deploy "${JOB_NAME}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --image="${API_IMAGE}" \
        --command="python" \
        --args="-m,src.entrypoints.workers.job_runner" \
        --set-cloudsql-instances="${CLOUDSQL_INSTANCE}" \
        --tasks=1 \
        --max-retries=1 \
        --task-timeout=1800s \
        --cpu=2 \
        --memory=2Gi \
        --set-env-vars="ENVIRONMENT=${ENV},GCP_PROJECT_ID=${PROJECT_ID},GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GCS_BUCKET_NAME=${GCS_BUCKET},CLOUD_RUN_JOB_NAME=${JOB_NAME},SODA_USE_LIVE_API=true${EXTRA_ENV_VARS}" \
        --set-secrets="DATABASE_URL=DATABASE_URL:latest,WOMPI_PUBLIC_KEY=WOMPI_PUBLIC_KEY:latest,WOMPI_INTEGRITY_SECRET=WOMPI_INTEGRITY_SECRET:latest,WOMPI_EVENTS_SECRET=WOMPI_EVENTS_SECRET:latest,ALERT_WEBHOOK_URL=ALERT_WEBHOOK_URL:latest,ORDERS_FEED_WEBHOOK_URL=ORDERS_FEED_WEBHOOK_URL:latest,GEMINI_API_KEY=GEMINI_API_KEY:latest" \
        --quiet

    # 4. Configure Pub/Sub Push Subscription to route orders directly to Cloud Run
    echo ""
    echo "--> [3/4] Configuring Pub/Sub Push Subscription to ${API_URL}/api/v1/pubsub/orders..."
    $GCLOUD pubsub subscriptions update "${PUBSUB_SUBSCRIPTION}" \
        --project="${PROJECT_ID}" \
        --push-endpoint="${API_URL}/api/v1/pubsub/orders" \
        --ack-deadline=600 \
        --quiet || \
    $GCLOUD pubsub subscriptions create "${PUBSUB_SUBSCRIPTION}" \
        --project="${PROJECT_ID}" \
        --topic="${PUBSUB_TOPIC}" \
        --push-endpoint="${API_URL}/api/v1/pubsub/orders" \
        --ack-deadline=600 \
        --quiet
else
    API_URL="$($GCLOUD run services describe "${API_SERVICE_NAME}" --project="${PROJECT_ID}" --region="${REGION}" --format="value(status.url)" 2>/dev/null || true)"
    if [ -z "${API_URL}" ]; then
        echo "ERROR: Backend API not found. Please deploy the API first before running with --only-web."
        exit 1
    fi
    echo "Reusing existing Backend API at: ${API_URL}"
fi

WEB_URL=""
if [ "${TARGET}" != "--only-api" ]; then
    # 5. Build Web SPA Client Docker Image using Cloud Build (reuses existing image if already built)
    if [ "${TARGET}" != "--skip-web-build" ] && [ "${TARGET}" != "--only-web-deploy" ]; then
        echo ""
        echo "--> [4/4] Building Web SPA container with Cloud Build..."
        $GCLOUD builds submit . \
            --project="${PROJECT_ID}" \
            --config=/dev/stdin <<EOF
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-t', '${WEB_IMAGE}', '-f', 'clients/web/Dockerfile', '.']
images:
- '${WEB_IMAGE}'
EOF
    fi

    # 6. Deploy Web Client SPA to Cloud Run
    echo ""
    echo "--> Deploying Web SPA service to Cloud Run (${WEB_SERVICE_NAME})..."
    $GCLOUD run deploy "${WEB_SERVICE_NAME}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --image="${WEB_IMAGE}" \
        --platform=managed \
        --allow-unauthenticated \
        --port=8080 \
        --min-instances=0 \
        --max-instances=3 \
        --cpu=1 \
        --memory=256Mi \
        --set-env-vars="BACKEND_URL=${API_URL}" \
        --quiet

    WEB_URL="$($GCLOUD run services describe "${WEB_SERVICE_NAME}" --project="${PROJECT_ID}" --region="${REGION}" --format="value(status.url)")"
fi

echo ""
echo "=============================================================================="
echo " Deployment Successfully Completed! [${ENV_UPPER}]"
echo " Backend API:  ${API_URL}"
echo " API Docs:     ${API_URL}/docs"
echo " Web Portal:   ${WEB_URL}"
echo " Cloud SQL:    ${CLOUDSQL_INSTANCE}"
echo " Storage:      gs://${GCS_BUCKET}"
echo "=============================================================================="
