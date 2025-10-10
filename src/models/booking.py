"""Booking model for Thailand Guide Bot"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid


@dataclass
class BookingDetails:
    """Booking details data model"""
    date: str
    duration: int
    location: str
    activities: List[str] = field(default_factory=list)
    group_size: int = 1
    special_requests: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage"""
        return {
            'date': self.date,
            'duration': self.duration,
            'location': self.location,
            'activities': self.activities,
            'groupSize': self.group_size,
            'specialRequests': self.special_requests
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BookingDetails':
        """Create from dictionary"""
        return cls(
            date=data['date'],
            duration=data['duration'],
            location=data['location'],
            activities=data.get('activities', []),
            group_size=data.get('groupSize', 1),
            special_requests=data.get('specialRequests')
        )


@dataclass
class Pricing:
    """Pricing data model"""
    base_price: float
    commission: float
    total_price: float
    currency: str = 'THB'

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage"""
        return {
            'basePrice': self.base_price,
            'commission': self.commission,
            'totalPrice': self.total_price,
            'currency': self.currency
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Pricing':
        """Create from dictionary"""
        return cls(
            base_price=data['basePrice'],
            commission=data['commission'],
            total_price=data['totalPrice'],
            currency=data.get('currency', 'THB')
        )


@dataclass
class Communication:
    """Communication data model"""
    tourist_platform: str
    guide_platform: str
    conversation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage"""
        return {
            'touristPlatform': self.tourist_platform,
            'guidePlatform': self.guide_platform,
            'conversationId': self.conversation_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Communication':
        """Create from dictionary"""
        return cls(
            tourist_platform=data['touristPlatform'],
            guide_platform=data['guidePlatform'],
            conversation_id=data.get('conversationId')
        )


@dataclass
class Timestamps:
    """Timestamps data model"""
    created: str
    confirmed: Optional[str] = None
    completed: Optional[str] = None
    cancelled: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage"""
        return {
            'created': self.created,
            'confirmed': self.confirmed,
            'completed': self.completed,
            'cancelled': self.cancelled
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Timestamps':
        """Create from dictionary"""
        return cls(
            created=data['created'],
            confirmed=data.get('confirmed'),
            completed=data.get('completed'),
            cancelled=data.get('cancelled')
        )


@dataclass
class Review:
    """Review data model"""
    rating: int
    comment: Optional[str] = None
    submitted_at: Optional[str] = None

    def __post_init__(self):
        """Set timestamp if not provided"""
        if not self.submitted_at:
            self.submitted_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage"""
        return {
            'rating': self.rating,
            'comment': self.comment,
            'submittedAt': self.submitted_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Review':
        """Create from dictionary"""
        return cls(
            rating=data['rating'],
            comment=data.get('comment'),
            submitted_at=data.get('submittedAt')
        )


@dataclass
class Booking:
    """Booking data model"""
    booking_id: str
    tourist_id: str
    guide_id: str
    status: str = 'pending'
    booking_details: Optional[BookingDetails] = None
    pricing: Optional[Pricing] = None
    communication: Optional[Communication] = None
    timestamps: Optional[Timestamps] = None
    review: Optional[Review] = None

    def __post_init__(self):
        """Initialize default values"""
        if not self.booking_id:
            self.booking_id = str(uuid.uuid4())
        if not self.timestamps:
            self.timestamps = Timestamps(created=datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage"""
        return {
            'bookingId': self.booking_id,
            'touristId': self.tourist_id,
            'guideId': self.guide_id,
            'status': self.status,
            'bookingDetails': self.booking_details.to_dict() if self.booking_details else {},
            'pricing': self.pricing.to_dict() if self.pricing else {},
            'communication': self.communication.to_dict() if self.communication else {},
            'timestamps': self.timestamps.to_dict() if self.timestamps else {},
            'review': self.review.to_dict() if self.review else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Booking':
        """Create Booking from dictionary"""
        booking = cls(
            booking_id=data['bookingId'],
            tourist_id=data['touristId'],
            guide_id=data['guideId'],
            status=data.get('status', 'pending')
        )
        
        if data.get('bookingDetails'):
            booking.booking_details = BookingDetails.from_dict(data['bookingDetails'])
        
        if data.get('pricing'):
            booking.pricing = Pricing.from_dict(data['pricing'])
        
        if data.get('communication'):
            booking.communication = Communication.from_dict(data['communication'])
        
        if data.get('timestamps'):
            booking.timestamps = Timestamps.from_dict(data['timestamps'])
        
        if data.get('review'):
            booking.review = Review.from_dict(data['review'])
        
        return booking

    def confirm(self) -> None:
        """Confirm the booking"""
        self.status = 'confirmed'
        if self.timestamps:
            self.timestamps.confirmed = datetime.utcnow().isoformat()

    def complete(self) -> None:
        """Complete the booking"""
        self.status = 'completed'
        if self.timestamps:
            self.timestamps.completed = datetime.utcnow().isoformat()

    def cancel(self) -> None:
        """Cancel the booking"""
        self.status = 'cancelled'
        if self.timestamps:
            self.timestamps.cancelled = datetime.utcnow().isoformat()

    def add_review(self, rating: int, comment: Optional[str] = None) -> None:
        """Add a review to the booking"""
        self.review = Review(rating=rating, comment=comment)