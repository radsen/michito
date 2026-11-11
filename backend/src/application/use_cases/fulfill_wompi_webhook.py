from src.application.ports.payment_gateway_port import PaymentGatewayPort
from src.application.ports.lead_order_repository_port import LeadOrderRepositoryPort

class FulfillPaymentWebhookUseCase:
    """Handles incoming Wompi payment webhook events.
    
    TODO(contingency-02): Implement an idempotent Payment Reconciliation Job (scheduled every 10m)
    that queries Wompi's GET /v1/transactions/{id} for orders stuck in awaiting_payment > 15m to
    guarantee order fulfillment even if Cloud Run experiences a cold-start timeout during webhook delivery.
    """
    def __init__(self, payment_gateway: PaymentGatewayPort, repository: LeadOrderRepositoryPort):
        self.payment_gateway = payment_gateway
        self.repository = repository

    def execute(self, event_data: dict, signature: str) -> bool:
        # Verify signature
        is_valid = self.payment_gateway.verify_webhook_signature(event_data, signature)
        if not is_valid:
            return False

        # Extract transaction info
        try:
            data = event_data.get("data", {})
            transaction = data.get("transaction", {})
            
            status = transaction.get("status", "")
            reference = transaction.get("reference", "")

            if status != "APPROVED":
                # We only fulfill if APPROVED
                # Could update status to FAILED or similar, but for now we only process approvals
                return True # We successfully processed the webhook, even if it wasn't an approval
            
            order = self.repository.get_by_id(reference)
            if not order:
                return False
                
            order.status = "UNLOCKED"
            self.repository.save(order)
            return True

        except Exception:
            return False
