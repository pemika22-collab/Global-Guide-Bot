# S3 Bucket for Nova Act Image Storage

resource "aws_s3_bucket" "nova_images" {
  bucket = "${var.project_name}-${var.environment}-nova-images"

  tags = {
    Name        = "Nova Act Image Storage"
    Environment = var.environment
    Purpose     = "Temporary storage for WhatsApp images"
  }
}

# Lifecycle policy to auto-delete old images
resource "aws_s3_bucket_lifecycle_configuration" "nova_images_lifecycle" {
  bucket = aws_s3_bucket.nova_images.id

  rule {
    id     = "delete-old-images"
    status = "Enabled"

    filter {}  # Apply to all objects in bucket

    expiration {
      days = 1  # Delete images after 24 hours - perfect for hackathon demo
    }

    noncurrent_version_expiration {
      noncurrent_days = 1
    }
  }
}

# Block all public access
resource "aws_s3_bucket_public_access_block" "nova_images" {
  bucket = aws_s3_bucket.nova_images.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning for safety
resource "aws_s3_bucket_versioning" "nova_images" {
  bucket = aws_s3_bucket.nova_images.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "nova_images" {
  bucket = aws_s3_bucket.nova_images.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Outputs moved to outputs.tf for centralized management
