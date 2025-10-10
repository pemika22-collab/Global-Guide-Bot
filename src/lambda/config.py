"""
Configuration module for Lambda functions
Reads WhatsApp credentials from AWS Systems Manager Parameter Store
"""

import os
import boto3
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

# Initialize SSM client
ssm = boto3.client('ssm')

# Get project configuration from environment
PROJECT_NAME = os.getenv('PROJECT_NAME', 'thailand-guide-bot')
ENVIRONMENT = os.getenv('ENVIRONMENT', 'demo')
# AWS_REGION is automatically available in Lambda environment

def get_parameter(param_name, decrypt=True):
    """
    Get parameter from Parameter Store (no caching to avoid stale values)
    
    Args:
        param_name: Parameter name (e.g., 'phone_number_id')
        decrypt: Whether to decrypt SecureString parameters
    
    Returns:
        Parameter value or None if not found
    """
    full_param_name = f"/{PROJECT_NAME}/{ENVIRONMENT}/whatsapp/{param_name}"
    
    try:
        logger.info(f"🔍 Fetching parameter: {full_param_name}")
        response = ssm.get_parameter(
            Name=full_param_name,
            WithDecryption=decrypt
        )
        value = response['Parameter']['Value']
        logger.info(f"✅ Got parameter {param_name}: {value[:20]}...")
        
        # Check if it's still a placeholder
        if value.startswith('PLACEHOLDER'):
            logger.warning(f"⚠️  Parameter {full_param_name} is still a placeholder. Run setup_whatsapp.py")
            return None
        
        return value
    except ssm.exceptions.ParameterNotFound:
        logger.error(f"❌ Parameter not found: {full_param_name}")
        return None
    except Exception as e:
        logger.error(f"❌ Error getting parameter {full_param_name}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def get_whatsapp_config():
    """
    Get all WhatsApp configuration from Parameter Store
    
    Returns:
        dict with WhatsApp credentials
    """
    return {
        'phone_number_id': get_parameter('phone_number_id'),
        'access_token': get_parameter('access_token'),
        'verify_token': get_parameter('verify_token'),
        'business_account_id': get_parameter('business_account_id')
    }

# Cache credentials for Lambda container reuse
_cached_config = None

def get_cached_whatsapp_config():
    """
    Get WhatsApp config with Lambda container-level caching
    This reduces Parameter Store API calls
    """
    global _cached_config
    
    if _cached_config is None:
        _cached_config = get_whatsapp_config()
        logger.info("✅ Loaded WhatsApp credentials from Parameter Store")
    
    return _cached_config

# Convenience functions for backward compatibility
def get_whatsapp_phone_number_id():
    """Get WhatsApp Phone Number ID"""
    config = get_cached_whatsapp_config()
    return config.get('phone_number_id')

def get_whatsapp_access_token():
    """Get WhatsApp Access Token"""
    config = get_cached_whatsapp_config()
    return config.get('access_token')

def get_whatsapp_verify_token():
    """Get WhatsApp Verify Token"""
    config = get_cached_whatsapp_config()
    return config.get('verify_token')

def get_whatsapp_business_account_id():
    """Get WhatsApp Business Account ID"""
    config = get_cached_whatsapp_config()
    return config.get('business_account_id')
