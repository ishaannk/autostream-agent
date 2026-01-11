"""
Test script to demonstrate AutoStream agent capabilities
Run this to see automated conversation flows
"""

import os
import sys
from agent import create_agent_graph, load_knowledge_base
from langchain_core.messages import HumanMessage, AIMessage

def test_agent():
    """Run automated test scenarios"""
    
    print("\n" + "="*70)
    print("🧪 TESTING AUTOSTREAM AI AGENT")
    print("="*70 + "\n")
    
    # Check API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️  Setting dummy API key for testing (replace with real key for actual use)")
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
    
    agent = create_agent_graph()
    
    # Test Scenario 1: Pricing Inquiry
    print("\n📋 TEST SCENARIO 1: Pricing Inquiry")
    print("-" * 70)
    
    config = {"configurable": {"thread_id": "test_thread_1"}}
    state = {
        "messages": [HumanMessage(content="Hi, tell me about your pricing")],
        "intent": "",
        "lead_data": {},
        "awaiting_info": None
    }
    
    print("User: Hi, tell me about your pricing")
    
    try:
        result = agent.invoke(state, config)
        print(f"Agent: {result['messages'][-1].content}")
        print(f"Intent Detected: {result['intent']}")
    except Exception as e:
        print(f"⚠️  Error (expected if no real API key): {e}")
        print("💡 This demonstrates the conversation flow structure")
    
    # Test Scenario 2: High Intent Lead Flow
    print("\n\n📋 TEST SCENARIO 2: High Intent Lead Qualification")
    print("-" * 70)
    
    config2 = {"configurable": {"thread_id": "test_thread_2"}}
    
    # Simulate full conversation
    conversation_flow = [
        "I want to try the Pro plan for my YouTube channel",
        "Jane Smith",
        "jane@example.com",
        "YouTube"
    ]
    
    state2 = {
        "messages": [],
        "intent": "",
        "lead_data": {},
        "awaiting_info": None
    }
    
    for i, user_msg in enumerate(conversation_flow, 1):
        print(f"\n[Turn {i}]")
        print(f"User: {user_msg}")
        
        state2["messages"].append(HumanMessage(content=user_msg))
        
        try:
            result = agent.invoke(state2, config2)
            state2 = result
            print(f"Agent: {result['messages'][-1].content}")
            
            if result.get('awaiting_info'):
                print(f"→ Awaiting: {result['awaiting_info']}")
        except Exception as e:
            print(f"⚠️  Error: {e}")
            break
    
    # Show knowledge base structure
    print("\n\n📚 KNOWLEDGE BASE STRUCTURE")
    print("-" * 70)
    kb = load_knowledge_base()
    print(f"Company: {kb['company_name']}")
    print(f"Plans: {list(kb['pricing'].keys())}")
    print(f"Basic Plan: {kb['pricing']['basic_plan']['price']}")
    print(f"Pro Plan: {kb['pricing']['pro_plan']['price']}")
    print(f"Refund Policy: {kb['policies']['refund_policy']}")
    
    print("\n\n✅ TESTS COMPLETE")
    print("="*70)
    print("To run the interactive agent, use: python agent.py")
    print("="*70 + "\n")

if __name__ == "__main__":
    test_agent()
