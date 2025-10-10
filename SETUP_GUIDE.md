# Global Guide Bot - Setup Guide

Enhanced AgentCore system with Memory & Strands architecture for intelligent tour guide assistance.

**Region Requirement**: Deploy strictly in `eu-west-1` only (IAM bound to EU cross-region inference models).

## Quick Setup

### 1. AWS Credentials
```bash
aws configure
# or
aws sso login
```

### 2. Configure Terraform Variables
```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values if you would like to change Default verify token:
- Keep default `whatsapp_access_token` and `whatsapp_phone_number_id` for testing without real WhatsApp
- Default verify token: `global_guide_bot_verify_2024`

### 3. Deploy Infrastructure
```bash
terraform init
terraform apply -auto-approve
```

Note the outputs:
- **Webhook URL**: `https://xxx.execute-api.eu-west-1.amazonaws.com/dev/webhook/whatsapp`
- **Generate 200 mock up guides command**: Copy from terraform output 

### 4. Populate Guide Database
Export environment variables and run the populate script:
```bash
# Copy the exact command from terraform output, example:
export GUIDES_TABLE_NAME=thailand-guide-bot-dev-guides
export AWS_REGION=eu-west-1
python3 generate_200_guides.py
```

### 5. Enable Bedrock Models
Go to AWS Bedrock Console in `eu-west-1` and enable model access for:
- **Nova Pro** (Text & Vision) - Required for AI semantic analysis
- **Nova Reel** (Video) - Optional for video processing
- **Nova Canvas** - Optional for image generation

### 6. Test Demo Flows
System is ready to test all 5 demo flows:
1. Tourist booking conversation
2. Image analysis with Nova Pro
3. Guide registration
4. Cultural intelligence
5. Memory & Strands system

see /demo/DEMO_GUIDE.md for more detail

## WhatsApp Integration (Optional)

For real WhatsApp testing:

### 7. Meta Developer Setup
- Register at https://developers.facebook.com/
- Create WhatsApp Business App
- Get temporary access token and phone number ID
- try sending message from meta business console you should get testing message to your pick phone number in whatsapp

### 8. Update Configuration
Update `terraform.tfvars` with real values:
```
whatsapp_access_token    = "YOUR_REAL_TOKEN"
whatsapp_phone_number_id = "YOUR_REAL_PHONE_ID"
```

Run `terraform apply` to update.

### 9. Configure Webhook
In Meta Business Console:
- **Callback URL**: Use webhook URL from terraform output
- **Verify Token**: `global_guide_bot_verify_2024` or the value that you change in step 2
- **Subscribe to**: messages **** very important step

### 10. Test
Send "Hi" from your registered phone number to the WhatsApp Business number.

## Architecture
- **Enhanced AgentCore** with Memory & Strands
- **AI Models**: Nova Pro (Text & Vision), Nova Reel (Video), Nova Canvas (Image)
- **Agents**: Tourist, Cultural, Guide, Booking, Registration
- **Features**: Semantic analysis, multi-modal processing, context continuity


