"""
AgentCore Memory System
Replaces flat context with intelligent memory layers
"""

import json
import boto3
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal


def convert_decimals(obj):
    """Convert Decimal objects for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(v) for v in obj]
    return obj


class AgentMemory:
    """
    Intelligent memory system for AgentCore
    Replaces flat context with layered memory:
    - Short-term: Current conversation
    - Working: Active booking/registration process  
    - Long-term: User preferences and history
    """
    
    def __init__(self, dynamodb_table_name: str = 'thailand-guide-bot-dev-memory'):
        self.dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        self.memory_table = self.dynamodb.Table(dynamodb_table_name)
        
    async def get_memory(self, user_id: str) -> Dict[str, Any]:
        """Get complete memory for user"""
        try:
            response = self.memory_table.get_item(Key={'userId': user_id})
            if 'Item' in response:
                memory = response['Item']
                return convert_decimals(memory)
            else:
                return self._create_empty_memory(user_id)
        except Exception as e:
            print(f"❌ Memory get error: {e}")
            return self._create_empty_memory(user_id)
    
    async def update_memory(self, user_id: str, memory_data: Dict[str, Any]):
        """Update user memory"""
        try:
            # Convert floats to Decimals for DynamoDB
            def convert_floats(obj):
                if isinstance(obj, float):
                    return Decimal(str(obj))
                elif isinstance(obj, dict):
                    return {k: convert_floats(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_floats(v) for v in obj]
                return obj
            
            memory_data = convert_floats(memory_data)
            memory_data['userId'] = user_id
            memory_data['lastUpdated'] = int(datetime.now().timestamp())
            
            self.memory_table.put_item(Item=memory_data)
            print(f"💾 Memory updated for {user_id}")
            
        except Exception as e:
            print(f"❌ Memory update error: {e}")
    
    async def remember_preference(self, user_id: str, key: str, value: Any):
        """Remember user preference"""
        memory = await self.get_memory(user_id)
        if 'long_term' not in memory:
            memory['long_term'] = {}
        if 'preferences' not in memory['long_term']:
            memory['long_term']['preferences'] = {}
            
        memory['long_term']['preferences'][key] = value
        await self.update_memory(user_id, memory)
    
    async def recall_preference(self, user_id: str, key: str) -> Any:
        """Recall user preference"""
        memory = await self.get_memory(user_id)
        return memory.get('long_term', {}).get('preferences', {}).get(key)
    
    async def add_to_history(self, user_id: str, event: Dict[str, Any]):
        """Add event to user history"""
        memory = await self.get_memory(user_id)
        if 'long_term' not in memory:
            memory['long_term'] = {}
        if 'history' not in memory['long_term']:
            memory['long_term']['history'] = []
            
        event['timestamp'] = datetime.now().isoformat()
        memory['long_term']['history'].append(event)
        
        # Keep only last 50 events
        memory['long_term']['history'] = memory['long_term']['history'][-50:]
        
        await self.update_memory(user_id, memory)
    
    async def get_working_memory(self, user_id: str) -> Dict[str, Any]:
        """Get current working memory (active processes)"""
        memory = await self.get_memory(user_id)
        return memory.get('working', {})
    
    async def update_working_memory(self, user_id: str, process: str, data: Dict[str, Any]):
        """Update working memory for specific process"""
        memory = await self.get_memory(user_id)
        if 'working' not in memory:
            memory['working'] = {}
            
        memory['working'][process] = data
        await self.update_memory(user_id, memory)
    
    async def clear_memory(self, user_id: str):
        """Clear all memory for a user"""
        await self.update_memory(user_id, {
            'events': [],
            'working': {},
            'last_updated': time.time()
        })
    
    async def clear_memory(self, user_id: str):
        """Clear all memory for a user"""
        import time
        await self.update_memory(user_id, {
            'events': [],
            'working': {},
            'last_updated': time.time()
        })
    
    async def clear_working_memory(self, user_id: str, process: str = None):
        """Clear working memory (process completed)"""
        memory = await self.get_memory(user_id)
        if 'working' in memory:
            if process:
                memory['working'].pop(process, None)
            else:
                memory['working'] = {}
        await self.update_memory(user_id, memory)
    
    def _create_empty_memory(self, user_id: str) -> Dict[str, Any]:
        """Create empty memory structure"""
        return {
            'userId': user_id,
            'short_term': {
                'current_conversation': [],
                'last_intent': None,
                'active_agent': None
            },
            'working': {
                # Active processes: booking, registration, etc.
            },
            'long_term': {
                'preferences': {},
                'history': [],
                'successful_bookings': [],
                'favorite_guides': [],
                'travel_style': None
            },
            'created': datetime.now().isoformat(),
            'lastUpdated': int(datetime.now().timestamp())
        }