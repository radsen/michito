from typing import Dict, Any
import logging

from src.application.ports.delivery_port import DeliveryPort
# Using a duck-typed repository that must have get_order(order_id)
# This could be SqlOrderAdapter or similar

logger = logging.getLogger(__name__)

class DeliverOrderUseCase:
    def __init__(self, delivery_port: DeliveryPort, order_repository: Any):
        self.delivery_port = delivery_port
        self.order_repository = order_repository

    def execute(self, order_id: str) -> bool:
        order = self.order_repository.get_order(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        status = order.get("status")
        if status != "paid":
            raise ValueError("Order not paid")
            
        success = self.delivery_port.send_delivery(order)
        if not success:
            logger.error(f"Failed to deliver order {order_id}")
            return False
            
        logger.info(f"Successfully delivered order {order_id}")
        return True
