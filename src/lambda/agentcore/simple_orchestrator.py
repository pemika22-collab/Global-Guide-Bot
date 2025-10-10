"""
Simple AgentCore Orchestrator without persistent memory
Clean state for each interaction
"""

import json
from typing import Dict, Any


class SimpleAgentCoreOrchestrator:
    """
    Simple orchestrator without persistent memory/strands
    Each interaction is independent
    """
    
    def __init__(self):
        self.agents = {}
        
    def register_agent(self, name: str, agent: Any):
        """Register an agent with the orchestrator"""
        self.agents[name] = agent
        print(f"✅ Registered {name}Agent")
        
    async def process_user_message(
        self, 
        user_message: str, 
        user_id: str,
        conversation_context: Dict[str, Any] = None,
        message_type: str = "text"
    ) -> Dict[str, Any]:
        """
        Process user message with simple routing
        """
        
        print(f"🎯 Simple AgentCore Processing")
        print(f"User: {user_id}")
        print(f"Message: {user_message}")
        print(f"{'='*50}")
        
        # Get tourist agent
        tourist_agent = self.agents.get('tourist')
        if not tourist_agent:
            raise ValueError("TouristAgent not registered")
        
        # Create simple context
        context = conversation_context or {}
        context['user_id'] = user_id
        
        # Process message
        response = await tourist_agent.process(
            message=user_message,
            context=context,
            orchestrator=self
        )
        
        print(f"✅ Simple AgentCore Response Ready")
        print(f"{'='*50}")
        
        return response
    
    async def agent_to_agent(
        self, 
        from_agent: str, 
        to_agent: str, 
        message: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Handle agent-to-agent communication"""
        
        target_agent = self.agents.get(to_agent)
        if not target_agent:
            return {"error": f"Agent {to_agent} not found"}
        
        print(f"🔄 {from_agent}Agent → {to_agent}Agent")
        
        # Process the message
        if hasattr(target_agent, 'process'):
            response = await target_agent.process(message, context or {}, self)
        else:
            response = {"message": "Agent processing not available"}
        
        return response
    
    async def delegate_to(self, agent_name: str, message: str, orchestrator=None):
        """Delegate to another agent (compatibility method)"""
        return await self.agent_to_agent("tourist", agent_name, message)
