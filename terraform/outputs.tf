# Essential Outputs for Global Guide Bot - Enhanced AgentCore

# WhatsApp Webhook URL (Primary)
output "webhook_url" {
  description = "WhatsApp webhook URL for Meta Business configuration"
  value = "${aws_api_gateway_deployment.main.invoke_url}/webhook/whatsapp"
}

# System Environment Variables
output "environment_variables" {
  description = "Environment variables for scripts and applications"
  value = {
    AWS_REGION = var.aws_region
    GUIDES_TABLE_NAME = aws_dynamodb_table.guides.name
    USERS_TABLE_NAME = aws_dynamodb_table.users.name
    BOOKINGS_TABLE_NAME = aws_dynamodb_table.bookings.name
    MESSAGES_TABLE_NAME = aws_dynamodb_table.messages.name
    MEMORY_TABLE_NAME = aws_dynamodb_table.memory.name
  }
}

# Quick Commands
output "commands" {
  description = "Essential commands for setup and monitoring"
  value = {
    generate_guides = "GUIDES_TABLE_NAME=${aws_dynamodb_table.guides.name} AWS_REGION=${var.aws_region} python3 generate_200_guides.py"
    view_logs = "aws logs tail /aws/lambda/${aws_lambda_function.whatsapp_webhook.function_name} --follow"
  }
}

# System Info
output "system_info" {
  description = "Enhanced AgentCore system information"
  value = {
    architecture = "Enhanced AgentCore with Memory & Strands"
    region = var.aws_region
    environment = var.environment
  }
}
