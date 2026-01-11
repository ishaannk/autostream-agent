"""
WhatsApp Webhook Integration Example for AutoStream Agent
This demonstrates how to integrate the agent with WhatsApp using FastAPI and Twilio
"""

from fastapi import FastAPI, Request, Form
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse
from agent import create_agent_graph
from langchain_core.messages import HumanMessage
import json
import redis
from typing import Optional

# Initialize FastAPI app
app = FastAPI()

# Initialize Redis for state persistence (use dict for demo)
# In production: redis_client = redis.Redis(host='localhost', port=6379, db=0)
conversation_states = {}

# Initialize agent
agent_graph = create_agent_graph()

def load_or_create_state(thread_id: str) -> dict:
    """Load existing conversation state or create new one"""
    if thread_id in conversation_states:
        return json.loads(conversation_states[thread_id])
    else:
        return {
            "messages": [],
            "intent": "",
            "lead_data": {},
            "awaiting_info": None
        }

def save_state(thread_id: str, state: dict):
    """Save conversation state to Redis"""
    conversation_states[thread_id] = json.dumps({
        "messages": [{"type": m.type, "content": m.content} for m in state["messages"]],
        "intent": state.get("intent", ""),
        "lead_data": state.get("lead_data", {}),
        "awaiting_info": state.get("awaiting_info")
    })

@app.post("/whatsapp/webhook")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...),
    To: Optional[str] = Form(None),
    MessageSid: Optional[str] = Form(None)
):
    """
    Webhook endpoint for receiving WhatsApp messages from Twilio
    
    Twilio sends POST requests with form data:
    - Body: The message text
    - From: Sender's WhatsApp number (format: whatsapp:+1234567890)
    - To: Your WhatsApp business number
    - MessageSid: Unique message identifier
    """
    
    print(f"\n📱 Received WhatsApp message from {From}")
    print(f"Message: {Body}")
    
    # Create unique thread ID for this user
    thread_id = f"whatsapp_{From}"
    config = {"configurable": {"thread_id": thread_id}}
    
    # Load or create conversation state
    conversation_state = load_or_create_state(thread_id)
    
    # Add user message
    conversation_state["messages"].append(HumanMessage(content=Body))
    
    # Process through agent
    try:
        result = agent_graph.invoke(conversation_state, config)
        
        # Save updated state
        save_state(thread_id, result)
        
        # Extract agent response
        agent_response = result["messages"][-1].content
        
        print(f"🤖 Agent response: {agent_response[:100]}...")
        
    except Exception as e:
        print(f"❌ Error processing message: {e}")
        agent_response = "I'm having trouble processing your message. Please try again."
    
    # Create Twilio response
    resp = MessagingResponse()
    resp.message(agent_response)
    
    return PlainTextResponse(content=str(resp), media_type="application/xml")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "AutoStream WhatsApp Agent"}

@app.post("/whatsapp/status")
async def message_status(request: Request):
    """
    Webhook for message delivery status updates from Twilio
    Statuses: queued, sent, delivered, read, failed, undelivered
    """
    form_data = await request.form()
    message_sid = form_data.get('MessageSid')
    message_status = form_data.get('MessageStatus')
    
    print(f"📊 Message {message_sid} status: {message_status}")
    
    # Log or track delivery status
    return {"status": "ok"}

@app.get("/conversations/{phone_number}")
async def get_conversation_history(phone_number: str):
    """
    Admin endpoint to view conversation history
    For debugging and analytics
    """
    thread_id = f"whatsapp_whatsapp:+{phone_number}"
    
    if thread_id in conversation_states:
        state = json.loads(conversation_states[thread_id])
        return {
            "phone_number": phone_number,
            "message_count": len(state.get("messages", [])),
            "current_intent": state.get("intent"),
            "lead_data": state.get("lead_data"),
            "awaiting_info": state.get("awaiting_info")
        }
    else:
        return {"error": "No conversation found for this number"}

# For local development
if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("🚀 Starting AutoStream WhatsApp Webhook Server")
    print("="*60)
    print("\nEndpoints:")
    print("  POST /whatsapp/webhook  - Receive messages from Twilio")
    print("  POST /whatsapp/status   - Message delivery status")
    print("  GET  /health            - Health check")
    print("\nTo use with Twilio:")
    print("1. Deploy this server to a public URL (e.g., Heroku, Railway, AWS)")
    print("2. Configure Twilio webhook: https://your-domain.com/whatsapp/webhook")
    print("3. Start receiving WhatsApp messages!\n")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
