"""
AgentCore Strand System
Handles multiple conversation threads per user
"""

import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum


class StrandType(Enum):
    BOOKING = "booking"
    CULTURAL = "cultural" 
    REGISTRATION = "registration"
    GENERAL = "general"


class ConversationStrand:
    """
    Individual conversation thread
    Each strand tracks one specific goal/process
    """
    
    def __init__(self, strand_id: str, strand_type: StrandType, user_id: str):
        self.strand_id = strand_id
        self.strand_type = strand_type
        self.user_id = user_id
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.status = "active"  # active, completed, abandoned
        self.context = {}
        self.agents_involved = []
        self.messages = []
        
    def add_message(self, role: str, content: str, agent: str = None):
        """Add message to strand"""
        self.messages.append({
            "role": role,
            "content": content,
            "agent": agent,
            "timestamp": datetime.now().isoformat()
        })
        self.last_activity = datetime.now()
        
        if agent and agent not in self.agents_involved:
            self.agents_involved.append(agent)
    
    def update_context(self, key: str, value: Any):
        """Update strand context"""
        self.context[key] = value
        self.last_activity = datetime.now()
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if strand has expired"""
        return (datetime.now() - self.last_activity).total_seconds() > (timeout_minutes * 60)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "strand_id": self.strand_id,
            "strand_type": self.strand_type.value,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "status": self.status,
            "context": self.context,
            "agents_involved": self.agents_involved,
            "messages": self.messages
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationStrand':
        """Create from dictionary"""
        strand = cls(
            strand_id=data["strand_id"],
            strand_type=StrandType(data["strand_type"]),
            user_id=data["user_id"]
        )
        strand.created_at = datetime.fromisoformat(data["created_at"])
        strand.last_activity = datetime.fromisoformat(data["last_activity"])
        strand.status = data["status"]
        strand.context = data["context"]
        strand.agents_involved = data["agents_involved"]
        strand.messages = data["messages"]
        return strand


class StrandManager:
    """
    Manages multiple conversation strands per user
    Decides which strand to use for each message
    """
    
    def __init__(self, memory_system):
        self.memory = memory_system
    
    async def get_active_strands(self, user_id: str) -> List[ConversationStrand]:
        """Get all active strands for user"""
        memory = await self.memory.get_memory(user_id)
        strands_data = memory.get('strands', {})
        
        strands = []
        for strand_data in strands_data.values():
            strand = ConversationStrand.from_dict(strand_data)
            if not strand.is_expired() and strand.status == "active":
                strands.append(strand)
        
        return strands
    
    async def create_strand(self, user_id: str, strand_type: StrandType, initial_context: Dict[str, Any] = None) -> ConversationStrand:
        """Create new conversation strand"""
        strand_id = f"{strand_type.value}_{uuid.uuid4().hex[:8]}"
        strand = ConversationStrand(strand_id, strand_type, user_id)
        
        if initial_context:
            strand.context.update(initial_context)
        
        await self._save_strand(strand)
        print(f"🧵 Created {strand_type.value} strand: {strand_id}")
        return strand
    
    async def get_or_create_strand(self, user_id: str, message: str, intent: Dict[str, Any]) -> ConversationStrand:
        """Get existing strand or create new one based on intent"""
        
        # Determine strand type from intent
        strand_type = self._determine_strand_type(intent)
        
        # Get active strands
        active_strands = await self.get_active_strands(user_id)
        
        # Look for existing strand of same type
        for strand in active_strands:
            if strand.strand_type == strand_type:
                print(f"🧵 Using existing {strand_type.value} strand: {strand.strand_id}")
                return strand
        
        # Create new strand
        return await self.create_strand(user_id, strand_type, {"initial_intent": intent})
    
    async def update_strand(self, strand: ConversationStrand):
        """Update strand in memory"""
        await self._save_strand(strand)
    
    async def complete_strand(self, strand: ConversationStrand, outcome: str):
        """Mark strand as completed"""
        strand.status = "completed"
        strand.context["completion_outcome"] = outcome
        strand.context["completed_at"] = datetime.now().isoformat()
        
        await self._save_strand(strand)
        print(f"✅ Completed strand {strand.strand_id}: {outcome}")
    
    async def merge_strands(self, primary_strand: ConversationStrand, secondary_strand: ConversationStrand) -> ConversationStrand:
        """Merge two strands (e.g., cultural inquiry leads to booking)"""
        
        # Merge context
        primary_strand.context.update(secondary_strand.context)
        
        # Merge messages
        primary_strand.messages.extend(secondary_strand.messages)
        
        # Merge agents
        for agent in secondary_strand.agents_involved:
            if agent not in primary_strand.agents_involved:
                primary_strand.agents_involved.append(agent)
        
        # Mark secondary as completed
        await self.complete_strand(secondary_strand, f"merged_into_{primary_strand.strand_id}")
        
        # Update primary
        await self.update_strand(primary_strand)
        
        print(f"🔗 Merged {secondary_strand.strand_id} → {primary_strand.strand_id}")
        return primary_strand
    
    def _determine_strand_type(self, intent: Dict[str, Any]) -> StrandType:
        """Determine strand type from intent"""
        intent_type = intent.get("type", "general")
        
        if intent_type in ["booking", "guide_search", "guide_selection"]:
            return StrandType.BOOKING
        elif intent_type in ["cultural", "temple_etiquette", "customs"]:
            return StrandType.CULTURAL
        elif intent_type in ["registration", "guide_registration"]:
            return StrandType.REGISTRATION
        else:
            return StrandType.GENERAL
    
    async def _save_strand(self, strand: ConversationStrand):
        """Save strand to memory"""
        memory = await self.memory.get_memory(strand.user_id)
        
        if 'strands' not in memory:
            memory['strands'] = {}
        
        memory['strands'][strand.strand_id] = strand.to_dict()
        await self.memory.update_memory(strand.user_id, memory)
    
    async def cleanup_expired_strands(self, user_id: str):
        """Remove expired strands"""
        memory = await self.memory.get_memory(user_id)
        strands_data = memory.get('strands', {})
        
        active_strands = {}
        for strand_id, strand_data in strands_data.items():
            strand = ConversationStrand.from_dict(strand_data)
            if not strand.is_expired():
                active_strands[strand_id] = strand_data
        
        memory['strands'] = active_strands
        await self.memory.update_memory(user_id, memory)