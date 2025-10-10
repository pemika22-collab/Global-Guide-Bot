# Lambda Functions for Thailand Guide Bot

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "whatsapp_webhook" {
  name              = "/aws/lambda/${local.name_prefix}-whatsapp-webhook"
  retention_in_days = 14

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-whatsapp-webhook-logs"
    Type = "CloudWatch"
  })
}

resource "aws_cloudwatch_log_group" "message_processor" {
  name              = "/aws/lambda/${local.name_prefix}-message-processor"
  retention_in_days = 14

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-message-processor-logs"
    Type = "CloudWatch"
  })
}

# Lambda Deployment Packages
data "archive_file" "whatsapp_webhook" {
  type        = "zip"
  source_dir  = "${path.module}/../../src/lambda"
  output_path = "${path.module}/whatsapp_webhook.zip"
  excludes    = ["__pycache__", "*.pyc", ".pytest_cache"]
}

# AgentCore Lambda Layer
data "archive_file" "agents_layer" {
  type        = "zip"
  source_dir  = "${path.module}/../../lambda/layers/agents"
  output_path = "${path.module}/agents_layer.zip"
  excludes    = ["__pycache__", "*.pyc", ".pytest_cache"]
}

# Python Dependencies Layer
data "archive_file" "python_layer" {
  type        = "zip"
  source_dir  = "${path.module}/../../lambda/layers/python"
  output_path = "${path.module}/python_layer.zip"
  excludes    = ["__pycache__", "*.pyc", ".pytest_cache"]
}

resource "aws_lambda_layer_version" "python_layer" {
  filename         = data.archive_file.python_layer.output_path
  layer_name       = "${local.name_prefix}-python-layer"
  source_code_hash = data.archive_file.python_layer.output_base64sha256

  compatible_runtimes = [var.python_runtime]
  description         = "Python dependencies for Global Guide Bot"
}

resource "aws_lambda_layer_version" "agents_layer" {
  filename         = data.archive_file.agents_layer.output_path
  layer_name       = "${local.name_prefix}-agents-layer"
  source_code_hash = data.archive_file.agents_layer.output_base64sha256

  compatible_runtimes = [var.python_runtime]
  description         = "AgentCore components for Global Guide Bot"
}

# WhatsApp Webhook Lambda Function (embedded agents, no layers)
resource "aws_lambda_function" "whatsapp_webhook" {
  filename         = data.archive_file.whatsapp_webhook.output_path
  function_name    = "${local.name_prefix}-whatsapp-webhook"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "whatsapp_webhook.lambda_handler"
  runtime          = var.python_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size
  source_code_hash = data.archive_file.whatsapp_webhook.output_base64sha256

  environment {
    variables = {
      # Project configuration (for Parameter Store lookups)
      PROJECT_NAME             = var.project_name
      ENVIRONMENT              = var.environment
      # Note: AWS_REGION is automatically available as AWS_REGION env var in Lambda
      
      # DynamoDB tables
      USERS_TABLE              = aws_dynamodb_table.users.name
      GUIDES_TABLE             = aws_dynamodb_table.guides.name
      BOOKINGS_TABLE           = aws_dynamodb_table.bookings.name
      MESSAGES_TABLE           = aws_dynamodb_table.messages.name
      AVAILABILITY_TABLE       = aws_dynamodb_table.availability.name
      
      # S3 buckets
      MEDIA_BUCKET             = aws_s3_bucket.media.bucket
      NOVA_IMAGES_BUCKET       = aws_s3_bucket.nova_images.id
      
      # Bedrock configuration
      BEDROCK_MODEL_ID         = var.bedrock_model_id
      
      # WhatsApp API version
      WHATSAPP_API_VERSION     = "v20.0"
      
      # WhatsApp credentials (reverted from Parameter Store to env vars)
      WHATSAPP_ACCESS_TOKEN    = var.whatsapp_access_token
      WHATSAPP_PHONE_NUMBER_ID = var.whatsapp_phone_number_id
      WHATSAPP_VERIFY_TOKEN    = var.whatsapp_verify_token
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_cloudwatch_log_group.whatsapp_webhook,
  ]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-whatsapp-webhook"
    Type = "Lambda"
  })
}

# Message Processor Lambda Function
resource "aws_lambda_function" "message_processor" {
  filename         = data.archive_file.whatsapp_webhook.output_path
  function_name    = "${local.name_prefix}-message-processor"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "whatsapp_webhook.lambda_handler"
  runtime          = var.python_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size
  source_code_hash = data.archive_file.whatsapp_webhook.output_base64sha256

  layers = [
    aws_lambda_layer_version.agents_layer.arn,
    aws_lambda_layer_version.python_layer.arn
  ]

  environment {
    variables = {
      ENVIRONMENT        = var.environment
      PROJECT_NAME       = var.project_name
      USERS_TABLE        = aws_dynamodb_table.users.name
      GUIDES_TABLE       = aws_dynamodb_table.guides.name
      BOOKINGS_TABLE     = aws_dynamodb_table.bookings.name
      MESSAGES_TABLE     = aws_dynamodb_table.messages.name
      AVAILABILITY_TABLE = aws_dynamodb_table.availability.name
      MEDIA_BUCKET       = aws_s3_bucket.media.bucket
      BEDROCK_MODEL_ID   = var.bedrock_model_id
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_cloudwatch_log_group.message_processor,
  ]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-message-processor"
    Type = "Lambda"
  })
}

# Lambda Function URL removed for security - using API Gateway only