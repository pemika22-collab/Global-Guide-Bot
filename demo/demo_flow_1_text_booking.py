#!/usr/bin/env python3
"""
Demo Flow 1: Text-Based Tourist Booking - REAL API CALLS WITH USER INTERACTION
==============================================================================

This demo shows the complete text-based booking flow with REAL AgentCore API calls
and interactive user input for a realistic experience.

Requirements:
- AWS credentials configured
- Amazon Nova Pro access in eu-west-1
- DynamoDB tables (guides, bookings, users, messages)
"""

import json
import time
import asyncio
import os
import sys
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

def print_agent_response(agent_name, message, color=Colors.BLUE):
    """Print formatted agent response"""
    print(f"\n{color}🤖 {agent_name}:{Colors.RESET}")
    print(f"   {message}")
    time.sleep(1)

def print_whatsapp_message(sender, message, color=Colors.CYAN):
    """Print formatted WhatsApp message"""
    print(f"\n{color}📱 {sender}:{Colors.RESET}")
    for line in message.split('\n'):
        if line.strip():
            print(f"   {line}")
    time.sleep(1)

def print_system_status(message):
    """Print system status message"""
    print(f"\n{Colors.CYAN}⚙️  System:{Colors.RESET} {message}")
    time.sleep(0.5)

def get_user_input(prompt, color=Colors.YELLOW):
    """Get user input with colored prompt"""
    print(f"\n{color}👤 {prompt}{Colors.RESET}")
    return input("   > ").strip()

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

async def simulate_conversation_flow(orchestrator):
    """Run interactive conversation flow with real API calls"""
    
    print(f"{Colors.HEADER}")
    print("=" * 70)
    print("🏛️  GLOBAL GUIDE BOT - INTERACTIVE REAL API DEMO")
    print("=" * 70)
    print(f"{Colors.RESET}")
    
    print(f"{Colors.YELLOW}📍 Demo Location: Thailand")
    print(f"🤖 AgentCore System: LIVE Amazon Nova Pro API calls")
    print(f"📱 Platform: WhatsApp (simulated)")
    print(f"☁️  AWS Region: eu-west-1")
    print(f"🎯 Mode: Interactive - YOU control the conversation!{Colors.RESET}")
    
    user_id = "demo_tourist_interactive"
    conversation_context = {}
    
    print(f"\n{Colors.GREEN}🎬 Starting Interactive Demo...")
    print(f"You are a tourist visiting Thailand. Chat with the AI guide bot!")
    print(f"Type 'quit' to exit the demo.{Colors.RESET}")
    
    # Initial greeting with clear guidance
    print_whatsapp_message(
        "WhatsApp Bot", 
        "🙏 Sawasdee! Welcome to Global Guide Bot Thailand! 🇹🇭\n\nI can help you find amazing local guides for your Thailand adventure!\n\n🏙️ Popular destinations: Bangkok, Phuket, Chiang Mai, Pattaya, Krabi\n🎯 Activities: Temple tours, Food tours, Beach tours, Cultural experiences\n\n💬 To get started, tell me where you'd like to go!\n\nExample: \"Hi! I'd like to visit Bangkok\" or \"I want to explore Phuket\"",
        Colors.CYAN
    )
    
    # Show example for user guidance
    print(f"\n{Colors.YELLOW}💡 DEMO GUIDANCE:")
    print(f"   Start with: 'Hi! I'd like to visit [CITY]'")
    print(f"   Cities: Bangkok, Phuket, Chiang Mai, Pattaya, Krabi")
    print(f"   The bot will guide you through the rest!{Colors.RESET}")
    
    message_count = 0
    max_messages = 10  # Prevent infinite loops
    
    while message_count < max_messages:
        message_count += 1
        
        # Provide contextual guidance based on conversation stage
        if message_count == 1:
            guidance = "Start with location (e.g., 'Hi! I'd like to visit Bangkok')"
        else:
            # Dynamic guidance based on what the bot just said
            last_bot_message = conversation_context.get('last_bot_message', '').lower()
            
            if 'when would you like' in last_bot_message or 'provide the date' in last_bot_message:
                guidance = "Provide future date (e.g., 'December 15' or '12/15/2025') - Past dates will be rejected"
            elif 'what activities interest' in last_bot_message or 'activities interest you' in last_bot_message:
                guidance = "Say what you like (e.g., 'temples', 'food tours', 'beaches')"
            elif 'reply with guide name' in last_bot_message or 'found' in last_bot_message and 'guide' in last_bot_message:
                guidance = "Choose a guide by name (e.g., 'Wichai', 'Kanya', 'Somchai') - Check reviews & open video links in browser!"
            elif 'booking summary' in last_bot_message or 'confirm to proceed' in last_bot_message:
                guidance = "Confirm booking (say 'yes' to confirm or 'no' to cancel)"
            else:
                guidance = "Follow the bot's guidance"
        
        # Get user input
        user_message = get_user_input(
            f"Your WhatsApp message (#{message_count}) - {guidance}:",
            Colors.GREEN
        )
        
        if user_message.lower() in ['quit', 'exit', 'stop']:
            print(f"\n{Colors.YELLOW}👋 Thanks for trying the demo! Goodbye!{Colors.RESET}")
            break
            
        if not user_message:
            print(f"{Colors.RED}Please enter a message or 'quit' to exit.{Colors.RESET}")
            continue
        
        # Don't show user message - it's already in the input prompt
        
        try:
            # Process through AgentCore with REAL API calls
            print_system_status("🤖 Processing with AI...")
            
            response = await orchestrator.process_user_message(
                user_message=user_message,
                user_id=user_id,
                conversation_context=conversation_context
            )
            
            # Update conversation context
            conversation_context = response.get('context', {})
            
            # Display bot response
            if 'message' in response:
                bot_response = response['message']
                print_whatsapp_message("WhatsApp Bot", bot_response, Colors.CYAN)
                
                # Store bot message for next guidance
                conversation_context['last_bot_message'] = bot_response
                
                # Show helpful tips for specific bot responses
                if 'found' in bot_response.lower() and 'guide' in bot_response.lower() and 'video:' in bot_response:
                    print(f"\n{Colors.YELLOW}💡 TIP: You can:")
                    print(f"   • Check the ⭐ review scores and experience years")
                    print(f"   • Open the 🎥 video links in your browser to see guide introductions")
                    print(f"   • Compare prices 💰 before choosing{Colors.RESET}")
                elif 'past' in bot_response.lower() and 'date' in bot_response.lower():
                    print(f"\n{Colors.YELLOW}💡 NOTE: The system validates dates and only accepts future dates for bookings{Colors.RESET}")
            
            # Show minimal system info
            if response.get('agents_involved'):
                agents = ', '.join(response.get('agents_involved', []))
                print(f"{Colors.BLUE}   🤖 AI Agents: {agents}{Colors.RESET}")
            
            # Check if conversation is complete (booking confirmed)
            if ('booking_confirmed' in response or 'booking_id' in response or 
                'Booking Confirmed' in bot_response or 'TGB-' in bot_response):
                print(f"\n{Colors.GREEN}🎉 BOOKING COMPLETED! Demo conversation finished successfully!")
                print(f"✅ The tourist has successfully booked a guide through the AI system.{Colors.RESET}")
                break
                
        except Exception as e:
            print(f"{Colors.RED}❌ Error processing message: {e}")
            print(f"Continuing demo...{Colors.RESET}")
            continue
    
    if message_count >= max_messages:
        print(f"\n{Colors.YELLOW}⏰ Demo reached maximum messages ({max_messages}). Ending conversation.{Colors.RESET}")

async def run_sample_conversation(orchestrator):
    """Run a sample conversation without user input for quick testing"""
    
    print(f"{Colors.HEADER}")
    print("=" * 70)
    print("🏛️  GLOBAL GUIDE BOT - SAMPLE CONVERSATION (REAL API)")
    print("=" * 70)
    print(f"{Colors.RESET}")
    
    user_id = "demo_tourist_sample"
    conversation_context = {}
    
    # Sample conversation flow
    messages = [
        "Hi! I'm visiting Bangkok next week with my girlfriend. We love temples and want some romantic sunset experiences. Budget around $100/day.",
        "December 15th",
        "Somchai sounds perfect! Can I book him?",
        "My name is Sarah Johnson"
    ]
    
    for i, message in enumerate(messages, 1):
        print_whatsapp_message(f"Tourist Message #{i}", message, Colors.GREEN)
        
        try:
            print_system_status(f"🚀 Processing message #{i} with LIVE API calls...")
            
            response = await orchestrator.process_user_message(
                user_message=message,
                user_id=user_id,
                conversation_context=conversation_context
            )
            
            conversation_context = response.get('context', {})
            
            if 'message' in response:
                print_whatsapp_message("WhatsApp Bot Response", response['message'], Colors.CYAN)
            
            print_system_status(f"✅ Message #{i} processed successfully")
            
        except Exception as e:
            print(f"{Colors.RED}❌ Error processing message #{i}: {e}{Colors.RESET}")
            break

async def main():
    """Main demo function"""
    
    # Setup AgentCore
    orchestrator, agents = await setup_agentcore()
    
    if not orchestrator:
        print(f"{Colors.RED}❌ Failed to setup AgentCore system")
        print(f"Make sure you're running from the project root directory and AWS credentials are configured.{Colors.RESET}")
        return
    
    # Go directly to interactive mode
    await simulate_conversation_flow(orchestrator)
    
    # Demo Summary
    print(f"\n{Colors.HEADER}")
    print("=" * 70)
    print("✅ REAL API DEMO COMPLETED")
    print("=" * 70)
    print(f"{Colors.RESET}")
    
    print(f"{Colors.YELLOW}🎯 What This Demo Showed:")
    print(f"   • LIVE Amazon Nova Pro API calls")
    print(f"   • Real AgentCore multi-agent processing")
    print(f"   • Interactive user conversation flow")
    print(f"   • Actual AWS DynamoDB interactions")
    print(f"   • Live cultural intelligence analysis")
    print(f"   • Real guide matching from database")
    print(f"\n🚀 System Performance:")
    print(f"   • Model: eu.amazon.nova-pro-v1:0")
    print(f"   • Region: eu-west-1")
    print(f"   • Agents: 4 active (Tourist, Cultural, Guide, Booking)")
    print(f"   • Database: Live DynamoDB queries")
    print(f"   • Mode: Real-time API processing{Colors.RESET}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}👋 Demo interrupted by user. Goodbye!{Colors.RESET}")
    except Exception as e:
        print(f"\n{Colors.RED}❌ Demo failed: {e}{Colors.RESET}")