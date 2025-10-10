"""Message model for Thailand Guide Bot"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from datetime import datetime
import uuid


@dataclass
class MessageContent:
    """Message content data model"""
    text: Optional[str] = None
    media_url: Optional[str] = None
    location: Optional[Dict[str, float]] = None
    quick_reply: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage"""
        return {
            'text': self.text,
            'mediaUrl': self.media_url,
            'location': self.location,
            'quickReply': self.quick_reply
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageContent':
        """Create from dictionary"""
        return cls(
            text=data.get('text'),
            media_url=data.get('mediaUrl'),
            location=data.get('location'),
            quick_reply=data.get('quickReply')
        )


@dataclass
class MessageMetadata:
    """Message metadata data model"""
    language: Optional[str] = None
    translated: bool = False
    ai_processed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage"""
        return {
            'language': self.language,
            'translated': self.translated,
            'aiProcessed': self.ai_processed
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageMetadata':
        """Create from dictionary"""
        return cls(
            language=data.get('language'),
            translated=data.get('translated', False),
            ai_processed=data.get('aiProcessed', False)
        )


@dataclass
class Message:
    """Message data model"""
    message_id: str
    conversation_id: str
    sender_id: str
    recipient_id: str
    platform: str
    message_type: str
    content: MessageContent
    metadata: MessageMetadata = field(default_factory=MessageMetadata)
    timestamp: Optional[str] = None
    status: str = 'sent'

    def __post_init__(self):
        """Initialize default values"""
        if not self.message_id:
            self.message_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage"""
        return {
            'messageId': self.message_id,
            'conversationId': self.conversation_id,
            'senderId': self.sender_id,
            'recipientId': self.recipient_id,
            'platform': self.platform,
            'messageType': self.message_type,
            'content': self.content.to_dict(),
            'metadata': self.metadata.to_dict(),
            'timestamp': self.timestamp,
            'status': self.status
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create Message from dictionary"""
        return cls(
            message_id=data['messageId'],
            conversation_id=data['conversationId'],
            sender_id=data['senderId'],
            recipient_id=data['recipientId'],
            platform=data['platform'],
            message_type=data['messageType'],
            content=MessageContent.from_dict(data['content']),
            metadata=MessageMetadata.from_dict(data.get('metadata', {})),
            timestamp=data.get('timestamp'),
            status=data.get('status', 'sent')
        )

    def mark_delivered(self) -> None:
        """Mark message as delivered"""
        self.status = 'delivered'

    def mark_read(self) -> None:
        """Mark message as read"""
        self.status = 'read'

    def mark_failed(self) -> None:
        """Mark message as failed"""
        self.status = 'failed'

    def set_language(self, language: str) -> None:
        """Set message language"""
        self.metadata.language = language

    def mark_translated(self) -> None:
        """Mark message as translated"""
        self.metadata.translated = True

    def mark_ai_processed(self) -> None:
        """Mark message as AI processed"""
        self.metadata.ai_processed = True