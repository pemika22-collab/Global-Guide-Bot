#!/usr/bin/env python3
import json
import boto3
import logging
import urllib.request
import os
import asyncio
import time
import hashlib
from agentcore.enhanced_orchestrator import EnhancedAgentCoreOrchestrator
from agentcore.tourist_agent import TouristAgent
from agentcore.guide_agent import GuideAgent
from agentcore.cultural_agent import CulturalAgent
from agentcore.booking_agent import BookingAgent
from agentcore.registration_agent import RegistrationAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

orchestrator = None
dynamodb = boto3.resource('dynamodb')
messages_table = None

def get_messages_table():
    """Get DynamoDB messages table for deduplication"""
    global messages_table
    if messages_table is None:
        table_name = os.getenv('MESSAGES_TABLE', 'thailand-guide-bot-dev-messages')
        messages_table = dynamodb.Table(table_name)
    return messages_table

def is_duplicate_message(from_number, text_body, message_type="text"):
    """Check if message is a duplicate using DynamoDB"""
    try:
        # Generate message hash excluding timestamp for proper deduplication
        message_hash = hashlib.md5(f"{from_number}:{text_body}:{message_type}".encode()).hexdigest()
        
        table = get_messages_table()
        current_time = int(time.time())
        
        # Check if message exists in last 30 seconds
        response = table.get_item(
            Key={
                'message_hash': message_hash
            }
        )
        
        if 'Item' in response:
            last_timestamp = response['Item'].get('timestamp', 0)
            if current_time - last_timestamp < 30:  # 30 second deduplication window
                logger.info(f"🔄 Duplicate message detected: {text_body[:50]}...")
                return True
        
        # Store/update message hash with current timestamp
        table.put_item(
            Item={
                'message_hash': message_hash,
                'timestamp': current_time,
                'from_number': from_number,
                'message_preview': text_body[:100],
                'ttl': current_time + 300  # 5 minute TTL
            }
        )
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Deduplication error: {str(e)}")
        # If deduplication fails, allow message through to avoid blocking
        return False

def get_orchestrator():
    global orchestrator
    if orchestrator is None:
        orchestrator = EnhancedAgentCoreOrchestrator()
        orchestrator.register_agent("tourist", TouristAgent())
        orchestrator.register_agent("guide", GuideAgent())
        orchestrator.register_agent("cultural", CulturalAgent())
        orchestrator.register_agent("booking", BookingAgent())
        orchestrator.register_agent("registration", RegistrationAgent())
        logger.info("✅ AgentCore orchestrator initialized")
    return orchestrator

def send_whatsapp_message(to_number, message):
    """Send WhatsApp message"""
    try:
        logger.info(f"🚀 SEND_WHATSAPP_MESSAGE CALLED - to: {to_number}, message: {message[:100]}...")
        
        access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
        phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        
        if not access_token or not phone_number_id:
            logger.error("❌ Missing WhatsApp credentials")
            return False
        
        url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {"body": message}
        }
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        logger.info(f"📤 Making HTTP request to: {url}")
        logger.info(f"📤 Payload: {json.dumps(payload)}")
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers)
        
        with urllib.request.urlopen(req) as response:
            result = response.read().decode('utf-8')
            logger.info(f"✅ WhatsApp API response: {result}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error sending WhatsApp message: {str(e)}")
        return False

def lambda_handler(event, context):
    try:
        logger.info(f"📥 Received event: {json.dumps(event)}")
        
        http_method = event.get('httpMethod', 'POST')
        
        if http_method == 'GET':
            return handle_verification(event)
        elif http_method == 'POST':
            return handle_webhook(event)
        else:
            return {'statusCode': 405, 'body': json.dumps({'error': 'Method not allowed'})}
            
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'statusCode': 500, 'body': json.dumps({'error': 'Internal server error'})}

def handle_verification(event):
    """Handle WhatsApp webhook verification"""
    query_params = event.get('queryStringParameters') or {}
    
    mode = query_params.get('hub.mode')
    token = query_params.get('hub.verify_token')
    challenge = query_params.get('hub.challenge')
    
    verify_token = os.getenv('WHATSAPP_VERIFY_TOKEN', 'global_guide_bot_verify_2024')
    
    if mode == 'subscribe' and token == verify_token:
        logger.info("✅ Webhook verification successful")
        return {'statusCode': 200, 'body': challenge}
    else:
        logger.error("❌ Webhook verification failed")
        return {'statusCode': 403, 'body': json.dumps({'error': 'Verification failed'})}

def handle_webhook(event):
    """Handle WhatsApp messages"""
    try:
        body = json.loads(event.get('body', '{}'))
        logger.info(f"📨 WhatsApp webhook received: {json.dumps(body)}")
        
        entry = body.get('entry', [])
        if not entry:
            logger.info("📭 No entry in webhook body")
            return {'statusCode': 200, 'body': json.dumps({'status': 'no_entry'})}
        
        for entry_item in entry:
            changes = entry_item.get('changes', [])
            logger.info(f"🔄 Processing {len(changes)} changes")
            for change in changes:
                if change.get('field') == 'messages':
                    logger.info(f"💬 Processing message change: {json.dumps(change.get('value', {}))}")
                    process_message(change.get('value', {}))
                else:
                    logger.info(f"⏭️ Skipping non-message change: {change.get('field')}")
        
        return {'statusCode': 200, 'body': json.dumps({'status': 'success'})}
        
    except Exception as e:
        logger.error(f"❌ Error processing webhook: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}

def process_message(message_data):
    """Process WhatsApp message with AgentCore"""
    try:
        messages = message_data.get('messages', [])
        
        for message in messages:
            from_number = message.get('from')
            message_type = message.get('type')
            
            if message_type == 'text':
                text_body = message.get('text', {}).get('body', '').strip()
                
                if not text_body:
                    continue
                
                # DynamoDB-based deduplication
                if is_duplicate_message(from_number, text_body, message_type):
                    continue
                
                logger.info(f"💬 Text from {from_number}: {text_body}")
                
                # Process with AgentCore
                orch = get_orchestrator()
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    orch.process_user_message(text_body, from_number, {'message_type': message_type}, message_type)
                )
                loop.close()
                
                response_text = result.get('message', 'Hello! How can I help you?')
                
                # Send response via WhatsApp API
                send_whatsapp_message(from_number, response_text)
                
                logger.info(f"✅ Sent response: {response_text[:100]}...")
                
            elif message_type == 'image':
                # Handle image messages
                logger.info(f"📸 Image message from {from_number}")
                
                image_data = message.get('image', {})
                image_id = image_data.get('id')
                caption = image_data.get('caption', '').strip()
                
                if not image_id:
                    logger.error("❌ No image ID found")
                    send_whatsapp_message(from_number, "Sorry, I couldn't process that image. Please try again.")
                    continue
                
                logger.info(f"📸 Image ID: {image_id}, Caption: {caption}")
                
                # Download image from WhatsApp
                image_url = download_whatsapp_image(image_id)
                
                if not image_url:
                    logger.error("❌ Failed to download image")
                    send_whatsapp_message(from_number, "Sorry, I couldn't download that image. Please try again.")
                    continue
                
                logger.info(f"✅ Image downloaded: {image_url}")
                
                # Process with AgentCore
                orch = get_orchestrator()
                
                # Create message with image context
                user_message = caption if caption else "What is this place?"
                
                # Run async code in sync context
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    orch.process_user_message(user_message, from_number, {'image_url': image_url, 'has_image': True, 'message_type': message_type}, message_type)
                )
                loop.close()
                
                # Skip sending response if it's a duplicate
                if result.get('skip_response'):
                    logger.info(f"🔄 Skipping duplicate image response")
                    continue
                
                response_text = result.get('message', 'I analyzed your image!')
                
                # Send response via WhatsApp API
                send_whatsapp_message(from_number, response_text)
                
                logger.info(f"✅ Sent image analysis response: {response_text[:100]}...")
                
                
    except Exception as e:
        logger.error(f"❌ Error processing message: {str(e)}")
        import traceback
        traceback.print_exc()

def download_whatsapp_image(image_id):
    """Download image from WhatsApp and upload to S3"""
    try:
        access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
        bucket_name = os.getenv('NOVA_IMAGES_BUCKET', 'thailand-guide-bot-dev-nova-images')
        
        if not access_token:
            logger.error("❌ Missing WhatsApp access token")
            return None
        
        # Step 1: Get image URL from WhatsApp
        url = f"https://graph.facebook.com/v17.0/{image_id}"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            media_data = json.loads(response.read().decode('utf-8'))
            media_url = media_data.get('url')
            mime_type = media_data.get('mime_type', 'image/jpeg')
        
        if not media_url:
            logger.error("❌ No media URL in response")
            return None
        
        logger.info(f"📥 Downloading image from: {media_url}")
        
        # Step 2: Download image content
        req = urllib.request.Request(media_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            image_content = response.read()
        
        logger.info(f"✅ Downloaded {len(image_content)} bytes")
        
        # Step 3: Upload to S3
        s3 = boto3.client('s3')
        
        # Generate unique filename
        timestamp = int(time.time())
        extension = mime_type.split('/')[-1] if '/' in mime_type else 'jpg'
        s3_key = f"whatsapp-images/{timestamp}_{image_id}.{extension}"
        
        s3.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=image_content,
            ContentType=mime_type
        )
        
        # Generate S3 URL
        s3_url = f"s3://{bucket_name}/{s3_key}"
        logger.info(f"✅ Uploaded to S3: {s3_url}")
        
        return s3_url
        
    except Exception as e:
        logger.error(f"❌ Error downloading image: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
