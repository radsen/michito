with open("src/entrypoints/api/main.py", "r") as f:
    content = f.read()

old_block = """        try:
            from src.adapters.queue.gcp_pubsub_adapter import GcpPubSubQueueAdapter
            queue_adapter = GcpPubSubQueueAdapter()
            queue_adapter.publish_order({"order_id": order["order_id"]})
        except Exception as e:
            logger.error(f"Failed to publish order {order['order_id']} to queue: {e}")"""

new_block = """        try:
            queue_adapter = app_container.queue_adapter
            if queue_adapter:
                queue_adapter.publish_order({"order_id": order["order_id"]})
            else:
                logger.warning("Queue adapter not initialized. Order saved to DB but not published to Pub/Sub.")
        except Exception as e:
            logger.error(f"Failed to publish order {order['order_id']} to queue: {e}")"""

content = content.replace(old_block, new_block)

with open("src/entrypoints/api/main.py", "w") as f:
    f.write(content)
