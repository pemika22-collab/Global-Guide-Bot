"""User model for Thailand Guide Bot"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import json


@dataclass
class TouristPreferences:
    """Tourist preferences data model"""
    interests: List[str] = field(default_factory=list)
    budget_range: Dict[str, Any] = field(default_factory=dict)
    group_size: int = 1
    travel_dates: Dict[str, str] = field(default_factory=dict)
    preferred_languages: List[str] = field(default_factory=list)
    accessibility: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage"""
        return {
            'interests': self.interests,
            'budgetRange': self.budget_range,
            'groupSize': self.group_size,
            'travelDates': self.travel_dates,
            'preferredLanguages': self.preferred_languages,
            'accessibility': self.accessibility
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TouristPreferences':
        """Create from dictionary"""
        return cls(
            interests=data.get('interests', []),
            budget_range=data.get('budgetRange', {}),
            group_size=data.get('groupSize', 1),
            travel_dates=data.get('travelDates', {}),
            preferred_languages=data.get('preferredLanguages', []),
            accessibility=data.get('accessibility', [])
        )


@dataclass
class GuideProfile:
    """Guide profile data model"""
    specialties: List[str] = field(default_factory=list)
    languages: List[Dict[str, str]] = field(default_factory=list)
    experience: int = 0
    certifications: List[str] = field(default_factory=list)
    availability: Dict[str, Any] = field(default_factory=dict)
    pricing: Dict[str, Any] = field(default_factory=dict)
    location: Dict[str, Any] = field(default_factory=dict)
    rating: float = 0.0
    review_count: int = 0
    status: str = 'pending'

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage"""
        return {
            'specialties': self.specialties,
            'languages': self.languages,
            'experience': self.experience,
            'certifications': self.certifications,
            'availability': self.availability,
            'pricing': self.pricing,
            'location': self.location,
            'rating': self.rating,
            'reviewCount': self.review_count,
            'status': self.status
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GuideProfile':
        """Create from dictionary"""
        return cls(
            specialties=data.get('specialties', []),
            languages=data.get('languages', []),
            experience=data.get('experience', 0),
            certifications=data.get('certifications', []),
            availability=data.get('availability', {}),
            pricing=data.get('pricing', {}),
            location=data.get('location', {}),
            rating=data.get('rating', 0.0),
            review_count=data.get('reviewCount', 0),
            status=data.get('status', 'pending')
        )


@dataclass
class User:
    """User data model"""
    user_id: str
    platform: str
    phone_number: str
    preferred_language: str = 'en'
    user_type: str = 'tourist'
    profile: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    is_active: bool = True

    def __post_init__(self):
        """Set timestamps if not provided"""
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage"""
        return {
            'userId': self.user_id,
            'platform': self.platform,
            'phoneNumber': self.phone_number,
            'preferredLanguage': self.preferred_language,
            'userType': self.user_type,
            'profile': self.profile or {},
            'createdAt': self.created_at,
            'updatedAt': self.updated_at,
            'isActive': self.is_active
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create User from dictionary"""
        return cls(
            user_id=data['userId'],
            platform=data['platform'],
            phone_number=data['phoneNumber'],
            preferred_language=data.get('preferredLanguage', 'en'),
            user_type=data.get('userType', 'tourist'),
            profile=data.get('profile'),
            created_at=data.get('createdAt'),
            updated_at=data.get('updatedAt'),
            is_active=data.get('isActive', True)
        )

    def get_tourist_preferences(self) -> Optional[TouristPreferences]:
        """Get tourist preferences if user is a tourist"""
        if self.user_type == 'tourist' and self.profile:
            return TouristPreferences.from_dict(self.profile)
        return None

    def get_guide_profile(self) -> Optional[GuideProfile]:
        """Get guide profile if user is a guide"""
        if self.user_type == 'guide' and self.profile:
            return GuideProfile.from_dict(self.profile)
        return None

    def update_profile(self, profile_data: Dict[str, Any]) -> None:
        """Update user profile"""
        self.profile = profile_data
        self.updated_at = datetime.utcnow().isoformat()

    def set_language(self, language: str) -> None:
        """Set preferred language"""
        self.preferred_language = language
        self.updated_at = datetime.utcnow().isoformat()