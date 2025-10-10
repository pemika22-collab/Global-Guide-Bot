# CloudWatch Monitoring and Alerting - Task 13 Implementation
# Comprehensive monitoring for all system components

# CloudWatch Log Groups for all Lambda functions
resource "aws_cloudwatch_log_group" "lambda_logs" {
  for_each = toset([
    "whatsapp-webhook",
    "guide-matching-tool",
    "cultural-intelligence-tool",
    "booking-coordination-tool",
    "guide-registration-tool"
  ])

  name              = "/aws/lambda/${var.project_name}-${var.environment}-${each.key}"
  retention_in_days = var.environment == "prod" ? 30 : 7

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Component   = "monitoring"
  }
}

# CloudWatch Dashboard for system overview
resource "aws_cloudwatch_dashboard" "system_overview" {
  dashboard_name = "${var.project_name}-${var.environment}-overview"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", "${var.project_name}-${var.environment}-whatsapp-webhook"],
            [".", "Errors", ".", "."],
            [".", "Invocations", ".", "."],
            ["AWS/Lambda", "Duration", "FunctionName", "${var.project_name}-${var.environment}-guide-matching-tool"],
            [".", "Errors", ".", "."],
            [".", "Invocations", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Lambda Performance Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", "${var.project_name}-${var.environment}-guides"],
            [".", "ConsumedWriteCapacityUnits", ".", "."],
            [".", "ConsumedReadCapacityUnits", "TableName", "${var.project_name}-${var.environment}-bookings"],
            [".", "ConsumedWriteCapacityUnits", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "DynamoDB Capacity Metrics"
          period  = 300
        }
      },
      {
        type   = "log"
        x      = 0
        y      = 12
        width  = 24
        height = 6

        properties = {
          query  = "SOURCE '/aws/lambda/${var.project_name}-${var.environment}-whatsapp-webhook' | fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 20"
          region = var.aws_region
          title  = "Recent Errors"
        }
      }
    ]
  })
}

# Performance Alarms for Lambda Functions
resource "aws_cloudwatch_metric_alarm" "lambda_duration_alarm" {
  for_each = toset([
    "whatsapp-webhook",
    "guide-matching-tool",
    "cultural-intelligence-tool",
    "booking-coordination-tool",
    "guide-registration-tool"
  ])

  alarm_name          = "${var.project_name}-${var.environment}-${each.key}-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = "5000" # 5 seconds
  alarm_description   = "This metric monitors lambda duration for ${each.key}"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = "${var.project_name}-${var.environment}-${each.key}"
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Component   = "monitoring"
  }
}

# Error Rate Alarms for Lambda Functions
resource "aws_cloudwatch_metric_alarm" "lambda_error_alarm" {
  for_each = toset([
    "whatsapp-webhook",
    "guide-matching-tool",
    "cultural-intelligence-tool",
    "booking-coordination-tool",
    "guide-registration-tool"
  ])

  alarm_name          = "${var.project_name}-${var.environment}-${each.key}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors lambda errors for ${each.key}"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = "${var.project_name}-${var.environment}-${each.key}"
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Component   = "monitoring"
  }
}

# DynamoDB Performance Alarms
resource "aws_cloudwatch_metric_alarm" "dynamodb_read_throttle" {
  for_each = toset([
    "guides",
    "bookings",
    "users",
    "messages"
  ])

  alarm_name          = "${var.project_name}-${var.environment}-${each.key}-read-throttle"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ReadThrottledEvents"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors DynamoDB read throttling for ${each.key}"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    TableName = "${var.project_name}-${var.environment}-${each.key}"
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Component   = "monitoring"
  }
}

resource "aws_cloudwatch_metric_alarm" "dynamodb_write_throttle" {
  for_each = toset([
    "guides",
    "bookings",
    "users",
    "messages"
  ])

  alarm_name          = "${var.project_name}-${var.environment}-${each.key}-write-throttle"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "WriteThrottledEvents"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors DynamoDB write throttling for ${each.key}"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    TableName = "${var.project_name}-${var.environment}-${each.key}"
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Component   = "monitoring"
  }
}

# API Gateway Performance Alarms
resource "aws_cloudwatch_metric_alarm" "api_gateway_4xx_errors" {
  alarm_name          = "${var.project_name}-${var.environment}-api-4xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "4XXError"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors API Gateway 4XX errors"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ApiName = "${var.project_name}-${var.environment}-api"
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Component   = "monitoring"
  }
}

resource "aws_cloudwatch_metric_alarm" "api_gateway_5xx_errors" {
  alarm_name          = "${var.project_name}-${var.environment}-api-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "This metric monitors API Gateway 5XX errors"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ApiName = "${var.project_name}-${var.environment}-api"
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Component   = "monitoring"
  }
}

resource "aws_cloudwatch_metric_alarm" "api_gateway_latency" {
  alarm_name          = "${var.project_name}-${var.environment}-api-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Latency"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Average"
  threshold           = "2000" # 2 seconds
  alarm_description   = "This metric monitors API Gateway latency"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ApiName = "${var.project_name}-${var.environment}-api"
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Component   = "monitoring"
  }
}

# SNS Topic for Alerts
resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-${var.environment}-alerts"

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Component   = "monitoring"
  }
}

# SNS Topic Subscription (Email)
# SNS email subscription - configure manually in AWS Console
# resource "aws_sns_topic_subscription" "email_alerts" {
#   topic_arn = aws_sns_topic.alerts.arn
#   protocol  = "email"
#   endpoint  = "your-email@example.com"
# }

# Custom Metrics for Business Logic
resource "aws_cloudwatch_log_metric_filter" "booking_success_rate" {
  name           = "${var.project_name}-${var.environment}-booking-success"
  log_group_name = aws_cloudwatch_log_group.lambda_logs["booking-coordination-tool"].name
  pattern        = "[timestamp, request_id, level=\"INFO\", message=\"BOOKING_SUCCESS\", ...]"

  metric_transformation {
    name      = "BookingSuccessCount"
    namespace = "${var.project_name}/${var.environment}/Business"
    value     = "1"
  }
}

resource "aws_cloudwatch_log_metric_filter" "booking_failure_rate" {
  name           = "${var.project_name}-${var.environment}-booking-failure"
  log_group_name = aws_cloudwatch_log_group.lambda_logs["booking-coordination-tool"].name
  pattern        = "[timestamp, request_id, level=\"ERROR\", message=\"BOOKING_FAILURE\", ...]"

  metric_transformation {
    name      = "BookingFailureCount"
    namespace = "${var.project_name}/${var.environment}/Business"
    value     = "1"
  }
}

resource "aws_cloudwatch_log_metric_filter" "guide_registration_success" {
  name           = "${var.project_name}-${var.environment}-guide-registration-success"
  log_group_name = aws_cloudwatch_log_group.lambda_logs["guide-registration-tool"].name
  pattern        = "[timestamp, request_id, level=\"INFO\", message=\"GUIDE_REGISTERED\", ...]"

  metric_transformation {
    name      = "GuideRegistrationCount"
    namespace = "${var.project_name}/${var.environment}/Business"
    value     = "1"
  }
}

# Performance Insights for Business Metrics
resource "aws_cloudwatch_metric_alarm" "booking_success_rate_alarm" {
  alarm_name          = "${var.project_name}-${var.environment}-booking-success-rate"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "BookingSuccessCount"
  namespace           = "${var.project_name}/${var.environment}/Business"
  period              = "900" # 15 minutes
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "This metric monitors booking success rate"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "breaching"

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Component   = "monitoring"
  }
}

# X-Ray Tracing removed - not needed for core functionality

# Outputs moved to outputs.tf for centralized management