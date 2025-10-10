# S3 bucket for demo guide videos (PRIVATE with pre-signed URLs)

resource "aws_s3_bucket" "guide_videos" {
  bucket = "thailand-guide-videos-demo-${var.environment}"
  
  tags = {
    Name        = "Guide Demo Videos"
    Environment = var.environment
    Project     = "Thailand Guide Bot"
  }
}

# Keep bucket private (default security)
resource "aws_s3_bucket_public_access_block" "guide_videos" {
  bucket = aws_s3_bucket.guide_videos.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CORS for video playback in WhatsApp/browsers
resource "aws_s3_bucket_cors_configuration" "guide_videos" {
  bucket = aws_s3_bucket.guide_videos.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# IAM policy for Lambda to generate pre-signed URLs
resource "aws_iam_policy" "s3_video_presign" {
  name        = "${var.project_name}-${var.environment}-s3-video-presign"
  description = "Allow Lambda to generate pre-signed URLs for guide videos"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.guide_videos.arn}/*"
      }
    ]
  })
}

# Attach policy to Lambda execution role (used by all Lambda functions)
resource "aws_iam_role_policy_attachment" "lambda_s3_video" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = aws_iam_policy.s3_video_presign.arn
}

# Outputs moved to outputs.tf for centralized management
