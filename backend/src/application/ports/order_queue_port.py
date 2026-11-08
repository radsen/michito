"""
Order Queue Application Port.
Defines the abstract interface for decoupled event-driven message brokers
(Google Cloud Pub/Sub, Redis Streams, or Local In-Memory Queues).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable


class OrderQueuePort(ABC):
    @abstractmethod
    def publish_order(self, order_payload: Dict[str, Any]) -> str:
        """
        Publishes a new prospecting order event to the queue.
        Returns the unique published message ID.
        """
        pass

    @abstractmethod
    def listen_orders(self, handler: Callable[[Dict[str, Any]], bool], max_messages: int = 1) -> None:
        """
        Subscribes to or pulls incoming order events from the queue and routes them to handler.
        """
        pass

