# CloudFront distribution for guide videos
# Provides clean, short URLs that agents can display fully
# Uses OAC (Origin Access Control) - newer, more secure than OAI

resource "aws_cloudfront_distribution" "guide_videos" {
  origin {
    domain_name              = aws_s3_bucket.guide_videos.bucket_regional_domain_name
    origin_id                = "S3-${aws_s3_bucket.guide_videos.id}"
    origin_access_control_id = aws_cloudfront_origin_access_control.guide_videos.id
  }

  enabled = true
  comment = "Thailand Guide Bot - Video Distribution"

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${aws_s3_bucket.guide_videos.id}"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 86400    # 24 hours
    max_ttl     = 31536000 # 1 year
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Name        = "Guide Videos CDN"
    Environment = var.environment
    Project     = "Thailand Guide Bot"
  }
}

resource "aws_cloudfront_origin_access_control" "guide_videos" {
  name                              = "guide-videos-oac-${var.environment}"
  description                       = "OAC for guide videos bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# Update S3 bucket policy to allow CloudFront access via OAC
resource "aws_s3_bucket_policy" "guide_videos_cloudfront" {
  bucket = aws_s3_bucket.guide_videos.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontServicePrincipal"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.guide_videos.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.guide_videos.arn
          }
        }
      }
    ]
  })
}

# Outputs moved to outputs.tf for centralized management
