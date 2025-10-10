# IAM Roles and Policies for Thailand Guide Bot

# Lambda Execution Role
resource "aws_iam_role" "lambda_execution" {
  name = "${local.name_prefix}-lambda-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-lambda-execution"
    Type = "IAM"
  })
}

# Lambda Basic Execution Policy
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}



# DynamoDB Access Policy
resource "aws_iam_policy" "dynamodb_access" {
  name        = "${local.name_prefix}-dynamodb-access"
  description = "Policy for DynamoDB access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem"
        ]
        Resource = [
          aws_dynamodb_table.users.arn,
          aws_dynamodb_table.guides.arn,
          aws_dynamodb_table.bookings.arn,
          aws_dynamodb_table.messages.arn,
          aws_dynamodb_table.availability.arn,
          aws_dynamodb_table.memory.arn,
          "${aws_dynamodb_table.users.arn}/index/*",
          "${aws_dynamodb_table.guides.arn}/index/*",
          "${aws_dynamodb_table.bookings.arn}/index/*",
          "${aws_dynamodb_table.messages.arn}/index/*",
          "${aws_dynamodb_table.availability.arn}/index/*",
          "${aws_dynamodb_table.memory.arn}/index/*"
        ]
      }
    ]
  })

  tags = local.common_tags
}

# Attach DynamoDB Policy to Lambda Role
resource "aws_iam_role_policy_attachment" "lambda_dynamodb" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = aws_iam_policy.dynamodb_access.arn
}

# S3 Access Policy
resource "aws_iam_policy" "s3_access" {
  name        = "${local.name_prefix}-s3-access"
  description = "Policy for S3 access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetObjectVersion"
        ]
        Resource = [
          aws_s3_bucket.media.arn,
          "${aws_s3_bucket.media.arn}/*",
          aws_s3_bucket.nova_images.arn,
          "${aws_s3_bucket.nova_images.arn}/*"
        ]
      }
    ]
  })

  tags = local.common_tags
}

# Attach S3 Policy to Lambda Role
resource "aws_iam_role_policy_attachment" "lambda_s3" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = aws_iam_policy.s3_access.arn
}

# Bedrock Access Policy
resource "aws_iam_policy" "bedrock_access" {
  name        = "${local.name_prefix}-bedrock-access"
  description = "Policy for AWS Bedrock access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:GetFoundationModel",
          "bedrock:ListFoundationModels"
        ]
        Resource = [
          # Keep Claude 3.5 Sonnet permissions for tools
          "arn:aws:bedrock:eu-west-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
          "arn:aws:bedrock:eu-west-1::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0",
          "arn:aws:bedrock:eu-west-2::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
          "arn:aws:bedrock:eu-west-2::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0",
          "arn:aws:bedrock:eu-west-3::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
          "arn:aws:bedrock:eu-west-3::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0",
          "arn:aws:bedrock:eu-central-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
          "arn:aws:bedrock:eu-central-1::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0",
          "arn:aws:bedrock:eu-north-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
          "arn:aws:bedrock:eu-north-1::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0",
          # Cross-region inference profiles
          "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/eu.anthropic.claude-3-5-sonnet-20240620-v1:0",
          "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/eu.anthropic.claude-3-haiku-20240307-v1:0",
          # Amazon Nova Pro permissions - all EU regions
          "arn:aws:bedrock:eu-west-1::foundation-model/amazon.nova-pro-v1:0",
          "arn:aws:bedrock:eu-west-2::foundation-model/amazon.nova-pro-v1:0",
          "arn:aws:bedrock:eu-west-3::foundation-model/amazon.nova-pro-v1:0",
          "arn:aws:bedrock:eu-central-1::foundation-model/amazon.nova-pro-v1:0",
          "arn:aws:bedrock:eu-north-1::foundation-model/amazon.nova-pro-v1:0",
          # Cross-region inference profiles for Nova Pro
          "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/eu.amazon.nova-pro-v1:0"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeAgent",
          "bedrock-agent-runtime:InvokeAgent",
          "bedrock-agent:GetAgent",
          "bedrock-agent:ListAgents"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:agent/*",
          "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:agent-alias/*/*"
        ]
      }
    ]
  })

  tags = local.common_tags
}

# Attach Bedrock Policy to Lambda Role
resource "aws_iam_role_policy_attachment" "lambda_bedrock" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = aws_iam_policy.bedrock_access.arn
}

# Translate Access Policy
resource "aws_iam_policy" "translate_access" {
  name        = "${local.name_prefix}-translate-access"
  description = "Policy for Amazon Translate access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "translate:TranslateText",
          "translate:DetectDominantLanguage"
        ]
        Resource = "*"
      }
    ]
  })

  tags = local.common_tags
}

# Attach Translate Policy to Lambda Role
resource "aws_iam_role_policy_attachment" "lambda_translate" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = aws_iam_policy.translate_access.arn
}