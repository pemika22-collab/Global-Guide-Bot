"""Database service for Thailand Guide Bot"""

import boto3
from boto3.dynamodb.conditions import Key, Attr
from typing import Dict, List, Optional, Any
import os
import logging
from botocore.exceptions import ClientError

from ..models.user import User
from ..models.booking import Booking
from ..models.message import Message

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for DynamoDB operations"""
    
    def __init__(self):
        """Initialize DynamoDB client and table references"""
        self.dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'ap-southeast-1'))
        
        # Table names from environment variables
        self.users_table = self.dynamodb.Table(os.getenv('USERS_TABLE'))
        self.guides_table = self.dynamodb.Table(os.getenv('GUIDES_TABLE'))
        self.bookings_table = self.dynamodb.Table(os.getenv('BOOKINGS_TABLE'))
        self.messages_table = self.dynamodb.Table(os.getenv('MESSAGES_TABLE'))
    
    # User operations
    async def create_user(self, user: User) -> bool:
        """Create a new user"""
        try:
            self.users_table.put_item(
                Item=user.to_dict(),
                ConditionExpression='attribute_not_exists(userId)'
            )
            logger.info(f"Created user: {user.user_id}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.warning(f"User already exists: {user.user_id}")
                return False
            logger.error(f"Error creating user: {e}")
            raise
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            response = self.users_table.get_item(Key={'userId': user_id})
            if 'Item' in response:
                return User.from_dict(response['Item'])
            return None
        except ClientError as e:
            logger.error(f"Error getting user {user_id}: {e}")
            raise
    
    async def update_user(self, user: User) -> bool:
        """Update existing user"""
        try:
            self.users_table.put_item(Item=user.to_dict())
            logger.info(f"Updated user: {user.user_id}")
            return True
        except ClientError as e:
            logger.error(f"Error updating user {user.user_id}: {e}")
            raise
    
    async def get_users_by_platform(self, platform: str, limit: int = 50) -> List[User]:
        """Get users by platform"""
        try:
            response = self.users_table.query(
                IndexName='platform-created-index',
                KeyConditionExpression=Key('platform').eq(platform),
                Limit=limit
            )
            return [User.from_dict(item) for item in response['Items']]
        except ClientError as e:
            logger.error(f"Error getting users by platform {platform}: {e}")
            raise
    
    # Guide operations
    async def create_guide(self, guide_data: Dict[str, Any]) -> bool:
        """Create a new guide"""
        try:
            self.guides_table.put_item(
                Item=guide_data,
                ConditionExpression='attribute_not_exists(guideId)'
            )
            logger.info(f"Created guide: {guide_data['guideId']}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.warning(f"Guide already exists: {guide_data['guideId']}")
                return False
            logger.error(f"Error creating guide: {e}")
            raise
    
    async def get_guide(self, guide_id: str) -> Optional[Dict[str, Any]]:
        """Get guide by ID"""
        try:
            response = self.guides_table.get_item(Key={'guideId': guide_id})
            if 'Item' in response:
                return response['Item']
            return None
        except ClientError as e:
            logger.error(f"Error getting guide {guide_id}: {e}")
            raise
    
    async def get_guides_by_location(self, location: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get guides by location, ordered by rating"""
        try:
            response = self.guides_table.query(
                IndexName='location-rating-index',
                KeyConditionExpression=Key('location').eq(location),
                ScanIndexForward=False,  # Descending order (highest rating first)
                Limit=limit
            )
            return response['Items']
        except ClientError as e:
            logger.error(f"Error getting guides by location {location}: {e}")
            raise
    
    async def get_guides_by_status(self, status: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get guides by status"""
        try:
            response = self.guides_table.query(
                IndexName='status-index',
                KeyConditionExpression=Key('status').eq(status),
                Limit=limit
            )
            return response['Items']
        except ClientError as e:
            logger.error(f"Error getting guides by status {status}: {e}")
            raise
    
    async def update_guide(self, guide_data: Dict[str, Any]) -> bool:
        """Update existing guide"""
        try:
            self.guides_table.put_item(Item=guide_data)
            logger.info(f"Updated guide: {guide_data['guideId']}")
            return True
        except ClientError as e:
            logger.error(f"Error updating guide {guide_data['guideId']}: {e}")
            raise
    
    # Booking operations
    async def create_booking(self, booking: Booking) -> bool:
        """Create a new booking"""
        try:
            self.bookings_table.put_item(
                Item=booking.to_dict(),
                ConditionExpression='attribute_not_exists(bookingId)'
            )
            logger.info(f"Created booking: {booki