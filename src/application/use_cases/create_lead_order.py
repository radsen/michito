from dataclasses import dataclass
from typing import Optional
from src.domain.entities.lead_order import LeadOrder
from src.application.ports.payment_gateway_port import PaymentGatewayPort
from src.application.ports.lead_order_repository_port import LeadOrderRepositoryPort
import uuid

@dataclass
class CreateLeadOrderResponse:
    order_id: str
    checkout_url: str

class CreateLeadOrderUseCase:
    TIER_PRICING = {
        1: 10000 * 100,  # 10,000 COP in cents
        2: 50000 * 100,  # 50,000 COP in cents
        3: 75000 * 100,  # 75,000 COP in cents
    }

    def __init__(self, payment_gateway: PaymentGatewayPort, repository: LeadOrderRepositoryPort, redirect_url: str):
        self.payment_gateway = payment_gateway
        self.repository = repository
        self.redirect_url = redirect_url

    def execute(self, order: LeadOrder) -> CreateLeadOrderResponse:
        # Determine the price based on tier
        tier = order.tier
        amount_in_cents = self.TIER_PRICING.get(tier, self.TIER_PRICING[1])

        # Generate checkout session
        checkout_url = self.payment_gateway.generate_checkout_session(
            order_id=order.id,
            amount_in_cents=amount_in_cents,
            currency="COP",
            redirect_url=self.redirect_url
        )

        # Save order to repository
        self.repository.save(order)

        return CreateLeadOrderResponse(order_id=order.id, checkout_url=checkout_url)
