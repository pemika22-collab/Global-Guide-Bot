"""
RegistrationAgent - Guide registration specialist
REPLICATES: src/tools/guide_registration_tool.py
Handles guide registration workflow for complete marketplace demo
"""

import json
import uuid
import boto3
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional
from .base_agent import BaseAgent


class RegistrationAgent(BaseAgent):
    """
    Specialized agent for guide registration
    REPLICATES guide_registration_tool.py approach:
    - AI-powered profile analysis
    - Auto-approval system
    - Complete marketplace workflow
    """
    
    def __init__(self):
        system_prompt = """You are a guide registration specialist for the Thailand Guide Bot marketplace.

Your responsibilities:
1. Help potential guides register for the platform
2. Collect required information (name, phone, specialties, languages, location, experience)
3. Analyze profiles using AI for quality assessment
4. Handle registration workflow and status updates
5. Manage guide availability updates

Registration Requirements:
- Name (required)
- Phone number (required) 
- Specialties (required) - what they specialize in
- Languages (required) - what languages they speak
- Location (required) - where they operate
- Gender (required) - male or female (for video assignment)
- Bio (required) - brief description about themselves
- Experience years (optional)

Always be encouraging and professional. Guide them through the registration process step by step."""

        super().__init__(
            name="registration",
            model_id="eu.amazon.nova-pro-v1:0",  # Nova Pro cross-region
            system_prompt=system_prompt
        )
        
        # Use shared context from orchestrator (persisted in DynamoDB)
        self.shared_context = {}
        
        # Initialize AWS clients
        self.dynamodb = boto3.resource('dynamodb')
        self.guides_table = self.dynamodb.Table('thailand-guide-bot-dev-guides')
        self.reasoning_steps = []
        
    async def process(
        self, 
        message: str, 
        context: Dict[str, Any],
        orchestrator: Any = None
    ) -> Dict[str, Any]:
        """Process registration request"""
        
        print(f"🤖 RegistrationAgent: Processing registration request...")
        
        # Use shared context from orchestrator
        self.shared_context = context
        
        # This shouldn't be called directly - use handle_agent_message
        result = await self.handle_agent_message("tourist", message)
        
        # Ensure context is returned
        if 'context' not in result:
            result['context'] = {}
        result['context'].update(self.shared_context)
        
        return result
        
    async def handle_agent_message(self, from_agent: str, message: str) -> Dict[str, Any]:
        """
        Handle message from another agent
        REPLICATES: guide_registration_tool.py lambda_handler
        """
        
        print(f"📝 RegistrationAgent: Received request from {from_agent}Agent")
        print(f"📋 Registration query: {message}")
        
        try:
            # Check if awaiting confirmation
            if self.shared_context.get('pending_registration'):
                message_lower = message.strip().lower()
                if 'yes' in message_lower or 'confirm' in message_lower or 'correct' in message_lower:
                    pending = self.shared_context['pending_registration']
                    return await self._confirm_registration(pending['guide_id'])
                elif 'no' in message_lower or 'cancel' in message_lower:
                    return await self._cancel_registration()
                else:
                    return {
                        "status": "awaiting_confirmation",
                        "message": "Please reply 'yes' to confirm or 'no' to cancel your registration."
                    }
            
            # Parse request
            try:
                request = json.loads(message)
                action = request.get('action')
                guide_data = request.get('guide_data', {})
            except json.JSONDecodeError:
                # Analyze message to determine intent
                intent_analysis = await self._analyze_registration_intent(message)
                action = intent_analysis.get('action')
                guide_data = intent_analysis.get('guide_data', {})
            
            print(f"🔍 Parsed action: {action}")
            print(f"🔍 Guide data: {guide_data}")
            
            # Route to appropriate handler (exactly like Lambda tool)
            if action == 'start_registration' or action == 'register':
                # Start registration flow - ask for information
                return await self._start_registration_flow(guide_data, request.get('user_message', ''))
            elif action == 'check_status':
                return await self._check_application_status(guide_data.get('phone_number'))
            elif action == 'update_availability':
                return await self._update_guide_availability(guide_data)
            else:
                return {
                    "status": "needs_clarification",
                    "message": "I can help you with guide registration. Please specify if you want to:\n- Register as a new guide\n- Check your application status\n- Update your availability",
                    "available_actions": ["register", "check_status", "update_availability"]
                }
                
        except Exception as e:
            print(f"❌ RegistrationAgent error: {str(e)}")
            return {
                "status": "error",
                "message": f"Sorry, there was an error processing your guide registration request: {str(e)}"
            }
    
    async def _analyze_registration_intent(self, message: str) -> Dict[str, Any]:
        """Analyze message to determine registration intent and extract data"""
        
        intent_prompt = f"""Analyze this message for guide registration intent:

Message: "{message}"

Determine:
1. What action they want (register, check_status, update_availability)
2. Extract any guide information provided

Respond in JSON format:
{{
    "action": "register|check_status|update_availability|unclear",
    "guide_data": {{
        "name": "extracted name if provided",
        "phone_number": "extracted phone if provided", 
        "specialties": ["specialty1", "specialty2"],
        "languages": ["language1", "language2"],
        "location": "extracted location if provided",
        "experience_years": number_if_provided,
        "bio": "extracted bio if provided"
    }},
    "missing_fields": ["field1", "field2"],
    "confidence": 0.0-1.0
}}"""

        try:
            response = self.call_bedrock(intent_prompt, max_tokens=500)
            
            # Parse JSON response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                intent_data = json.loads(response[json_start:json_end])
            else:
                # Fallback
                intent_data = {
                    "action": "unclear",
                    "guide_data": {},
                    "missing_fields": [],
                    "confidence": 0.5
                }
            
            self._add_reasoning("intent_analysis", intent_data)
            return intent_data
            
        except Exception as e:
            print(f"❌ Intent analysis error: {str(e)}")
            return {
                "action": "unclear",
                "guide_data": {},
                "missing_fields": [],
                "confidence": 0.0
            }
    
    async def _start_registration_flow(self, guide_data: Dict[str, Any], user_message: str) -> Dict[str, Any]:
        """
        Start guide registration - extract all info using AI
        """
        
        print("🚀 RegistrationAgent: Starting registration...")
        
        # Use AI to extract information
        extract_prompt = f"""Extract guide registration info from: "{user_message}"

CRITICAL: Only extract information that is ACTUALLY PROVIDED. If a field is not mentioned, leave it as null or empty.
DO NOT use placeholder values like "Not provided", "N/A", or "...".

IMPORTANT: Names can contain numbers (e.g., "John Guide123", "Prasert Guide3254") - these are valid names.
IMPORTANT: Bio includes any description about experience, background, or qualifications mentioned.

Extract if present:
- name: Full name including numbers if present (or null if not provided)
- phone_number: Phone number with country code (or null if not provided)
- specialties: Array of tour specialties mentioned (or [] if not provided)
- languages: Array of languages spoken (or [] if not provided)
- location: City/location where they operate (or null if not provided)
- gender: "male" or "female" (or null if not provided)
- bio: Any description about experience, background, qualifications (or null if not provided)
- experience_years: Years of experience as number (or null if not provided)

Example input: "My name is Prasert Guide3254, phone +66482350509, I'm based in Pattaya, I specialize in historical tours, I speak English and Thai, I am female, and I have 5 years of experience showing tourists around Thailand."

Example output: {{"name": "Prasert Guide3254", "phone_number": "+66482350509", "specialties": ["historical tours"], "languages": ["English", "Thai"], "location": "Pattaya", "gender": "female", "bio": "5 years of experience showing tourists around Thailand", "experience_years": 5}}

JSON only (use null for missing fields):
{{"name": null, "phone_number": null, "specialties": [], "languages": [], "location": null, "gender": null, "bio": null, "experience_years": null}}"""

        response = self.call_bedrock(extract_prompt, max_tokens=500)
        
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            extracted = json.loads(response[json_start:json_end])
            
            print(f"✅ Extracted: {extracted}")
            
            # Check required fields - including bio and gender
            required = ['name', 'phone_number', 'specialties', 'languages', 'location', 'bio', 'gender']
            # Check for missing, empty, placeholder, or "not provided" values
            def is_missing(value):
                if not value:
                    return True
                if value == '...' or value == '' or value == []:
                    return True
                if isinstance(value, str) and value.lower() in ['not provided', 'n/a', 'na', 'none', 'null']:
                    return True
                return False
            
            missing = [f for f in required if is_missing(extracted.get(f))]
            
            if missing:
                # Create friendly field names
                field_map = {
                    'phone_number': 'Phone',
                    'bio': 'Bio',
                    'gender': 'Gender'
                }
                friendly_missing = [field_map.get(f, f.title()) for f in missing]
                
                return {
                    "status": "need_info",
                    "message": f"""📋 *Guide Registration*

Please provide: {', '.join(friendly_missing)}

Format:
Name: [your name]
Phone: [number]
Specialties: [tours]
Languages: [languages]
Location: [city]
Gender: [male/female]
Bio: [brief description about yourself]"""
                }
            
            # Register the guide
            return await self._handle_guide_registration(extracted)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return {
                "status": "error",
                "message": """🌟 *Guide Registration*

Please provide:
Name: [name]
Phone: [number]
Specialties: [tours]
Languages: [languages]
Location: [city]
Gender: [male/female]
Bio: [brief description about yourself]"""
            }
    
    async def _handle_guide_registration(self, guide_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle new guide registration
        REPLICATES: guide_registration_tool.py handle_guide_registration()
        """
        
        print("📝 RegistrationAgent: Processing new guide registration...")
        
        try:
            # Validate required fields - including bio and gender
            required_fields = ['name', 'phone_number', 'specialties', 'languages', 'location', 'bio', 'gender']
            missing_fields = [field for field in required_fields if not guide_data.get(field)]
            
            if missing_fields:
                # Create friendly field names
                field_names = {
                    'phone_number': 'phone number',
                    'bio': 'brief bio (tell us about yourself)',
                    'gender': 'gender (male/female)'
                }
                friendly_missing = [field_names.get(f, f) for f in missing_fields]
                
                return {
                    "status": "missing_info",
                    "message": f"📋 Please provide the following information:\n\n{chr(10).join([f'• {field}' for field in friendly_missing])}\n\nPlease send all the information in one message.",
                    "missing_fields": missing_fields,
                    "current_data": guide_data
                }
            
            # Check if guide already exists (exactly like Lambda tool)
            existing_guide = await self._check_existing_guide(guide_data['phone_number'])
            if existing_guide:
                return {
                    "status": "already_exists",
                    "message": f"A guide with phone number {guide_data['phone_number']} is already registered. Status: {existing_guide.get('status', 'unknown')}"
                }
            
            # AI-powered profile analysis (exactly like Lambda tool)
            profile_analysis = await self._analyze_guide_profile_with_ai(guide_data)
            
            # Generate guide ID
            guide_id = f"guide_{datetime.now().strftime('%Y%m%d')}_{str(uuid.uuid4())[:8]}"
            
            # Determine video URL based on gender
            gender = guide_data.get('gender', '').lower()
            if 'male' in gender and 'female' not in gender:
                video_url = 'https://tinyurl.com/thailand-guide-male'
            elif 'female' in gender:
                video_url = 'https://tinyurl.com/thailand-guide-female'
            else:
                # Default to male if unclear
                video_url = 'https://tinyurl.com/thailand-guide-male'
            
            # Create guide profile
            new_guide = {
                'guideId': guide_id,
                'name': guide_data['name'],
                'phoneNumber': guide_data['phone_number'],  # Store at top level
                'age': guide_data.get('age', 30),
                'gender': gender,
                'location': guide_data['location'],
                'regions': [guide_data['location']],
                'languages': guide_data['languages'] if isinstance(guide_data['languages'], list) else guide_data['languages'].split(','),
                'specialties': guide_data['specialties'] if isinstance(guide_data['specialties'], list) else guide_data['specialties'].split(','),
                'experience_years': guide_data.get('experience_years', 0),
                # NO rating for new guides - they need to earn it
                'total_reviews': 0,
                'price_per_day': Decimal('80'),
                'bio': guide_data.get('bio', ''),
                'videoUrl': video_url,  # Gender-based video
                'contact': {
                    'whatsapp': guide_data['phone_number'],
                    'email': f"{guide_data['name'].lower().replace(' ', '.')}@thailandguides.com"
                },
                'availability': 'available',
                'status': 'pending_approval',  # Always pending for new guides
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'ai_analysis': profile_analysis
            }
            
            # First, show confirmation and ask for approval
            specialties_str = ', '.join(guide_data['specialties']) if isinstance(guide_data['specialties'], list) else guide_data['specialties']
            languages_str = ', '.join(guide_data['languages']) if isinstance(guide_data['languages'], list) else guide_data['languages']
            
            confirmation_message = f"""📋 *Please confirm your registration details:*

👤 *Name*: {guide_data['name']}
📱 *Phone*: {guide_data['phone_number']}
📍 *Location*: {guide_data['location']}
⚧ *Gender*: {gender.title()}
🎯 *Specialties*: {specialties_str}
🗣️ *Languages*: {languages_str}
📝 *Bio*: {guide_data.get('bio', 'N/A')}
💰 *Rate*: $80 USD/day (default - you can adjust this later)

Is this information correct? Reply *"yes"* to submit or *"no"* to cancel."""

            # Store in shared context for confirmation (persisted in DynamoDB)
            pending_registration = {
                'guide_data': guide_data,
                'new_guide': new_guide,
                'guide_id': guide_id,
                'profile_analysis': profile_analysis
            }
            self.shared_context['pending_registration'] = pending_registration
            
            return {
                "status": "awaiting_confirmation",
                "guide_id": guide_id,
                "message": confirmation_message,
                "requires_confirmation": True,
                "context": {
                    "pending_registration": pending_registration
                }
            }
            
        except Exception as e:
            print(f"❌ Registration error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "message": f"Sorry, there was an error processing your registration: {str(e)}"
            }
    
    async def _confirm_registration(self, guide_id: str) -> Dict[str, Any]:
        """Complete registration after confirmation"""
        try:
            pending = self.shared_context.get('pending_registration', {})
            if not pending:
                return {
                    "status": "error",
                    "message": "No pending registration found. Please start registration again."
                }
            
            new_guide = pending['new_guide']
            guide_data = pending['guide_data']
            
            # Convert any float values to Decimal for DynamoDB
            def convert_floats_to_decimal(obj):
                """Recursively convert floats to Decimal for DynamoDB"""
                if isinstance(obj, float):
                    return Decimal(str(obj))
                elif isinstance(obj, dict):
                    return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_floats_to_decimal(v) for v in obj]
                return obj
            
            # Helper to convert Decimals back to regular numbers for JSON serialization
            def convert_decimals_to_float(obj):
                """Recursively convert Decimals to float for JSON serialization"""
                if isinstance(obj, Decimal):
                    return float(obj)
                elif isinstance(obj, dict):
                    return {k: convert_decimals_to_float(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_decimals_to_float(v) for v in obj]
                return obj
            
            new_guide = convert_floats_to_decimal(new_guide)
            
            # Save to DynamoDB
            self.guides_table.put_item(Item=new_guide)
            
            # Clear pending registration from shared context
            self.shared_context.pop('pending_registration', None)
            
            # Success message - NO AI analysis, NO rating
            specialties_str = ', '.join(guide_data['specialties']) if isinstance(guide_data['specialties'], list) else guide_data['specialties']
            
            success_message = f"""🎉 *Registration Successful!*

Welcome to Thailand Guide Bot marketplace! 🇹🇭

📋 *Your Profile*:
• *Guide ID*: {guide_id}
• *Name*: {guide_data['name']}
• *Location*: {guide_data['location']}
• *Specialties*: {specialties_str}
• *Status*: Pending Approval
• *Base Rate*: $80 USD/day (you can adjust this anytime)

⏳ *Next Steps*:
1. Our team will review your application within 24 hours
2. You'll receive a notification once approved
3. After approval, you can start receiving bookings

💡 *Tips*:
• You can update your rate by messaging: "update my rate"
• Set your availability: "update availability"
• Check application status: "check my status"

Thank you for joining our guide community!"""
            
            response = {
                "status": "registered",
                "guide_id": guide_id,
                "message": success_message
            }
            
            # Ensure no Decimal objects in response for JSON serialization
            return convert_decimals_to_float(response)
            
        except Exception as e:
            print(f"❌ Confirmation error: {str(e)}")
            return {
                "status": "error",
                "message": f"Sorry, there was an error completing your registration: {str(e)}"
            }
    
    async def _cancel_registration(self) -> Dict[str, Any]:
        """Cancel pending registration"""
        self.shared_context.pop('pending_registration', None)
        return {
            "status": "cancelled",
            "message": "Registration cancelled. You can start again anytime by saying 'register as a guide'."
        }
    
    async def _analyze_guide_profile_with_ai(self, guide_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use AI to analyze and optimize guide profile
        REPLICATES: guide_registration_tool.py analyze_guide_profile_with_ai()
        """
        
        try:
            # Exact same prompt as Lambda tool
            prompt = f"""Analyze this guide registration profile and provide recommendations:

Name: {guide_data.get('name', 'Not provided')}
Specialties: {', '.join(guide_data.get('specialties', [])) if isinstance(guide_data.get('specialties'), list) else guide_data.get('specialties', 'Not provided')}
Languages: {', '.join(guide_data.get('languages', [])) if isinstance(guide_data.get('languages'), list) else guide_data.get('languages', 'Not provided')}
Experience: {guide_data.get('experience_years', 0)} years
Location: {guide_data.get('location', 'Not provided')}
Bio: {guide_data.get('bio', 'Not provided')}

Please analyze:
1. Profile completeness and quality
2. Market demand for their specialties
3. Language skills for tourist market
4. Experience level appropriateness
5. Overall recommendation (approve/review/reject)

Provide a JSON response with:
- recommendation: "approve" | "review" | "reject"
- score: 1-100
- summary: brief analysis
- suggestions: improvement recommendations
- market_fit: how well they fit Thailand tourism market"""

            response = self.call_bedrock(prompt, max_tokens=1000)
            
            # Try to parse JSON from AI response (exactly like Lambda tool)
            try:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start != -1 and json_end != -1:
                    analysis_json = json.loads(response[json_start:json_end])
                    
                    # Convert any numeric scores to Decimal for DynamoDB
                    if 'score' in analysis_json and isinstance(analysis_json['score'], (int, float)):
                        analysis_json['score'] = Decimal(str(analysis_json['score']))
                    
                    self._add_reasoning("ai_profile_analysis", analysis_json)
                    return analysis_json
                else:
                    # Fallback if JSON not found
                    fallback_analysis = {
                        'recommendation': 'review',
                        'score': Decimal('75'),
                        'summary': response[:200] + '...' if len(response) > 200 else response,
                        'suggestions': 'Please review profile manually',
                        'market_fit': 'Good potential for Thailand tourism market'
                    }
                    self._add_reasoning("ai_profile_analysis_fallback", fallback_analysis)
                    return fallback_analysis
            except json.JSONDecodeError:
                # Fallback if AI doesn't return valid JSON (exactly like Lambda tool)
                fallback_analysis = {
                    'recommendation': 'review',
                    'score': Decimal('75'),
                    'summary': response[:200] + '...' if len(response) > 200 else response,
                    'suggestions': 'Please review profile manually',
                    'market_fit': 'Good potential for Thailand tourism market'
                }
                self._add_reasoning("ai_profile_analysis_json_error", fallback_analysis)
                return fallback_analysis
                
        except Exception as e:
            print(f"❌ AI profile analysis error: {str(e)}")
            # Exact same fallback as Lambda tool
            fallback_analysis = {
                'recommendation': 'review',
                'score': Decimal('50'),
                'summary': 'AI analysis unavailable, manual review required',
                'suggestions': 'Complete all profile fields for better evaluation',
                'market_fit': 'Manual assessment needed'
            }
            self._add_reasoning("ai_profile_analysis_error", {"error": str(e), "fallback": fallback_analysis})
            return fallback_analysis
    
    async def _check_existing_guide(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Check if guide already exists by phone number
        REPLICATES: guide_registration_tool.py check_existing_guide()
        """
        
        try:
            # Check in guides table by scanning contact.whatsapp field (exactly like Lambda tool)
            response = self.guides_table.scan(
                FilterExpression='contact.whatsapp = :phone',
                ExpressionAttributeValues={':phone': phone_number}
            )
            
            if response['Items']:
                existing_guide = response['Items'][0]
                self._add_reasoning("existing_guide_check", {"found": True, "guide_id": existing_guide.get('guideId')})
                return existing_guide
            
            self._add_reasoning("existing_guide_check", {"found": False})
            return None
            
        except Exception as e:
            print(f"❌ Error checking existing guide: {str(e)}")
            self._add_reasoning("existing_guide_check_error", {"error": str(e)})
            return None
    
    async def _check_application_status(self, phone_number: Optional[str]) -> Dict[str, Any]:
        """
        Check guide application status
        REPLICATES: guide_registration_tool.py check_application_status()
        """
        
        try:
            if not phone_number:
                return {
                    "status": "missing_phone",
                    "message": "Please provide your phone number to check application status."
                }
            
            # Check in guides table (exactly like Lambda tool)
            guide = await self._check_existing_guide(phone_number)
            if not guide:
                return {
                    "status": "not_found",
                    "message": "No application found for this phone number. Would you like to register as a guide?"
                }
            
            if guide.get('status') == 'active':
                # Exact same active status message as Lambda tool
                active_message = f"""✅ **Guide Status: ACTIVE**

**Guide ID**: {guide.get('guideId', 'N/A')}
**Name**: {guide.get('name', 'N/A')}
**Location**: {guide.get('location', 'N/A')}
**Rating**: {guide.get('rating', 'N/A')}/5.0
**Total Reviews**: {guide.get('total_reviews', 0)}
**Specialties**: {', '.join(guide.get('specialties', []))}
**Languages**: {', '.join(guide.get('languages', []))}

You're all set to receive bookings! 🎉"""
                
                return {
                    "status": "active",
                    "guide_data": guide,
                    "message": active_message
                }
            else:
                # Exact same status messages as Lambda tool
                status_messages = {
                    'pending_approval': '⏳ Your application is under review',
                    'approved': '✅ Approved - Setting up your profile',
                    'rejected': '❌ Application not approved',
                    'suspended': '⚠️ Account temporarily suspended'
                }
                status_msg = status_messages.get(guide.get('status'), 'Unknown status')
                
                pending_message = f"""📋 **Application Status**: {status_msg}

**Guide ID**: {guide.get('guideId', 'N/A')}
**Name**: {guide.get('name', 'N/A')}
**Submitted**: {guide.get('created_at', 'N/A')}
**Last Updated**: {guide.get('updated_at', 'N/A')}

{guide.get('ai_analysis', {}).get('summary', 'No additional information available.')}"""
                
                return {
                    "status": guide.get('status', 'unknown'),
                    "guide_data": guide,
                    "message": pending_message
                }
                
        except Exception as e:
            print(f"❌ Status check error: {str(e)}")
            return {
                "status": "error",
                "message": f"Sorry, there was an error checking your application status: {str(e)}"
            }
    
    async def _update_guide_availability(self, guide_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update guide availability
        REPLICATES: guide_registration_tool.py update_guide_availability()
        """
        
        try:
            phone_number = guide_data.get('phone_number')
            if not phone_number:
                return {
                    "status": "missing_phone",
                    "message": "Please provide your phone number to update availability."
                }
            
            # Find guide (exactly like Lambda tool)
            guide = await self._check_existing_guide(phone_number)
            if not guide or guide.get('status') != 'active':
                return {
                    "status": "not_active",
                    "message": "Guide not found or not active. Please check your registration status."
                }
            
            # Simple availability toggle (exactly like Lambda tool)
            current_status = guide.get('availability', 'available')
            new_status = 'unavailable' if current_status == 'available' else 'available'
            
            # Update availability (exactly like Lambda tool)
            self.guides_table.update_item(
                Key={'guideId': guide['guideId']},
                UpdateExpression='SET availability = :status, updated_at = :updated',
                ExpressionAttributeValues={
                    ':status': new_status,
                    ':updated': datetime.now().isoformat()
                }
            )
            
            # Exact same success message as Lambda tool
            success_message = f"""✅ **Availability Updated**

**Status**: {new_status.title()}
**Guide**: {guide.get('name', 'N/A')}
**Location**: {guide.get('location', 'N/A')}

Your availability has been updated successfully. Tourists will {'see you as available for bookings' if new_status == 'available' else 'not see you in search results'}.

Current Status: {new_status.upper()}"""
            
            self._add_reasoning("availability_update", {
                "guide_id": guide['guideId'],
                "old_status": current_status,
                "new_status": new_status
            })
            
            return {
                "status": "updated",
                "availability": new_status,
                "message": success_message
            }
            
        except Exception as e:
            print(f"❌ Availability update error: {str(e)}")
            return {
                "status": "error",
                "message": f"Sorry, there was an error updating your availability: {str(e)}"
            }
    
    def _add_reasoning(self, step: str, details: Any):
        """Add reasoning step"""
        self.reasoning_steps.append({
            "agent": "RegistrationAgent",
            "step": step,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        })