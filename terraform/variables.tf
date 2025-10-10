# Variables for Thailand Guide Bot Infrastructure

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "eu-west-1" # Ireland
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "thailand-guide-bot"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "python_runtime" {
  description = "Python runtime version for Lambda functions"
  type        = string
  default     = "python3.11"
}

# DynamoDB Configuration
variable "dynamodb_billing_mode" {
  description = "DynamoDB billing mode"
  type        = string
  default     = "PAY_PER_REQUEST"
}

# S3 Configuration
variable "s3_force_destroy" {
  description = "Force destroy S3 buckets (useful for dev/staging)"
  type        = bool
  default     = false
}

# Lambda Configuration
variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 30
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 256
}

# Bedrock Configuration
variable "bedrock_model_id" {
  description = "AWS Bedrock model ID for AI processing"
  type        = string
  default     = "eu.amazon.nova-pro-v1:0"
}

# WhatsApp Configuration
variable "whatsapp_verify_token" {
  description = "WhatsApp webhook verification token"
  type        = string
  sensitive   = true
  default     = ""
}

variable "whatsapp_access_token" {
  description = "WhatsApp Business API access token"
  type        = string
  sensitive   = true
  default     = ""
}

variable "whatsapp_phone_number_id" {
  description = "WhatsApp Business API phone number ID"
  type        = string
  sensitive   = true
  default     = ""
}