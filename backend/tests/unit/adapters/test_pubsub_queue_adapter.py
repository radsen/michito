import pytest
from unittest.mock import MagicMock, patch
from google.api_core.exceptions import AlreadyExists, ServiceUnavailable
from src.adapters.queue.pubsub_queue_adapter import PubSubQueueAdapter

@patch("src.adapters.queue.pubsub_queue_adapter.pubsub_v1.PublisherClient")
@patch("src.adapters.queue.pubsub_queue_adapter.pubsub_v1.SubscriberClient")
def test_pubsub_adapter_init(mock_sub, mock_pub):
    mock_pub_client = MagicMock()
    mock_pub.return_value = mock_pub_client
    
    mock_sub_client = MagicMock()
    mock_sub.return_value = mock_sub_client
    
    adapter = PubSubQueueAdapter(project_id="test-project")
    
    mock_pub_client.create_topic.assert_called_once()
    mock_sub_client.create_subscription.assert_called_once()
    
    assert adapter.project_id == "test-project"

@patch("src.adapters.queue.pubsub_queue_adapter.pubsub_v1.PublisherClient")
@patch("src.adapters.queue.pubsub_queue_adapter.pubsub_v1.SubscriberClient")
def test_pubsub_adapter_init_already_exists(mock_sub, mock_pub):
    mock_pub_client = MagicMock()
    mock_pub_client.create_topic.side_effect = AlreadyExists("Topic exists")
    mock_pub.return_value = mock_pub_client
    
    mock_sub_client = MagicMock()
    mock_sub_client.create_subscription.side_effect = AlreadyExists("Subscription exists")
    mock_sub.return_value = mock_sub_client
    
    # Should not raise exception
    adapter = PubSubQueueAdapter(project_id="test-project")
    
    mock_pub_client.create_topic.assert_called_once()
    mock_sub_client.create_subscription.assert_called_once()

@patch("src.adapters.queue.pubsub_queue_adapter.pubsub_v1.PublisherClient")
@patch("src.adapters.queue.pubsub_queue_adapter.pubsub_v1.SubscriberClient")
def test_publish_order(mock_sub, mock_pub):
    mock_pub_client = MagicMock()
    mock_future = MagicMock()
    mock_future.result.return_value = "msg-123"
    mock_pub_client.publish.return_value = mock_future
    mock_pub.return_value = mock_pub_client
    
    adapter = PubSubQueueAdapter(project_id="test-project")
    msg_id = adapter.publish_order({"order_id": "order-1"})
    
    assert msg_id == "msg-123"
    mock_pub_client.publish.assert_called_once()
    
@patch("src.adapters.queue.pubsub_queue_adapter.pubsub_v1.PublisherClient")
@patch("src.adapters.queue.pubsub_queue_adapter.pubsub_v1.SubscriberClient")
def test_listen_orders(mock_sub, mock_pub):
    mock_sub_client = MagicMock()
    
    mock_message = MagicMock()
    mock_message.message.data = b'{"order_id": "order-1"}'
    mock_message.ack_id = "ack-1"
    
    mock_response = MagicMock()
    mock_response.received_messages = [mock_message]
    
    mock_sub_client.pull.return_value = mock_response
    mock_sub.return_value = mock_sub_client
    
    adapter = PubSubQueueAdapter(project_id="test-project")
    
    handler_called = False
    
    def handler(payload):
        nonlocal handler_called
        handler_called = True
        assert payload["order_id"] == "order-1"
        return True
        
    adapter.listen_orders(handler)
    
    assert handler_called
    mock_sub_client.acknowledge.assert_called_once()

@patch("src.adapters.queue.pubsub_queue_adapter.pubsub_v1.PublisherClient")
@patch("src.adapters.queue.pubsub_queue_adapter.pubsub_v1.SubscriberClient")
def test_listen_orders_service_unavailable(mock_sub, mock_pub):
    mock_sub_client = MagicMock()
    mock_sub_client.pull.side_effect = ServiceUnavailable("Service Unavailable")
    mock_sub.return_value = mock_sub_client
    
    adapter = PubSubQueueAdapter(project_id="test-project")
    
    handler_called = False
    def handler(payload):
        nonlocal handler_called
        handler_called = True
        return True
        
    # Should not raise exception
    adapter.listen_orders(handler)
    
    assert not handler_called
