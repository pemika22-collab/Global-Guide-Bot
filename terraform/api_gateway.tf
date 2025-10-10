# API Gateway for Thailand Guide Bot

# API Gateway REST API
resource "aws_api_gateway_rest_api" "main" {
  name        = "${local.name_prefix}-api"
  description = "Thailand Guide Bot API Gateway"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-api"
    Type = "API Gateway"
  })
}

# API Gateway Resource for Webhook
resource "aws_api_gateway_resource" "webhook" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "webhook"
}

# API Gateway Resource for WhatsApp
resource "aws_api_gateway_resource" "whatsapp" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.webhook.id
  path_part   = "whatsapp"
}

# API Gateway Method for WhatsApp GET (verification)
resource "aws_api_gateway_method" "whatsapp_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.whatsapp.id
  http_method   = "GET"
  authorization = "NONE"
}

# API Gateway Method for WhatsApp POST (webhook)
resource "aws_api_gateway_method" "whatsapp_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.whatsapp.id
  http_method   = "POST"
  authorization = "NONE"
}

# CORS preflight for web demo
resource "aws_api_gateway_method" "whatsapp_options" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.whatsapp.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# API Gateway Integration for WhatsApp GET
resource "aws_api_gateway_integration" "whatsapp_get" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.whatsapp.id
  http_method = aws_api_gateway_method.whatsapp_get.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.whatsapp_webhook.invoke_arn
}

# API Gateway Integration for WhatsApp POST
resource "aws_api_gateway_integration" "whatsapp_post" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.whatsapp.id
  http_method = aws_api_gateway_method.whatsapp_post.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.whatsapp_webhook.invoke_arn
}

# CORS preflight integration
resource "aws_api_gateway_integration" "whatsapp_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.whatsapp.id
  http_method = aws_api_gateway_method.whatsapp_options.http_method
  type        = "MOCK"
  
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "whatsapp_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.whatsapp.id
  http_method = aws_api_gateway_method.whatsapp_options.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "whatsapp_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.whatsapp.id
  http_method = aws_api_gateway_method.whatsapp_options.http_method
  status_code = aws_api_gateway_method_response.whatsapp_options.status_code
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS,POST,PUT'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# Lambda Permission for API Gateway GET
resource "aws_lambda_permission" "api_gateway_whatsapp_get" {
  statement_id  = "AllowExecutionFromAPIGatewayGET"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.whatsapp_webhook.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# Lambda Permission for API Gateway POST
resource "aws_lambda_permission" "api_gateway_whatsapp_post" {
  statement_id  = "AllowExecutionFromAPIGatewayPOST"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.whatsapp_webhook.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# API Gateway Deployment
resource "aws_api_gateway_deployment" "main" {
  depends_on = [
    aws_api_gateway_integration.whatsapp_get,
    aws_api_gateway_integration.whatsapp_post,
    aws_api_gateway_integration.whatsapp_options,
  ]

  rest_api_id = aws_api_gateway_rest_api.main.id
  stage_name  = var.environment

  # Force new deployment on every apply
  triggers = {
    redeployment = timestamp()
  }

  lifecycle {
    create_before_destroy = true
  }
}