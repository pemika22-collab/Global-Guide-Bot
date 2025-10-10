#!/usr/bin/env python3
"""
Demo Flow 5: Strands System Showcase
===================================

This demo shows how the strands system intelligently manages different conversation types:
- General conversations
- Booking flows  
- Cultural questions
- Registration processes

Each strand maintains its own context and memory.
"""

import asyncio
import sys
import os
import importlib.util

class Colors:
    HEADER = '\033[95m\033[1m'
    BLUE = '\033[94m\033[1m'
    CYAN = '\033[96m\033[1m'
    GREEN = '\033[92m\033[1m'
    YELLOW = '\033[93m\033[1m'
    RED = '\033[91m\033[1m'
    RESET = '\033[0m'

def load_agentcore_module(module_name, file_path):
    """Load AgentCore module using importlib"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Replace relative imports
        content = content.replace('from .base_agent import BaseAgent', 'from base_agent import BaseAgent')
        content = content.replace('from .memory import AgentMemory', 'from memory import AgentMemory')
        content = content.replace('from .strands import StrandManager, StrandType', 'from strands import StrandManager, StrandType')
        
        spec = importlib.util.spec_from_loader(module_name, loader=None)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        exec(content, module.__dict__)
        return module
    except Exception as e:
        print(f"❌ Failed to load {module_name}: {e}")
        return None

async def showcase_strands():
    """Showcase how strands manage different conversation types"""
    
    print(f"{Colors.HEADER}")
    print("=" * 70)
    print("🧵 STRANDS SYSTEM SHOWCASE")
    print("=" * 70)
    print(f"{Colors.RESET}")
    
    # Load modules
    print("Loading AgentCore modules...")
    base_agent = load_agentcore_module("base_agent", "src/lambda/agentcore/base_agent.py")
    memory = load_agentcore_module("memory", "src/lambda/agentcore/memory.py")
    strands = load_agentcore_module("strands", "src/lambda/agentcore/strands.py")
    orchestrator = load_agentcore_module("enhanced_orchestrator", "src/lambda/agentcore/enhanced_orchestrator.py")
    tourist = load_agentcore_module("tourist_agent", "src/lambda/agentcore/tourist_agent.py")
    cultural = load_agentcore_module("cultural_agent", "src/lambda/agentcore/cultural_agent.py")
    guide = load_agentcore_module("guide_agent", "src/lambda/agentcore/guide_agent.py")
    
    if not all([base_agent, memory, strands, orchestrator, tourist, cultural, guide]):
        print(f"{Colors.RED}Failed to load required modules{Colors.RESET}")
        return
    
    # Initialize system
    orchestrator_instance = orchestrator.EnhancedAgentCoreOrchestrator()
    orchestrator_instance.register_agent("tourist", tourist.TouristAgent())
    orchestrator_instance.register_agent("cultural", cultural.CulturalAgent())
    orchestrator_instance.register_agent("guide", guide.GuideAgent())
    
    user_id = "strand_demo_user"
    
    print(f"{Colors.YELLOW}🎯 Testing how strands intelligently categorize conversations:{Colors.RESET}\n")
    
    # Test different conversation types
    test_messages = [
        ("Hi there!", "general"),
        ("I need a guide in Bangkok", "booking"),
        ("Find me guides for Phuket", "booking"),
        ("How do I greet Thai people?", "cultural"),
        ("What should I wear to temples?", "cultural")
    ]
    
    for i, (message, expected_type) in enumerate(test_messages, 1):
        print(f"{Colors.CYAN}📝 Message {i}: {Colors.RESET}'{message}'")
        
        try:
            response = await orchestrator_instance.process_user_message(
                user_message=message,
                user_id=user_id
            )
            
            strand_info = response.get('strand_info', {})
            strand_type = strand_info.get('strand_type', 'unknown')
            strand_id = strand_info.get('strand_id', 'unknown')
            
            # Color code by strand type
            if strand_type == 'booking':
                color = Colors.GREEN
            elif strand_type == 'cultural':
                color = Colors.BLUE
            elif strand_type == 'registration':
                color = Colors.YELLOW
            else:
                color = Colors.CYAN
            
            print(f"{color}🧵 Strand: {strand_type} ({strand_id[:8]}...){Colors.RESET}")
            print(f"   Expected: {expected_type} | Actual: {strand_type}")
            
            if strand_type == expected_type:
                print(f"   ✅ Correct strand classification!")
            else:
                print(f"   ⚠️  Different classification (still valid)")
            
        except Exception as e:
            print(f"{Colors.RED}   ❌ Error: {e}{Colors.RESET}")
        
        print()
    
    print(f"\n{Colors.GREEN}✅ Strands showcase completed!{Colors.RESET}")
    print(f"{Colors.YELLOW}Key Benefits:{Colors.RESET}")
    print("• 🧵 Intelligent conversation categorization")
    print("• 🧠 Context-aware memory management") 
    print("• 🔄 Seamless conversation switching")
    print("• 📊 Multi-threaded conversation tracking")

if __name__ == "__main__":
    try:
        asyncio.run(showcase_strands())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Demo interrupted. Goodbye!{Colors.RESET}")
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.RESET}")
