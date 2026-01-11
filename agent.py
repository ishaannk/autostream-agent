"""
AutoStream Conversational AI Agent
Built with LangGraph for state management and conversation flow
"""

import json
import os
from typing import TypedDict, Annotated, Literal
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import operator

# Load knowledge base
def load_knowledge_base():
    with open('knowledge_base.json', 'r') as f:
        return json.load(f)

KB = load_knowledge_base()

# Mock API function for lead capture
def mock_lead_capture(name: str, email: str, platform: str):
    """Mock function to simulate lead capture API call"""
    print(f"\n{'='*50}")
    print(f"✅ Lead captured successfully!")
    print(f"{'='*50}")
    print(f"Name: {name}")
    print(f"Email: {email}")
    print(f"Platform: {platform}")
    print(f"{'='*50}\n")
    return {"status": "success", "message": f"Lead {name} captured successfully"}

# State definition
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    intent: str
    lead_data: dict
    awaiting_info: str  # Which info we're waiting for: 'name', 'email', 'platform', or None

# Initialize LLM
llm = ChatAnthropic(
    model="claude-3-haiku-20240307",
    temperature=0.7,
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

# RAG function - retrieve relevant knowledge
def retrieve_knowledge(query: str) -> str:
    """Simple keyword-based retrieval from knowledge base"""
    query_lower = query.lower()
    relevant_info = []
    
    # Check for pricing queries
    if any(word in query_lower for word in ['price', 'pricing', 'cost', 'plan', 'how much']):
        basic = KB['pricing']['basic_plan']
        pro = KB['pricing']['pro_plan']
        relevant_info.append(f"\n**Pricing Plans:**\n")
        relevant_info.append(f"📦 **{basic['name']}**: {basic['price']}")
        relevant_info.append(f"   • {', '.join(basic['features'])}")
        relevant_info.append(f"\n🚀 **{pro['name']}**: {pro['price']}")
        relevant_info.append(f"   • {', '.join(pro['features'])}")
    
    # Check for refund/policy queries
    if any(word in query_lower for word in ['refund', 'policy', 'cancel', 'money back']):
        relevant_info.append(f"\n**Refund Policy**: {KB['policies']['refund_policy']}")
    
    # Check for support queries
    if any(word in query_lower for word in ['support', 'help', 'customer service']):
        relevant_info.append(f"\n**Support**:")
        relevant_info.append(f"   • Basic Plan: {KB['policies']['support']['basic']}")
        relevant_info.append(f"   • Pro Plan: {KB['policies']['support']['pro']}")
    
    # Check for feature queries
    if any(word in query_lower for word in ['feature', 'what can', 'capabilities', 'do']):
        relevant_info.append(f"\n**Key Features**:")
        for feature, desc in KB['features'].items():
            relevant_info.append(f"   • {desc}")
    
    # General info about AutoStream
    if not relevant_info or any(word in query_lower for word in ['what is', 'tell me about', 'about']):
        relevant_info.insert(0, f"**{KB['company_name']}**: {KB['description']}")
    
    return '\n'.join(relevant_info) if relevant_info else ""

# Intent classification
def classify_intent(state: AgentState) -> str:
    """Classify user intent based on conversation"""
    if not state["messages"]:
        return "greeting"
    
    last_message = state["messages"][-1].content.lower()
    
    # High-intent signals
    high_intent_keywords = [
        'i want', 'sign up', 'get started', 'ready to', 'buy', 'purchase',
        'subscribe', 'try', 'interested in', 'would like', 'go with', 'choose'
    ]
    
    if any(keyword in last_message for keyword in high_intent_keywords):
        return "high_intent"
    
    # Product/pricing inquiry
    inquiry_keywords = [
        'price', 'cost', 'plan', 'feature', 'how much', 'what is',
        'tell me', 'explain', 'support', 'refund', 'policy'
    ]
    
    if any(keyword in last_message for keyword in inquiry_keywords):
        return "product_inquiry"
    
    # Greeting
    greeting_keywords = ['hi', 'hello', 'hey', 'good morning', 'good afternoon']
    if any(keyword in last_message for keyword in greeting_keywords):
        return "greeting"
    
    return "general"

# Node functions
def intent_classifier_node(state: AgentState):
    """Classify the intent of the user's message"""
    intent = classify_intent(state)
    return {"intent": intent}

def greeting_node(state: AgentState):
    """Handle casual greetings"""
    response = (
        "Hello! 👋 Welcome to AutoStream! I'm here to help you with our automated video "
        "editing tools. \n\nWould you like to learn about our pricing plans, features, or "
        "do you have any specific questions?"
    )
    return {"messages": [AIMessage(content=response)]}

def rag_node(state: AgentState):
    """Handle product/pricing inquiries using RAG"""
    last_user_message = state["messages"][-1].content
    
    # Retrieve relevant knowledge
    context = retrieve_knowledge(last_user_message)
    
    # Create prompt with context
    system_prompt = f"""You are a helpful sales assistant for AutoStream, an automated video editing SaaS platform.

Use the following knowledge to answer the user's question:

{context}

Be friendly, concise, and helpful. If the user shows interest in signing up, let them know you can help them get started."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=last_user_message)
    ]
    
    response = llm.invoke(messages)
    return {"messages": [AIMessage(content=response.content)]}

def lead_qualification_node(state: AgentState):
    """Handle high-intent users and collect lead information"""
    lead_data = state.get("lead_data", {})
    awaiting_info = state.get("awaiting_info", None)
    last_message = state["messages"][-1].content
    
    # If we're awaiting specific information
    if awaiting_info:
        if awaiting_info == "name":
            lead_data["name"] = last_message.strip()
            return {
                "lead_data": lead_data,
                "awaiting_info": "email",
                "messages": [AIMessage(content="Great! And what's your email address?")]
            }
        elif awaiting_info == "email":
            lead_data["email"] = last_message.strip()
            return {
                "lead_data": lead_data,
                "awaiting_info": "platform",
                "messages": [AIMessage(content="Perfect! Which platform do you create content for? (e.g., YouTube, Instagram, TikTok, etc.)")]
            }
        elif awaiting_info == "platform":
            lead_data["platform"] = last_message.strip()
            # All info collected - capture lead
            result = mock_lead_capture(
                lead_data["name"],
                lead_data["email"],
                lead_data["platform"]
            )
            return {
                "lead_data": lead_data,
                "awaiting_info": None,
                "messages": [AIMessage(content=f"Awesome! 🎉 I've registered your interest, {lead_data['name']}. Our team will reach out to {lead_data['email']} shortly to get you started with AutoStream for your {lead_data['platform']} content. You're going to love how much time our AI-powered editing saves you!")]
            }
    
    # Starting lead qualification
    response = (
        "That's great! I'd love to help you get started with AutoStream. 🚀\n\n"
        "Let me collect a few quick details. What's your name?"
    )
    return {
        "awaiting_info": "name",
        "messages": [AIMessage(content=response)]
    }

# Routing function
def route_based_on_intent(state: AgentState) -> Literal["greeting", "rag", "lead_qualification"]:
    """Route to appropriate node based on intent"""
    # If we're in the middle of collecting lead info, stay in lead qualification
    if state.get("awaiting_info"):
        return "lead_qualification"
    
    intent = state.get("intent", "general")
    
    if intent == "greeting":
        return "greeting"
    elif intent == "high_intent":
        return "lead_qualification"
    else:  # product_inquiry or general
        return "rag"

# Build the graph
def create_agent_graph():
    """Create the LangGraph workflow"""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("intent_classifier", intent_classifier_node)
    workflow.add_node("greeting", greeting_node)
    workflow.add_node("rag", rag_node)
    workflow.add_node("lead_qualification", lead_qualification_node)
    
    # Add edges
    workflow.set_entry_point("intent_classifier")
    workflow.add_conditional_edges(
        "intent_classifier",
        route_based_on_intent,
        {
            "greeting": "greeting",
            "rag": "rag",
            "lead_qualification": "lead_qualification"
        }
    )
    
    # All nodes end the conversation (waiting for next user input)
    workflow.add_edge("greeting", END)
    workflow.add_edge("rag", END)
    workflow.add_edge("lead_qualification", END)
    
    # Add memory for state persistence
    memory = MemorySaver()
    
    return workflow.compile(checkpointer=memory)

# Main conversation loop
def run_conversation():
    """Run the conversational agent"""
    print("\n" + "="*60)
    print("🎬 AutoStream AI Agent")
    print("="*60)
    print("Type your messages below. Type 'quit' or 'exit' to end.\n")
    
    agent = create_agent_graph()
    config = {"configurable": {"thread_id": "autostream_conversation_1"}}
    
    conversation_state = {
        "messages": [],
        "intent": "",
        "lead_data": {},
        "awaiting_info": None
    }
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("\nAgent: Thank you for chatting with AutoStream! Have a great day! 👋\n")
            break
        
        if not user_input:
            continue
        
        # Add user message to state
        conversation_state["messages"].append(HumanMessage(content=user_input))
        
        # Run the agent
        result = agent.invoke(conversation_state, config)
        
        # Update state with result
        conversation_state.update(result)
        
        # Print agent's response
        if result["messages"]:
            agent_response = result["messages"][-1].content
            print(f"\nAgent: {agent_response}\n")

if __name__ == "__main__":
    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️  Warning: ANTHROPIC_API_KEY not found in environment variables.")
        print("Please set it using: export ANTHROPIC_API_KEY='your-key-here'\n")
    
    run_conversation()
