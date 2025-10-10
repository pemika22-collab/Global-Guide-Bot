#!/usr/bin/env python3
"""
Demo Flow 4: Cultural Intelligence with Real API
===============================================

This demo shows the cultural intelligence capabilities using the real AgentCore system.
It demonstrates AI-powered cultural guidance for Thai customs and etiquette.

Features:
- Temple etiquette guidance with AI reasoning
- Social customs and wai gesture explanations
- Real AgentCore API integration with Cultural Agent
- Live Amazon Nova Pro cultural intelligence
"""

import json
import time
import asyncio
import os
import sys
import random
from datetime import datetime
import importlib.util

# Simple color class without external dependencies
class Colors:
    HEADER = '\033[95m\033[1m'
    BLUE = '\033[94m\033[1m'
    CYAN = '\033[96m\033[1m'
    GREEN = '\033[92m\033[1m'
    YELLOW = '\033[93m\033[1m'
    RED = '\033[91m\033[1m'
    RESET = '\033[0m'

def load_agentcore_module(module_name, file_path):
    """Load AgentCore module using importlib to bypass 'lambda' keyword issue"""
    try:
        # Read the file and modify imports
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Replace relative imports with absolute imports
        content = content.replace('from .base_agent import BaseAgent', 'from base_agent import BaseAgent')
        content = content.replace('from . import base_agent', 'import base_agent')
        content = content.replace('from .memory import', 'from memory import')
        content = content.replace('from .strands import', 'from strands import')
        
        # Handle try/except import blocks
        if 'from .memory import AgentMemory' in content:
            content = content.replace('from .memory import AgentMemory', 'from memory import AgentMemory')
        if 'from .strands import StrandManager, StrandType' in content:
            content = content.replace('from .strands import StrandManager, StrandType', 'from strands import StrandManager, StrandType')
        
        # Create a temporary module
        spec = importlib.util.spec_from_loader(module_name, loader=None)
        module = importlib.util.module_from_spec(spec)
        
        # Add to sys.modules to handle imports
        sys.modules[module_name] = module
        sys.modules[f"agentcore.{module_name}"] = module
        
        # Execute the modified code
        exec(content, module.__dict__)
        
        return module
    except Exception as e:
        print(f"❌ Failed to load {module_name}: {e}")
        return None

def print_system_status(message):
    """Print system status message"""
    print(f"\n{Colors.CYAN}⚙️  System:{Colors.RESET} {message}")

async def setup_agentcore():
    """Setup AgentCore system with proper module loading"""
    print_system_status("Loading AgentCore modules...")
    
    try:
        # Load base agent first
        base_agent_module = load_agentcore_module("base_agent", "src/lambda/agentcore/base_agent.py")
        
        if not base_agent_module:
            return None, None
        
        # Create mock agentcore package for imports
        import types
        agentcore_package = types.ModuleType("agentcore")
        agentcore_package.base_agent = base_agent_module
        sys.modules["agentcore"] = agentcore_package
        
        # Load memory and strands modules first
        memory_module = load_agentcore_module("memory", "src/lambda/agentcore/memory.py")
        strands_module = load_agentcore_module("strands", "src/lambda/agentcore/strands.py")
        
        if not all([memory_module, strands_module]):
            return None, None
        
        # Load enhanced orchestrator
        orchestrator_module = load_agentcore_module("enhanced_orchestrator", "src/lambda/agentcore/enhanced_orchestrator.py")
        
        if not orchestrator_module:
            return None, None
        
        # Load agents
        tourist_module = load_agentcore_module("tourist_agent", "src/lambda/agentcore/tourist_agent.py")
        cultural_module = load_agentcore_module("cultural_agent", "src/lambda/agentcore/cultural_agent.py")
        guide_module = load_agentcore_module("guide_agent", "src/lambda/agentcore/guide_agent.py")
        booking_module = load_agentcore_module("booking_agent", "src/lambda/agentcore/booking_agent.py")
        
        if not all([tourist_module, cultural_module, guide_module, booking_module]):
            return None, None
        
        # Extract classes
        EnhancedAgentCoreOrchestrator = orchestrator_module.EnhancedAgentCoreOrchestrator
        
        TouristAgent = tourist_module.TouristAgent
        CulturalAgent = cultural_module.CulturalAgent
        GuideAgent = guide_module.GuideAgent
        BookingAgent = booking_module.BookingAgent
        
        print_system_status("✅ AgentCore modules loaded successfully")
        
        # Initialize enhanced system
        orchestrator = EnhancedAgentCoreOrchestrator()
        
        # Create and register agents
        tourist_agent = TouristAgent()
        cultural_agent = CulturalAgent()
        guide_agent = GuideAgent()
        booking_agent = BookingAgent()
        
        orchestrator.register_agent("tourist", tourist_agent)
        orchestrator.register_agent("cultural", cultural_agent)
        orchestrator.register_agent("guide", guide_agent)
        orchestrator.register_agent("booking", booking_agent)
        
        print("✅ Registered touristAgent")
        print("✅ Registered culturalAgent")
        print("✅ Registered guideAgent")
        print("✅ Registered bookingAgent")
        
        print_system_status("✅ AgentCore system initialized with 4 agents")
        
        return orchestrator, {
            'tourist': tourist_agent,
            'cultural': cultural_agent,
            'guide': guide_agent,
            'booking': booking_agent
        }
        
    except Exception as e:
        print(f"{Colors.RED}❌ AgentCore setup failed: {e}{Colors.RESET}")
        return None, None

async def demonstrate_cultural_question(orchestrator, user_id, question, scenario_name):
    """Demonstrate a cultural intelligence question"""
    
    print(f"\n📱 Tourist:")
    print(f"   {question}")
    
    print(f"\n⚙️  System: 🤖 Processing cultural question with AI...")
    
    try:
        print(f"\n" + "=" * 70)
        print(f"🎯 AgentCore Processing Message")
        print(f"User: {user_id}")
        print(f"Message: {question}")
        print("=" * 70)
        
        # Process the cultural question
        response = await orchestrator.process_user_message(
            user_message=question,
            user_id=user_id
        )
        
        # Response ready (logged by orchestrator)
        
        # Display the response
        print(f"\n📱 WhatsApp Bot:")
        bot_message = response.get('message', 'Cultural guidance provided!')
        for line in bot_message.split('\n'):
            if line.strip():
                print(f"   {line}")
        
        # Show AI agents involved
        agents_involved = response.get('agents_involved', [])
        if agents_involved:
            print(f"   🤖 AI Agents: {', '.join(agents_involved)}")
        
        print(f"\n✅ {scenario_name} guidance completed successfully!")
        
        return response
        
    except Exception as e:
        print(f"❌ Error processing cultural question: {str(e)}")
        return None

async def main():
    """Run the cultural intelligence demo with real API calls"""
    
    # Setup AgentCore
    orchestrator, agents = await setup_agentcore()
    
    if not orchestrator:
        print(f"{Colors.RED}❌ Failed to setup AgentCore system")
        print(f"Make sure you're running from the project root directory and AWS credentials are configured.{Colors.RESET}")
        return
    
    print("\n" + "=" * 70)
    print("🏛️  GLOBAL GUIDE BOT - CULTURAL INTELLIGENCE REAL API DEMO")
    print("=" * 70)
    
    print("🎯 Feature: AI-Powered Cultural Intelligence")
    print("🤖 AgentCore System: LIVE Amazon Nova Pro API calls")
    print("📱 Platform: WhatsApp (simulated)")
    print("☁️  AWS Region: eu-west-1")
    print("🎯 Mode: Automated - Cultural guidance demonstrations!")
    
    print(f"\n🎬 Starting Cultural Intelligence Demo...")
    print(f"🇹🇭 Focus: Thai cultural customs and temple etiquette")
    
    # Create user ID for the tourist
    user_id = f"cultural_tourist_{random.randint(1000, 9999)}"
    
    print(f"\n📱 WhatsApp Bot:")
    print(f"   🙏 Sawasdee! Welcome to Global Guide Bot Thailand! 🇹🇭")
    print(f"   I can provide cultural guidance to help you respect Thai customs!")
    print(f"   💬 Ask me about temple etiquette, social customs, or cultural do's and don'ts!")
    
    # Scenario 1: Temple Etiquette
    print(f"\n" + "🏛️ " * 20)
    print(f"📍 SCENARIO 1: TEMPLE ETIQUETTE")
    print(f"🏛️ " * 20)
    
    temple_question = "What should I wear when visiting Thai temples? I don't want to be disrespectful."
    
    temple_response = await demonstrate_cultural_question(
        orchestrator, user_id, temple_question, "Temple etiquette"
    )
    
    # Wait a moment between scenarios
    await asyncio.sleep(2)
    
    # Scenario 2: Social Customs
    print(f"\n" + "🙏 " * 20)
    print(f"📍 SCENARIO 2: SOCIAL CUSTOMS")
    print(f"🙏 " * 20)
    
    social_question = "How do I greet Thai people properly? What is the wai gesture and when should I use it?"
    
    social_response = await demonstrate_cultural_question(
        orchestrator, user_id, social_question, "Social customs"
    )
    
    print(f"\n🎉 CULTURAL INTELLIGENCE DEMO COMPLETED!")
    print(f"✅ The tourist received comprehensive cultural guidance through AI.")
    
    # Demo Summary
    print(f"\n" + "=" * 70)
    print(f"✅ CULTURAL INTELLIGENCE DEMO COMPLETED")
    print("=" * 70)
    
    print(f"🎯 What This Demo Showed:")
    print(f"   • LIVE Amazon Nova Pro cultural intelligence")
    print(f"   • Real AgentCore cultural agent processing")
    print(f"   • Thai temple etiquette and dress code guidance")
    print(f"   • Social customs and wai gesture explanations")
    print(f"   • Proactive cultural mistake prevention")
    print(f"   • Respectful tourism education")
    
    print(f"\n🏛️  Cultural Intelligence Features:")
    print(f"   • Temple etiquette and Buddhist customs")
    print(f"   • Social greeting protocols and wai gesture")
    print(f"   • Dress code guidance for religious sites")
    print(f"   • Cultural sensitivity and respect education")
    print(f"   • Real-time cultural guidance via chat")
    
    print(f"\n🚀 System Performance:")
    print(f"   • Model: eu.amazon.nova-pro-v1:0")
    print(f"   • Region: eu-west-1")
    print(f"   • Agents: 2 active (Tourist, Cultural)")
    print(f"   • Cultural Database: Thai customs and etiquette")
    print(f"   • Mode: Real-time cultural intelligence")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())