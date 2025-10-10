import json
import urllib3
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Lambda function to handle WhatsApp token renewal notifications
    """
    try:
        # Parse SNS message
        message = json.loads(event['Records'][0]['Sns']['Message'])
        
        logger.info(f"Received WhatsApp token renewal notification: {message}")
        
        # Extract alarm details
        alarm_name = message.get('AlarmName', 'Unknown')
        new_state = message.get('NewStateValue', 'Unknown')
        reason = message.get('NewStateReason', 'No reason provided')
        
        # Webhook configuration
        webhook_url = "${webhook_url}"
        verify_token = "${verify_token}"
        
        # Prepare notification payload
        notification_payload = {
            "type": "token_renewal_alert",
            "alarm_name": alarm_name,
            "state": new_state,
            "reason": reason,
            "verify_token": verify_token,
            "timestamp": message.get('StateChangeTime', 'Unknown')
        }
        
        # Send notification to webhook
        http = urllib3.PoolManager()
        response = http.request(
            'POST',
            webhook_url,
            body=json.dumps(notification_payload),
            headers={'Content-Type': 'application/json'}
        )
        
        logger.info(f"Notification sent to webhook. Status: {response.status}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'WhatsApp token renewal notification processed successfully',
                'alarm_name': alarm_name,
                'webhook_status': response.status
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp token renewal notification: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Failed to process notification',
                'details': str(e)
            })
        }