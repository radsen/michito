"""
In-Memory Order Queue Adapter.
Provides zero-dependency, local queueing for development, testing, and single-instance deployments.
"""

import queue
import uuid
from typing import Dict, Any, Callable
from src.application.ports.order_queue_port import OrderQueuePort


class MemoryQueueAdapter(OrderQueuePort):
    def __init__(self):
        self._queue: queue.Queue = queue.Queue()

    def publish_order(self, order_payload: Dict[str, Any]) -> str:
        msg_id = f"msg_{uuid.uuid4().hex[:8]}"
        envelope = {
            "message_id": msg_id,
            "payload": order_payload
        }
        self._queue.put(envelope)
        return msg_id

    def listen_orders(self, handler: Callable[[Dict[str, Any]], bool], max_messages: int = 1) -> None:
        processed = 0
        while not self._queue.empty() and processed < max_messages:
            try:
                envelope = self._queue.get_nowait()
                success = handler(envelope["payload"])
                self._queue.task_done()
                processed += 1
            except queue.Empty:
                break

    # Ergonomic aliases for testing and queue semantics
    def enqueue(self, order_payload: Dict[str, Any]) -> str:
        return self.publish_order(order_payload)

    def size(self) -> int:
        return self._queue.qsize()

    @property
    def qsize(self) -> int:
        return self._queue.qsize()
