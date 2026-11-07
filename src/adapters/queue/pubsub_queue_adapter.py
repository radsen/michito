import os
import json
import logging
from typing import Dict, Any, Callable
from google.cloud import pubsub_v1
from google.api_core.exceptions import AlreadyExists, RetryError, ServiceUnavailable
import grpc

from src.application.ports.order_queue_port import OrderQueuePort

logger = logging.getLogger(__name__)

class PubSubQueueAdapter(OrderQueuePort):
    def __init__(
        self,
        project_id: str = None,
        topic_id: str = "michito-orders",
        subscription_id: str = "michito-worker-sub"
    ):
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT", "michito-dev")
        self.topic_id = topic_id
        self.subscription_id = subscription_id
        
        # In case we're using emulator
        if "PUBSUB_EMULATOR_HOST" in os.environ:
            logger.info(f"Connecting to Pub/Sub Emulator at {os.environ['PUBSUB_EMULATOR_HOST']}")
            
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(self.project_id, self.topic_id)
        
        self.subscriber = pubsub_v1.SubscriberClient()
        self.subscription_path = self.subscriber.subscription_path(self.project_id, self.subscription_id)
        
        self._ensure_topic_and_subscription()

    def _ensure_topic_and_subscription(self):
        try:
            self.publisher.create_topic(request={"name": self.topic_path})
            logger.info(f"Created topic: {self.topic_path}")
        except AlreadyExists:
            pass
        except Exception as e:
            logger.warning(f"Failed to create topic (may already exist or emulator unreachable): {e}")

        try:
            self.subscriber.create_subscription(
                request={"name": self.subscription_path, "topic": self.topic_path}
            )
            logger.info(f"Created subscription: {self.subscription_path}")
        except AlreadyExists:
            pass
        except Exception as e:
            logger.warning(f"Failed to create subscription (may already exist or emulator unreachable): {e}")
            
    def publish_order(self, order_payload: Dict[str, Any]) -> str:
        data_str = json.dumps(order_payload)
        data_bytes = data_str.encode("utf-8")
        
        try:
            future = self.publisher.publish(self.topic_path, data_bytes)
            message_id = future.result(timeout=10)
            logger.info(f"Published order payload to pubsub, message_id: {message_id}")
            return message_id
        except Exception as e:
            logger.error(f"Failed to publish order: {e}")
            raise RuntimeError(f"Failed to publish order to Pub/Sub: {e}")

    def listen_orders(self, handler: Callable[[Dict[str, Any]], bool], max_messages: int = 1) -> None:
        try:
            response = self.subscriber.pull(
                request={"subscription": self.subscription_path, "max_messages": max_messages},
                timeout=10
            )
            
            ack_ids = []
            for received_message in response.received_messages:
                message = received_message.message
                data_str = message.data.decode("utf-8")
                
                try:
                    payload = json.loads(data_str)
                    success = handler(payload)
                    
                    if success:
                        ack_ids.append(received_message.ack_id)
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    # Acknowledging invalid messages so they don't block the queue
                    ack_ids.append(received_message.ack_id)
                    
            if ack_ids:
                self.subscriber.acknowledge(
                    request={"subscription": self.subscription_path, "ack_ids": ack_ids}
                )
                
        except (ServiceUnavailable, RetryError) as e:
            logger.error(f"Pub/Sub emulator/service unavailable: {e}")
        except Exception as e:
            logger.error(f"Error pulling messages from pubsub: {e}")
