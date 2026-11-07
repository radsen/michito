with open("src/entrypoints/container.py", "r") as f:
    content = f.read()

import_statement = "from src.adapters.queue.pubsub_queue_adapter import PubSubQueueAdapter\n"

# Insert import at the top
content = import_statement + content

# Add the queue adapter to the Container init
init_marker = "self.repository = MemoryRepositoryAdapter()"
init_addition = """
        try:
            self.queue_adapter = PubSubQueueAdapter()
        except Exception as e:
            # Fallback or log if we can't connect, e.g. local dev without emulator
            import logging
            logging.getLogger(__name__).warning(f"Failed to initialize PubSub adapter: {e}")
            self.queue_adapter = None
"""

content = content.replace(init_marker, init_marker + init_addition)

with open("src/entrypoints/container.py", "w") as f:
    f.write(content)
