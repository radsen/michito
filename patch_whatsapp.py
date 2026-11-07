import re

with open("src/entrypoints/api/main.py", "r") as f:
    content = f.read()

new_webhook = """
@app.post("/api/v1/webhooks/whatsapp")
def whatsapp_webhook(payload: dict):
    from clients.whatsapp.bot_service import WhatsAppBotService
    
    # Very basic parser for Meta Cloud API structure
    try:
        if "entry" in payload:
            for entry in payload["entry"]:
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    if "messages" in value:
                        for msg in value["messages"]:
                            from_number = msg.get("from")
                            text = msg.get("text", {}).get("body", "")
                            
                            bot = WhatsAppBotService()
                            response = bot.handle_incoming_message(from_number, text)
                            # In a real system, we'd send 'response' to Meta/Twilio API here
                            logger.info(f"Bot response: {response}")
    except Exception as e:
        logger.error(f"Error processing WhatsApp Webhook: {e}")
        
    return {"status": "ok"}
"""

content = re.sub(
    r'@app\.post\("/api/v1/webhooks/whatsapp"\)\s*def whatsapp_webhook\(payload: dict\):\s*return \{"status": "ok"\}',
    new_webhook.strip(),
    content
)

with open("src/entrypoints/api/main.py", "w") as f:
    f.write(content)
