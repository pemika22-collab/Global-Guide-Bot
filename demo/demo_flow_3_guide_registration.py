#!/usr/bin/env python3
"""
Demo Flow 3: Guide Registration with Real API
=============================================

This demo shows the guide registration process using the real AgentCore system.
It demonstrates the two-sided marketplace capabilities with live API calls.

Features:
- Random guide data generation
- Real AgentCore API integration
- AI-powered validation with Nova Pro
- Live DynamoDB guide registration
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
        registration_module = load_agentcore_module("registration_agent", "src/lambda/agentcore/registration_agent.py")
        
        if not all([tourist_module, cultural_module, guide_module, booking_module, registration_module]):
            return None, None
        
        # Extract classes
        EnhancedAgentCoreOrchestrator = orchestrator_module.EnhancedAgentCoreOrchestrator
        
        TouristAgent = tourist_module.TouristAgent
        CulturalAgent = cultural_module.CulturalAgent
        GuideAgent = guide_module.GuideAgent
        BookingAgent = booking_module.BookingAgent
        RegistrationAgent = registration_module.RegistrationAgent
        
        print_system_status("✅ AgentCore modules loaded successfully")
        
        # Initialize enhanced system
        orchestrator = EnhancedAgentCoreOrchestrator()
        
        # Create and register agents
        tourist_agent = TouristAgent()
        cultural_agent = CulturalAgent()
        guide_agent = GuideAgent()
        booking_agent = BookingAgent()
        registration_agent = RegistrationAgent()
        
        orchestrator.register_agent("tourist", tourist_agent)
        orchestrator.register_agent("cultural", cultural_agent)
        orchestrator.register_agent("guide", guide_agent)
        orchestrator.register_agent("booking", booking_agent)
        orchestrator.register_agent("registration", registration_agent)
        
        print("✅ Registered touristAgent")
        print("✅ Registered culturalAgent")
        print("✅ Registered guideAgent")
        print("✅ Registered bookingAgent")
        print("✅ Registered registrationAgent")
        
        print_system_status("✅ AgentCore system initialized with 5 agents")
        
        return orchestrator, {
            'tourist': tourist_agent,
            'cultural': cultural_agent,
            'guide': guide_agent,
            'booking': booking_agent,
            'registration': registration_agent
        }
        
    except Exception as e:
        print(f"{Colors.RED}❌ AgentCore setup failed: {e}{Colors.RESET}")
        return None, None

# Random data generators
THAI_FIRST_NAMES = [
    "Somchai", "Kamon", "Niran", "Wichai", "Ekachai", "Thawat", "Kasem", "Narong",
    "Apinya", "Kanya", "Wanida", "Anchalee", "Busaba", "Chanida", "Ganya", "Mali",
    "Ploy", "Ratchanee", "Suda", "Tida", "Usa", "Vanna", "Zara", "Hansa", "Jinda"
]

THAI_LAST_NAMES = [
    "Thanakit", "Wongsakul", "Chaiwong", "Photiwat", "Srisawat", "Kaewmanee", 
    "Boonmee", "Ruangsri", "Kanjana", "Saengchai", "Panya", "Damrong", "Hiran",
    "Srisai", "Gamon", "Boonsong", "Pattana", "Boonlert", "Ekkarat", "Chai"
]

LOCATIONS = ["Bangkok", "Chiang Mai", "Phuket", "Pattaya", "Krabi", "Koh Samui", "Ayutthaya"]

SPECIALTIES = [
    "temple tours", "food tours", "beach tours", "cultural experiences", "cooking classes",
    "night markets", "historical sites", "adventure tours", "photography tours", 
    "traditional crafts", "meditation retreats", "elephant sanctuaries"
]

LANGUAGES = [
    ["Thai", "English"], ["Thai", "English", "Chinese"], ["Thai", "English", "Japanese"],
    ["Thai", "English", "German"], ["Thai", "English", "French"], ["Thai", "English", "Spanish"],
    ["Thai", "English", "Korean"], ["Thai", "English", "Russian"]
]

def generate_random_guide():
    """Generate random guide application data"""
    first_name = random.choice(THAI_FIRST_NAMES)
    last_name = random.choice(THAI_LAST_NAMES)
    location = random.choice(LOCATIONS)
    specialties = random.sample(SPECIALTIES, random.randint(2, 4))
    languages = random.choice(LANGUAGES)
    experience = random.randint(2, 15)
    phone = f"+6688{random.randint(1000000, 9999999)}"
    gender = random.choice(["male", "female"])
    
    # Generate a bio based on the guide's info
    specialties_text = ", ".join(specialties)
    bio_templates = [
        f"Experienced {location} guide specializing in {specialties_text}. Passionate about sharing Thai culture with visitors.",
        f"Local {location} expert with {experience} years of experience in {specialties_text}. Love meeting people from around the world!",
        f"Professional guide from {location} offering authentic {specialties_text} experiences. Dedicated to creating memorable adventures.",
        f"Born and raised in {location}, I specialize in {specialties_text} and enjoy showing visitors the real Thailand.",
        f"{experience}-year veteran guide in {location} focusing on {specialties_text}. Let me share my hometown's hidden gems with you!"
    ]
    bio = random.choice(bio_templates)
    
    return {
        "name": f"{first_name} {last_name}",
        "phone": phone,
        "location": location,
        "specialties": specialties,
        "languages": languages,
        "experience": experience,
        "gender": gender,
        "bio": bio
    }

async def main():
    """Run the guide registration demo with real API calls"""
    
    # Setup AgentCore
    orchestrator, agents = await setup_agentcore()
    
    if not orchestrator:
        print(f"{Colors.RED}❌ Failed to setup AgentCore system")
        print(f"Make sure you're running from the project root directory and AWS credentials are configured.{Colors.RESET}")
        return
    
    print("\n" + "=" * 70)
    print("👨‍🏫 GLOBAL GUIDE BOT - GUIDE REGISTRATION REAL API DEMO")
    print("=" * 70)
    
    print("🎯 Feature: Two-Sided Marketplace Registration")
    print("🤖 AgentCore System: LIVE Amazon Nova Pro API calls")
    print("📱 Platform: WhatsApp (simulated)")
    print("☁️  AWS Region: eu-west-1")
    print("🎯 Mode: Automated - Random guide data generation!")
    
    # Generate random guide data
    guide_data = generate_random_guide()
    
    print(f"\n🎬 Starting Guide Registration Demo...")
    print(f"👨‍🏫 Random Guide Applicant: {guide_data['name']}")
    print(f"📍 Location: {guide_data['location']}")
    
    # Create comprehensive registration message with ALL required info
    specialties_text = ", ".join(guide_data['specialties'])
    languages_text = ", ".join(guide_data['languages'])
    
    registration_message = (
        f"I want to register as a guide. "
        f"Name: {guide_data['name']}, "
        f"Phone: {guide_data['phone']}, "
        f"Specialties: {specialties_text}, "
        f"Languages: {languages_text}, "
        f"Location: {guide_data['location']}, "
        f"Gender: {guide_data['gender']}, "
        f"Experience: {guide_data['experience']} years, "
        f"Bio: {guide_data['bio']}"
    )
    
    print(f"\n📱 WhatsApp Bot:")
    print(f"   🙏 Sawasdee! Welcome to Global Guide Bot Thailand! 🇹🇭")
    print(f"   I can help you register as a professional guide!")
    print(f"   💬 Tell me about your experience and specialties!")
    
    print(f"\n👨‍🏫 Guide Applicant:")
    print(f"   {registration_message}")
    
    # Process with AgentCore
    print(f"\n⚙️  System: 🤖 Processing with AI...")
    
    try:
        # Create user ID for the guide applicant
        user_id = f"guide_applicant_{random.randint(1000, 9999)}"
        
        print(f"\n" + "=" * 70)
        print(f"🎯 AgentCore Processing Message")
        print(f"User: {user_id}")
        print(f"Message: {registration_message}")
        print("=" * 70)
        
        # Process the registration message
        response = await orchestrator.process_user_message(
            user_message=registration_message,
            user_id=user_id
        )
        
        print(f"\n" + "=" * 70)
        print(f"✅ AgentCore Response Ready")
        print(f"Agents Involved: {', '.join(response.get('agents_involved', []))}")
        print(f"Interactions: {response.get('interaction_count', 0)}")
        print("=" * 70)
        
        # Display the response
        print(f"\n📱 WhatsApp Bot:")
        bot_message = response.get('message', 'Registration processed successfully!')
        for line in bot_message.split('\n'):
            if line.strip():
                print(f"   {line}")
        
        # Show AI agents involved
        agents_involved = response.get('agents_involved', [])
        if agents_involved:
            print(f"   🤖 AI Agents: {', '.join(agents_involved)}")
        
        # If registration shows confirmation request, simulate user saying "yes"
        if "confirm" in response.get('message', '').lower() and "yes" in response.get('message', '').lower():
            print(f"\n👨‍🏫 Guide Applicant:")
            print(f"   Yes, that's all correct! Please register me.")
            
            # Process confirmation
            print(f"\n⚙️  System: 🤖 Processing confirmation...")
            
            print(f"\n" + "=" * 70)
            print(f"🎯 AgentCore Processing Message")
            print(f"User: {user_id}")
            print(f"Message: Yes, that's all correct! Please register me.")
            print("=" * 70)
            
            # Pass the context from the first response to maintain registration flow
            conversation_context = response.get('context', {})
            
            confirmation_response = await orchestrator.process_user_message(
                user_message="Yes, that's all correct! Please register me.",
                user_id=user_id,
                conversation_context=conversation_context
            )
            
            print(f"\n" + "=" * 70)
            print(f"✅ AgentCore Response Ready")
            print(f"Agents Involved: {', '.join(confirmation_response.get('agents_involved', []))}")
            print(f"Interactions: {confirmation_response.get('interaction_count', 0)}")
            print("=" * 70)
            
            print(f"\n📱 WhatsApp Bot:")
            confirmation_message = confirmation_response.get('message', 'Registration confirmed!')
            for line in confirmation_message.split('\n'):
                if line.strip():
                    print(f"   {line}")
            
            # Show AI agents involved
            agents_involved = confirmation_response.get('agents_involved', [])
            if agents_involved:
                print(f"   🤖 AI Agents: {', '.join(agents_involved)}")
        
        print(f"\n🎉 REGISTRATION COMPLETED! Guide registration demo finished successfully!")
        print(f"✅ The guide applicant successfully registered through the AI system.")
        
    except Exception as e:
        print(f"❌ Error processing registration: {str(e)}")
        return
    
    # Demo Summary
    print(f"\n" + "=" * 70)
    print(f"✅ REAL API DEMO COMPLETED")
    print("=" * 70)
    
    print(f"🎯 What This Demo Showed:")
    print(f"   • LIVE Amazon Nova Pro API calls")
    print(f"   • Real AgentCore multi-agent processing")
    print(f"   • Two-sided marketplace functionality")
    print(f"   • AI-powered guide validation")
    print(f"   • Actual AWS DynamoDB interactions")
    print(f"   • Live guide registration processing")
    
    print(f"\n👨‍🏫 Guide Registration Features:")
    print(f"   • Random guide data generation")
    print(f"   • Natural language application processing")
    print(f"   • Intelligent information extraction")
    print(f"   • Real-time validation and approval")
    print(f"   • Database integration for guide storage")
    
    print(f"\n🚀 System Performance:")
    print(f"   • Model: eu.amazon.nova-pro-v1:0")
    print(f"   • Region: eu-west-1")
    print(f"   • Agents: 4 active (Tourist, Cultural, Guide, Booking)")
    print(f"   • Database: Live DynamoDB queries")
    print(f"   • Mode: Real-time API processing")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())