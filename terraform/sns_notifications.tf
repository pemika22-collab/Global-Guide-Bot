# SNS Topic for WhatsApp Token Renewal Notifications
resource "aws_sns_topic" "whatsapp_token_renewal" {
  name = "${var.project_name}-${var.environment}-whatsapp-token-renewal"

  tags = {
    Name        = "${var.project_name}-${var.environment}-whatsapp-token-renewal"
    Environment = var.environment
    Project     = var.project_name
    Type        = "SNS"
    Purpose     = "WhatsApp Token Renewal Alerts"
  }
}

# Email subscription for token renewal notifications
resource "aws_sns_topic_subscription" "whatsapp_token_email" {
  topic_arn = aws_sns_topic.whatsapp_token_renewal.arn
  protocol  = "email"
  endpoint  = "tipsupa.c@gmail.com"
}

# CloudWatch Log Metric Filter for WhatsApp 401 Errors
resource "aws_cloudwatch_log_metric_filter" "whatsapp_token_expired" {
  name           = "${var.project_name}-${var.environment}-whatsapp-token-expired"
  log_group_name = aws_cloudwatch_log_group.lambda_logs["whatsapp-webhook"].name
  pattern        = "[timestamp, request_id, level=\"ERROR\", ..., message=\"*HTTP Error 401: Unauthorized*\"]"

  metric_transformation {
    name      = "WhatsAppTokenExpired"
    namespace = "${var.project_name}/${var.environment}/WhatsApp"
    value     = "1"
    default_value = "0"
  }
}

# CloudWatch Alarm for WhatsApp Token Expiration
resource "aws_cloudwatch_metric_alarm" "whatsapp_token_expired_alarm" {
  alarm_name          = "${var.project_name}-${var.environment}-whatsapp-token-expired"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = "WhatsAppTokenExpired"
  namespace           = "${var.project_name}/${var.environment}/WhatsApp"
  period              = "300"  # 5 minutes
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "WhatsApp access token has expired and needs renewal"
  alarm_actions       = [aws_sns_topic.whatsapp_token_renewal.arn]
  ok_actions          = [aws_sns_topic.whatsapp_token_renewal.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "${var.project_name}-${var.environment}-whatsapp-token-expired"
    Environment = var.environment
    Project     = var.project_name
    Type        = "CloudWatch"
    Purpose     = "WhatsApp Token Monitoring"
  }
}

# Additional CloudWatch Log Metric Filter for general WhatsApp API errors
resource "aws_cloudwatch_log_metric_filter" "whatsapp_api_errors" {
  name           = "${var.project_name}-${var.environment}-whatsapp-api-errors"
  log_group_name = aws_cloudwatch_log_group.lambda_logs["whatsapp-webhook"].name
  pattern        = "[timestamp, request_id, level=\"ERROR\", ..., message=\"*Error sending WhatsApp message*\"]"

  metric_transformation {
    name      = "WhatsAppAPIErrors"
    namespace = "${var.project_name}/${var.environment}/WhatsApp"
    value     = "1"
    default_value = "0"
  }
}

# CloudWatch Alarm for WhatsApp API Errors
resource "aws_cloudwatch_metric_alarm" "whatsapp_api_errors_alarm" {
  alarm_name          = "${var.project_name}-${var.environment}-whatsapp-api-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "WhatsAppAPIErrors"
  namespace           = "${var.project_name}/${var.environment}/WhatsApp"
  period              = "300"  # 5 minutes
  statistic           = "Sum"
  threshold           = "5"    # Alert if more than 5 errors in 10 minutes
  alarm_description   = "High number of WhatsApp API errors detected"
  alarm_actions       = [aws_sns_topic.whatsapp_token_renewal.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "${var.project_name}-${var.environment}-whatsapp-api-errors"
    Environment = var.environment
    Project     = var.project_name
    Type        = "CloudWatch"
    Purpose     = "WhatsApp API Monitoring"
  }
}

# Lambda function to send detailed token renewal instructions
resource "aws_lambda_function" "whatsapp_token_notifier" {
  filename         = data.archive_file.whatsapp_token_notifier.output_path
  function_name    = "${var.project_name}-${var.environment}-whatsapp-token-notifier"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "whatsapp_token_notifier.lambda_handler"
  source_code_hash = data.archive_file.whatsapp_token_notifier.output_base64sha256
  runtime         = "python3.9"
  timeout         = 30

  environment {
    variables = {
      SNS_TOPIC_ARN = aws_sns_topic.whatsapp_token_renewal.arn
      PROJECT_NAME  = var.project_name
      ENVIRONMENT   = var.environment
    }
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-whatsapp-token-notifier"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Lambda"
    Purpose     = "WhatsApp Token Notifications"
  }
}

# Archive for the token notifier Lambda
data "archive_file" "whatsapp_token_notifier" {
  type        = "zip"
  output_path = "${path.module}/whatsapp_token_notifier.zip"
  source {
    content = templatefile("${path.module}/whatsapp_token_notifier.py", {
      webhook_url = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${var.environment}/webhook/whatsapp"
      verify_token = var.whatsapp_verify_token
    })
    filename = "whatsapp_token_notifier.py"
  }
}

# SNS Topic Policy to allow CloudWatch to publish
resource "aws_sns_topic_policy" "whatsapp_token_renewal_policy" {
  arn = aws_sns_topic.whatsapp_token_renewal.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "cloudwatch.amazonaws.com"
        }
        Action = "SNS:Publish"
        Resource = aws_sns_topic.whatsapp_token_renewal.arn
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
}

# EventBridge rule to trigger token renewal reminder (daily check)
resource "aws_cloudwatch_event_rule" "whatsapp_token_check" {
  name                = "${var.project_name}-${var.environment}-whatsapp-token-check"
  description         = "Daily check for WhatsApp token health"
  schedule_expression = "cron(0 9 * * ? *)"  # 9 AM UTC daily

  tags = {
    Name        = "${var.project_name}-${var.environment}-whatsapp-token-check"
    Environment = var.environment
    Project     = var.project_name
    Type        = "EventBridge"
    Purpose     = "WhatsApp Token Health Check"
  }
}

# EventBridge target for the token check
resource "aws_cloudwatch_event_target" "whatsapp_token_check_target" {
  rule      = aws_cloudwatch_event_rule.whatsapp_token_check.name
  target_id = "WhatsAppTokenNotifierTarget"
  arn       = aws_lambda_function.whatsapp_token_notifier.arn
}

# Permission for EventBridge to invoke the Lambda
resource "aws_lambda_permission" "allow_eventbridge_token_notifier" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.whatsapp_token_notifier.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.whatsapp_token_check.arn
}