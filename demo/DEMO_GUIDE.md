# Global Guide Bot - Demo Guide

## Quick Start

Run these 5 demo flows to see the complete AI tourism marketplace:

```bash
python3 demo/demo_flow_1_text_booking.py      # Text-based booking
python3 demo/demo_flow_2_image_booking.py     # Image analysis + booking  
python3 demo/demo_flow_3_guide_registration.py # Guide registration
python3 demo/demo_flow_4_cultural_intelligence.py # Cultural guidance
python3 demo/demo_flow_5_strands_showcase.py   # Conversation threading
```

## Demo Flows

### Flow 1: Text-Based Booking
Complete booking from "I need a guide in Bangkok" to confirmed reservation with pricing.

### Flow 2: Image-Based Booking  
Upload temple/beach image → AI analysis → guide recommendations → booking confirmation.

### Flow 3: Guide Registration
Guide applies → AI validates data → creates profile → registration confirmed.

### Flow 4: Cultural Intelligence
Ask cultural questions → get comprehensive guidance with do's, don'ts, and context.

### Flow 5: Strands System ✨ NEW
Demonstrates intelligent conversation categorization and multi-threaded conversations.

## What You'll See

- ✅ **Live AWS API calls** to Amazon Nova Pro/Act
- ✅ **Real booking confirmations** with confirmation IDs  
- ✅ **Actual database queries** with 200+ Thai guides
- ✅ **Multi-agent coordination** with real delegation
- ✅ **Complete end-to-end flows** in 1-2 minutes each

## Prerequisites

**⚠️ REQUIRED: Deploy Terraform Stack First**

Before running any demo flows, you must deploy the AWS infrastructure by following SETUP_GUIDE.md until step 5

**Note:** Demo flows require live AWS resources (DynamoDB tables, Lambda functions, Nova Pro access) that are created by the Terraform deployment.

All demos are **interactive** - follow the prompts to experience the full AI conversation flows with real confirmations.

## Demo Architecture

**🖥️ Local Execution:**
- All 5 demo flows run as **local Python scripts** on your machine
- They import AgentCore modules directly from `src/lambda/agentcore/`
- **No Lambda invocation** - bypass Lambda layer for faster testing

**☁️ Direct AWS API Calls:**
- **Bedrock/Nova Pro**: Direct API calls to `bedrock-runtime.eu-west-1.amazonaws.com`
- **DynamoDB**: Direct access to tables (guides, bookings, users, memory)
- **S3**: Direct access for image storage

**🏗️ Architecture Flow:**
```
Demo Script (Local) → AgentCore (Local) → AWS APIs (Bedrock/DynamoDB/S3)
```

**Why This Works:**
- Same codebase as deployed Lambda functions
- Uses your local AWS credentials (`~/.aws/credentials`)
- More efficient than Lambda cold starts for demos
- Simulates production behavior without API Gateway overhead
