#!/usr/bin/env python3
"""
WhatsApp Image Handler Module
Handles image downloads from WhatsApp and uploads to S3
"""

import boto3
import requests
import uuid
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Initialize AWS clients
s3_client = boto3.client('s3')
S3_BUCKET = os.environ.get('NOVA_IMAGES_BUCKET', 'global-guide-bot-dev-nova-images')

# WhatsApp API configuration
WHATSAPP_TOKEN = os.environ.get('WHATSAPP_ACCESS_TOKEN')
WHATSAPP_API_VERSION = os.environ.get('WHATSAPP_API_VERSION', 'v20.0')


def download_whatsapp_media(media_id: str) -> bytes:
    """
    Download media from WhatsApp API
    
    Args:
        media_id: WhatsApp media ID
        
    Returns:
        bytes: Image data
    """
    try:
        # Step 1: Get media URL
        url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{media_id}"
        headers = {'Authorization': f'Bearer {WHATSAPP_TOKEN}'}
        
        logger.info(f"📥 Fetching media URL for {media_id}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        media_url = response.json()['url']
        logger.info(f"✅ Got media URL: {media_url[:50]}...")
        
        # Step 2: Download media
        logger.info(f"📥 Downloading media from URL")
        media_response = requests.get(media_url, headers=headers, timeout=30)
        media_response.raise_for_status()
        
        image_data = media_response.content
        logger.info(f"✅ Downloaded {len(image_data)} bytes")
        
        return image_data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error downloading WhatsApp media: {str(e)}")
        raise Exception(f"Failed to download image from WhatsApp: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        raise


def upload_to_s3(image_data: bytes, user_id: str, file_extension: str = 'jpg') -> str:
    """
    Upload image to S3
    
    Args:
        image_data: Image bytes
        user_id: User identifier
        file_extension: File extension (default: jpg)
        
    Returns:
        str: S3 key
    """
    try:
        # Generate unique S3 key
        s3_key = f"uploads/{user_id}/{uuid.uuid4()}.{file_extension}"
        
        logger.info(f"📤 Uploading to S3: {s3_key}")
        
        # Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=image_data,
            ContentType=f'image/{file_extension}',
            Metadata={
                'user_id': user_id,
                'source': 'whatsapp'
            }
        )
        
        logger.info(f"✅ Uploaded to S3: s3://{S3_BUCKET}/{s3_key}")
        
        return s3_key
        
    except Exception as e:
        logger.error(f"❌ Error uploading to S3: {str(e)}")
        raise Exception(f"Failed to upload image to S3: {str(e)}")


def handle_image_message(message: Dict[str, Any], from_number: str) -> Dict[str, Any]:
    """
    Handle incoming WhatsApp image message
    
    Args:
        message: WhatsApp message object
        from_number: Sender's phone number
        
    Returns:
        dict: Processing result with image_data and s3_key
    """
    try:
        # Extract media ID and caption
        media_id = message['image']['id']
        caption = message['image'].get('caption', '')
        mime_type = message['image'].get('mime_type', 'image/jpeg')
        
        logger.info(f"📸 Image received from {from_number}")
        logger.info(f"   Media ID: {media_id}")
        logger.info(f"   Caption: {caption}")
        logger.info(f"   MIME type: {mime_type}")
        
        # Download image from WhatsApp
        image_data = download_whatsapp_media(media_id)
        
        # Determine file extension
        file_extension = 'jpg'
        if 'png' in mime_type.lower():
            file_extension = 'png'
        elif 'webp' in mime_type.lower():
            file_extension = 'webp'
        
        # Upload to S3
        s3_key = upload_to_s3(image_data, from_number, file_extension)
        
        return {
            'success': True,
            'image_data': image_data,
            's3_key': s3_key,
            's3_bucket': S3_BUCKET,
            'caption': caption,
            'mime_type': mime_type,
            'size_bytes': len(image_data)
        }
        
    except Exception as e:
        logger.error(f"❌ Error handling image message: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'success': False,
            'error': str(e)
        }


def format_image_analysis_response(analysis: Dict[str, Any]) -> str:
    """
    Format Nova Act analysis into user-friendly WhatsApp message
    
    Args:
        analysis: Analysis result from Cultural Agent
        
    Returns:
        str: Formatted response text
    """
    response = []
    
    # Location
    if analysis.get('location'):
        response.append(f"📍 *{analysis['location']}*")
        response.append("")
    
    # Main guidance
    if analysis.get('guidance'):
        response.append(analysis['guidance'])
        response.append("")
    
    # Appropriateness check
    if analysis.get('appropriateness_check') == 'needs_attention':
        response.append("⚠️ *Important Notes:*")
        for concern in analysis.get('concerns', []):
            response.append(f"  • {concern}")
        response.append("")
    
    # Recommendations
    if analysis.get('recommendations'):
        response.append("💡 *Recommendations:*")
        for rec in analysis['recommendations'][:3]:  # Top 3
            response.append(f"  • {rec}")
        response.append("")
    
    # Guide suggestions
    if analysis.get('suggested_guide_types'):
        response.append("🎯 *Suggested Guides:*")
        for guide_type in analysis['suggested_guide_types']:
            response.append(f"  • {guide_type.title()}")
        response.append("")
    
    # Next action
    if analysis.get('next_action'):
        response.append(analysis['next_action'])
    else:
        response.append("Would you like me to find a guide for this experience?")
    
    return "\n".join(response)
