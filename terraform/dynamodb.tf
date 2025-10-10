# DynamoDB Tables for Thailand Guide Bot

# Users Table
resource "aws_dynamodb_table" "users" {
  name         = "${local.name_prefix}-users"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "userId"

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "platform"
    type = "S"
  }

  attribute {
    name = "createdAt"
    type = "S"
  }

  global_secondary_index {
    name            = "platform-created-index"
    hash_key        = "platform"
    range_key       = "createdAt"
    projection_type = "ALL"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-users"
    Type = "DynamoDB"
  })
}

# Guides Table
resource "aws_dynamodb_table" "guides" {
  name         = "${local.name_prefix}-guides"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "guideId"

  attribute {
    name = "guideId"
    type = "S"
  }

  attribute {
    name = "location"
    type = "S"
  }

  attribute {
    name = "rating"
    type = "N"
  }

  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name            = "location-rating-index"
    hash_key        = "location"
    range_key       = "rating"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "status-index"
    hash_key        = "status"
    projection_type = "ALL"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-guides"
    Type = "DynamoDB"
  })
}

# Bookings Table
resource "aws_dynamodb_table" "bookings" {
  name         = "${local.name_prefix}-bookings"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "bookingId"

  attribute {
    name = "bookingId"
    type = "S"
  }

  attribute {
    name = "touristId"
    type = "S"
  }

  attribute {
    name = "guideId"
    type = "S"
  }

  attribute {
    name = "bookingDate"
    type = "S"
  }

  global_secondary_index {
    name            = "tourist-date-index"
    hash_key        = "touristId"
    range_key       = "bookingDate"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "guide-date-index"
    hash_key        = "guideId"
    range_key       = "bookingDate"
    projection_type = "ALL"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-bookings"
    Type = "DynamoDB"
  })
}

# Messages Table
resource "aws_dynamodb_table" "messages" {
  name         = "${local.name_prefix}-messages"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "messageId"

  attribute {
    name = "messageId"
    type = "S"
  }

  attribute {
    name = "conversationId"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  global_secondary_index {
    name            = "conversation-timestamp-index"
    hash_key        = "conversationId"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-messages"
    Type = "DynamoDB"
  })
}

# Guide Availability Table
resource "aws_dynamodb_table" "availability" {
  name         = "${local.name_prefix}-availability"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "guideId"
  range_key    = "date"

  attribute {
    name = "guideId"
    type = "S"
  }

  attribute {
    name = "date"
    type = "S"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-availability"
    Type = "DynamoDB"
  })
}

# AgentCore Memory Table
resource "aws_dynamodb_table" "memory" {
  name         = "${local.name_prefix}-memory"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "userId"

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "lastUpdated"
    type = "N"
  }

  global_secondary_index {
    name            = "last-updated-index"
    hash_key        = "lastUpdated"
    projection_type = "KEYS_ONLY"
  }

  # TTL for automatic cleanup of old memory data (optional)
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-memory"
    Type = "DynamoDB"
    Purpose = "AgentCore Memory System"
  })
}