#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Michito Operations Tool — Order Rerun & Resiliency Trigger
# ==============================================================================
# Triggers order pipeline execution via Pub/Sub or protected API endpoint.
# Usage: ./scripts/rerun_order.sh <order_id> [project_id]
# ==============================================================================

ORDER_ID="${1:-}"
PROJECT_ID="${2:-michito-staging}"
API_BASE="${API_BASE:-https://michito-api-limgi3puaq-uc.a.run.app}"
TOPIC_NAME="michito-orders-staging"

if [ -z "$ORDER_ID" ]; then
    echo "❌ Error: Missing order_id."
    echo "Usage: $0 <order_id> [project_id]"
    echo "Example: $0 ord_20261117_cd80b8"
    exit 1
fi

echo "=================================================================="
echo "  MICHITO ORDER RERUN DISPATCHER"
echo "  Order ID:    ${ORDER_ID}"
echo "  Target GCP:  ${PROJECT_ID}"
echo "  Target API:  ${API_BASE}"
echo "=================================================================="

# 1. Fetch current order status
echo "🔍 [1/3] Inspecting current order state..."
HTTP_STATUS=$(curl -s -o /tmp/order_info.json -w "%{http_code}" "${API_BASE}/api/v1/orders/${ORDER_ID}" || true)

if [ "$HTTP_STATUS" != "200" ]; then
    echo "❌ Order ${ORDER_ID} not found on ${API_BASE} (HTTP ${HTTP_STATUS})."
    exit 1
fi

CLIENT_NAME=$(grep -o '"name":"[^"]*' /tmp/order_info.json | head -1 | cut -d'"' -f4 || echo "Unknown")
CAMPAIGN=$(grep -o '"campaign_id":"[^"]*' /tmp/order_info.json | head -1 | cut -d'"' -f4 || echo "universal_prospecting")
CITY=$(grep -o '"city":"[^"]*' /tmp/order_info.json | head -1 | cut -d'"' -f4 || echo "Medellín")
CURRENT_STATUS=$(grep -o '"status":"[^"]*' /tmp/order_info.json | head -1 | cut -d'"' -f4 || echo "unknown")

echo "   Client:    ${CLIENT_NAME}"
echo "   Campaign:  ${CAMPAIGN} | City: ${CITY}"
echo "   Status:    ${CURRENT_STATUS}"

# 2. Trigger processing via Pub/Sub or API
echo ""
echo "🚀 [2/3] Dispatching execution request..."
ADMIN_KEY="${ADMIN_API_KEY:-}"
if [ -z "$ADMIN_KEY" ] && [ -f .env.stg ]; then
    ADMIN_KEY=$(grep '^ADMIN_API_KEY=' .env.stg | cut -d'=' -f2- | tr -d '"' | tr -d "'" || true)
fi

if [ -n "$ADMIN_KEY" ]; then
    echo "   Triggering worker pipeline via POST /api/v1/orders/${ORDER_ID}/process..."
    TRIGGER_RESP=$(curl -s -X POST "${API_BASE}/api/v1/orders/${ORDER_ID}/process" \
        -H "X-Admin-Key: ${ADMIN_KEY}" \
        -H "Content-Type: application/json" || echo '{"status":"error"}')
    echo "   Worker Pipeline Result: ${TRIGGER_RESP}"
fi

# Also dispatch to Pub/Sub topic if gcloud is configured
if command -v gcloud >/dev/null 2>&1; then
    echo "   Publishing execution message to Pub/Sub topic '${TOPIC_NAME}'..."
    gcloud pubsub topics publish "${TOPIC_NAME}" --message="{\"order_id\": \"${ORDER_ID}\"}" --project="${PROJECT_ID}" >/dev/null 2>&1 || true
fi

# 3. Monitor for completion
echo ""
echo "⏳ [3/3] Polling order progress (up to 90 seconds)..."
sleep 2
for i in {1..30}; do
    ORDER_DATA=$(curl -s "${API_BASE}/api/v1/orders/${ORDER_ID}" || true)
    POLL_STATUS=$(echo "$ORDER_DATA" | grep -o '"status":"[^"]*' | head -1 | cut -d'"' -f4 || echo "unknown")
    QUALIFIED=$(echo "$ORDER_DATA" | grep -o '"total_qualified":[0-9]*' | head -1 | cut -d':' -f2 || echo "0")
    TARGET_LIMIT=$(echo "$ORDER_DATA" | grep -o '"limit":[0-9]*' | head -1 | cut -d':' -f2 || echo "10")

    if [ "$POLL_STATUS" = "awaiting_payment" ] || [ "$POLL_STATUS" = "completed" ] || [ "$POLL_STATUS" = "delivered" ]; then
        if [ "$QUALIFIED" -ge "$TARGET_LIMIT" ] || [ $i -gt 5 ]; then
            echo "   🎉 SUCCESS! Order transitioned to '${POLL_STATUS}' with ${QUALIFIED} qualified leads (Target: ${TARGET_LIMIT})!"
            echo "   Order Tracking URL: https://michito-web-limgi3puaq-uc.a.run.app/?order_id=${ORDER_ID}"
            exit 0
        fi
    fi
    if [ "$POLL_STATUS" = "failed" ] && [ $i -gt 3 ]; then
        ERR_MSG=$(echo "$ORDER_DATA" | grep -o '"error_message":"[^"]*' | head -1 | cut -d'"' -f4 || echo "Unknown error")
        echo "   ⚠️ Order marked as failed. Detail: ${ERR_MSG}"
        exit 1
    else
        echo "   ... Polling ($((i * 3))s): Status = '${POLL_STATUS}', Leads = ${QUALIFIED} / ${TARGET_LIMIT}"
    fi
    sleep 3
done

echo "⚠️ Timed out waiting for completion. Check worker logs on Google Cloud Run."
