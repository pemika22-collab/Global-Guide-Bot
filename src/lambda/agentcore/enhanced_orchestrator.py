"""
Enhanced AgentCore Orchestrator with Memory and Strands
Replaces flat context with intelligent memory and multi-threading
"""

import json
import time
import hashlib
import boto3
from typing import Dict, Any, List
from datetime import datetime

try:
    from .memory import AgentMemory
    from .strands import StrandManager, StrandType
except ImportError:
    # Fallback for demo environments
    import sys
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    sys.path.append(current_dir)
    from memory import AgentMemory
    from strands import StrandManager, StrandType


class EnhancedAgentCoreOrchestrator:
    """
    Enhanced orchestrator with Memory and Strands
    Replaces your current flat context system
    """
    
    def __init__(self):
        self.agents = {}
        self.memory = AgentMemory()
        self.strand_manager = StrandManager(self.memory)
        # Use DynamoDB for persistent deduplication
        self.dynamodb = boto3.resource('dynamodb')
        self.messages_table = self.dynamodb.Table('thailand-guide-bot-dev-messages')
        
    def _generate_message_hash(self, user_id: str, message: str, message_type: str = "text") -> str:
        """Generate hash for message deduplication"""
        # Include current minute to allow same message in different contexts
        current_minute = int(time.time() // 60)
        message_string = f"{user_id}:{message}:{message_type}:{current_minute}"
        return hashlib.md5(message_string.encode()).hexdigest()
    
    def _is_duplicate_message(self, message_hash: str, message: str = "") -> bool:
        """Check if message is duplicate using DynamoDB"""
        # Allow common booking confirmation words to bypass deduplication
        confirmation_words = ['yes', 'no', 'confirm', 'ok', 'sure', 'cancel', 'proceed']
        if message.lower().strip() in confirmation_words:
            return False
            
        try:
            current_time = int(time.time())
            
            # Try to put item with condition that it doesn't exist
            self.messages_table.put_item(
                Item={
                    'messageId': message_hash,  # Use messageId as the key
                    'timestamp': str(current_time),  # Convert to string for GSI
                    'ttl': current_time + 60  # 1 minute TTL for booking responses
                },
                ConditionExpression='attribute_not_exists(messageId)'
            )
            return False  # Not duplicate, item was created
        except self.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            print(f"🔄 Duplicate message detected, skipping processing")
            return True  # Duplicate, item already exists
        
        # For compatibility with existing demo
        self.message_bus = None
        self.context = {}
        
    def register_agent(self, name: str, agent: Any):
        """Register an agent with the orchestrator"""
        self.agents[name] = agent
        print(f"✅ Registered {name}Agent")
        
    async def process_user_message(
        self, 
        user_message: str, 
        user_id: str,
        conversation_context: Dict[str, Any] = None,  # Legacy - will be ignored
        message_type: str = "text"  # New parameter for message type
    ) -> Dict[str, Any]:
        """
        Process user message with Memory and Strands
        REPLACES your current context-based system
        """
        # Check for reset commands first
        if user_message.strip().lower() in ['reset', 'clear', 'start over', 'restart', 'new search']:
            print(f"🔄 Resetting memory and strands for user {user_id}")
            await self.memory.clear_memory(user_id)
            self.strand_manager.clear_strands(user_id)
            return {
                "message": "Context reset! How can I help you today? Looking for a guide?",
                "reset": True,
                "skip_response": False  # Ensure this gets sent
            }
        
        # Check for duplicate message
        message_hash = self._generate_message_hash(user_id, user_message, message_type)
        if self._is_duplicate_message(message_hash, user_message):
            return {"message": "", "duplicate": True, "skip_response": True}
            
        print(f"\n{'='*80}")
        print(f"🎯 Enhanced AgentCore Processing")
        print(f"User: {user_id}")
        print(f"Message: {user_message}")
        print(f"{'='*80}\n")
        
        # Get user memory (replaces flat context)
        memory = await self.memory.get_memory(user_id)
        
        # Detect intent first
        intent = self._detect_intent(user_message, memory)
        
        # Get or create appropriate strand
        strand = await self.strand_manager.get_or_create_strand(user_id, user_message, intent)
        
        # Add message to strand
        strand.add_message("user", user_message)
        
        # Process through appropriate agent
        tourist_agent = self.agents.get('tourist')
        if not tourist_agent:
            raise ValueError("TouristAgent not registered")
        
        # Create enhanced context from memory + strand (JSON serializable)
        enhanced_context = {
            **memory.get('long_term', {}).get('preferences', {}),
            **strand.context,
            'user_id': user_id,
            'strand_id': strand.strand_id,
            'strand_type': strand.strand_type.value,
            'memory_summary': memory.get('short_term', {}),
            'conversation_history': strand.messages[-5:] if strand.messages else []  # Last 5 messages
        }
        
        # Merge legacy conversation context for backward compatibility
        if conversation_context:
            enhanced_context.update(conversation_context)
        
        # Check if this is an image message - route to CulturalAgent
        if enhanced_context.get('has_image') or enhanced_context.get('image_url'):
            print(f"📸 Image detected - routing to CulturalAgent")
            cultural_agent = self.agents.get('cultural')
            if cultural_agent:
                # Create image analysis request
                image_request = {
                    "action": "analyze_image",
                    "image_url": enhanced_context.get('image_url'),
                    "user_question": user_message,
                    "context": enhanced_context
                }
                
                try:
                    response = await cultural_agent.process(
                        message=json.dumps(image_request),
                        context=enhanced_context,
                        orchestrator=self
                    )
                except TypeError:
                    # Fallback for sync agents
                    response = cultural_agent.process(
                        message=json.dumps(image_request),
                        context=enhanced_context,
                        orchestrator=self
                    )
                    if hasattr(response, '__await__'):
                        response = await response
                
                # Update strand with response
                strand.add_message("assistant", response.get('message', ''), "cultural")
                
                # Preserve response context for next message
                if response.get('context'):
                    strand.context.update(response['context'])
                
                # Update memory
                await self._update_memory_from_interaction(user_id, user_message, response, strand)
                
                # Save strand
                await self.strand_manager.update_strand(strand)
                
                print(f"✅ Enhanced AgentCore Response Ready")
                print(f"Strand: {strand.strand_type.value} ({strand.strand_id})")
                print(f"Memory Updated: {len(memory.get('long_term', {}).get('history', []))} events")
                print(f"{'='*80}\n")
                
                return response
        
        # Process message (handle both sync and async agents)
        try:
            response = await tourist_agent.process(
                message=user_message,
                context=enhanced_context,
                orchestrator=self
            )
        except TypeError:
            # Fallback for sync agents
            import asyncio
            response = tourist_agent.process(
                message=user_message,
                context=enhanced_context,
                orchestrator=self
            )
            if hasattr(response, '__await__'):
                response = await response
        
        # Update strand with response
        strand.add_message("assistant", response.get('message', ''), "tourist")
        
        # Preserve response context for next message
        if response.get('context'):
            strand.context.update(response['context'])
        
        # Update memory based on interaction
        await self._update_memory_from_interaction(user_id, user_message, response, strand)
        
        # Check if we need to auto-reset after completion
        # Only reset after COMPLETED bookings or registrations, not guide searches
        if (response.get('booking_result') and response.get('booking_result', {}).get('booking_id')) or response.get('registration_complete'):
            print(f"🔄 Auto-resetting memory after successful completion")
            await self.memory.clear_memory(user_id)
            self.strand_manager.clear_strands(user_id)
            # Add reset flag to result
            response['auto_reset'] = True
        
        # Save strand
        await self.strand_manager.update_strand(strand)
        
        # Enhanced response with memory insights
        response['memory_insights'] = await self._get_memory_insights(user_id)
        response['strand_info'] = {
            'strand_id': strand.strand_id,
            'strand_type': strand.strand_type.value,
            'agents_involved': strand.agents_involved
        }
        
        print(f"\n{'='*80}")
        print(f"✅ Enhanced AgentCore Response Ready")
        print(f"Strand: {strand.strand_type.value} ({strand.strand_id})")
        print(f"Memory Updated: {len(memory.get('long_term', {}).get('history', []))} events")
        print(f"{'='*80}\n")
        
        return response
    
    def _detect_intent(self, message: str, memory: Dict[str, Any]) -> Dict[str, Any]:
        """Detect user intent using memory context"""
        
        # Simple intent detection (you can enhance with Nova Pro)
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['guide', 'book', 'find', 'tour']):
            return {"type": "booking", "confidence": 0.8}
        elif any(word in message_lower for word in ['temple', 'culture', 'etiquette', 'dress', 'wai']):
            return {"type": "cultural", "confidence": 0.8}
        elif any(word in message_lower for word in ['register', 'become guide', 'join']):
            return {"type": "registration", "confidence": 0.8}
        else:
            return {"type": "general", "confidence": 0.5}
    
    async def _update_memory_from_interaction(
        self, 
        user_id: str, 
        message: str, 
        response: Dict[str, Any], 
        strand
    ):
        """Update memory based on interaction"""
        
        # Add to history
        await self.memory.add_to_history(user_id, {
            "type": "interaction",
            "user_message": message,
            "agent_response": response.get('message', ''),
            "intent": response.get('intent', {}),
            "strand_id": strand.strand_id
        })
        
        # Learn preferences
        intent = response.get('intent', {})
        if intent.get('type') == 'booking':
            # Extract location preference
            if 'location' in strand.context:
                await self.memory.remember_preference(
                    user_id, 
                    'preferred_location', 
                    strand.context['location']
                )
            
            # Extract budget preference  
            if 'budget' in strand.context:
                await self.memory.remember_preference(
                    user_id,
                    'typical_budget',
                    strand.context['budget']
                )
    
    async def _get_memory_insights(self, user_id: str) -> Dict[str, Any]:
        """Get insights from user memory"""
        memory = await self.memory.get_memory(user_id)
        
        return {
            "total_interactions": len(memory.get('long_term', {}).get('history', [])),
            "preferences": memory.get('long_term', {}).get('preferences', {}),
            "successful_bookings": len(memory.get('long_term', {}).get('successful_bookings', [])),
            "favorite_guides": memory.get('long_term', {}).get('favorite_guides', [])
        }
    
    # Keep existing agent_to_agent method for compatibility
    async def agent_to_agent(
        self, 
        from_agent: str, 
        to_agent: str, 
        message: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Handle agent-to-agent communication (enhanced with strand tracking)"""
        
        # Get target agent
        target = self.agents.get(to_agent)
        if not target:
            raise ValueError(f"Agent '{to_agent}' not registered")
        
        # Update strand with agent interaction
        if context and 'strand' in context:
            strand = context['strand']
            strand.add_message("agent", message, from_agent)
            await self.strand_manager.update_strand(strand)
        
        print(f"📨 {from_agent}Agent → {to_agent}Agent")
        
        # Process message
        response = await target.process(message, context, self)
        
        return response