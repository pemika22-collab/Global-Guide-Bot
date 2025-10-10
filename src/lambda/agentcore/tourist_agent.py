"""
TouristAgent - Primary interface for tourist interactions
Routes requests to specialized agents
"""

import json
from typing import Dict, Any, List
from datetime import datetime
from .base_agent import BaseAgent


class TouristAgent(BaseAgent):
    """
    Main conversation agent for tourists
    Understands requests and coordinates with other agents
    """
    
    def __init__(self):
        system_prompt = """You are an expert Thailand travel consultant with deep knowledge of Thai culture, destinations, and experiences.

INTELLIGENT DELEGATION RULES:
1. Cultural Intelligence: If user asks about temples, culture, traditions, etiquette, customs, respect, Buddhist practices, Thai culture → delegate to CulturalAgent
2. Guide Matching: If user mentions guide, tour guide, local guide, find guide, book guide, recommend guide, show me guides, tour, experience, activity → delegate to GuideAgent  
3. Booking: If user wants to book a specific guide or confirms a selection → delegate to BookingAgent

CONVERSATION INTELLIGENCE:
- Analyze user intent and preferences intelligently
- Extract group type (couple, family, friends, solo) from context clues
- Detect budget signals from numbers and currency mentions
- Ask intelligent follow-up questions based on what's missing
- For couples: ask about romantic experiences
- For cultural interests: ask about depth of cultural immersion
- For food interests: ask about spice tolerance
- Only ask about budget and group size if not already known

Keep responses conversational and helpful. Focus on understanding their travel desires."""

        super().__init__(
            name="tourist",
            model_id="eu.amazon.nova-pro-v1:0",  # Nova Pro cross-region
            system_prompt=system_prompt
        )
        self.reasoning_steps = []
        self.conversation_context = {}  # Store conversation state
        
    async def process(
        self, 
        message: str, 
        context: Dict[str, Any],
        orchestrator: Any = None
    ) -> Dict[str, Any]:
        """Process tourist message and coordinate with other agents"""
        
        print(f"🤖 TouristAgent: Processing message...")
        
        # Check for explicit reset commands FIRST
        message_lower = message.strip().lower()
        if message_lower in ['cancel', 'reset', 'start over', 'restart', 'clear', 'new search', 'new booking']:
            print("🔄 User requested reset")
            # AGGRESSIVE RESET - Clear everything
            self.conversation_context = {}
            self.reasoning_steps = []
            
            # Force return without any context processing
            return {
                "message": "🔄 Fresh start! I'm ready to help you find a guide. Where would you like to go?",
                "intent": {"type": "reset"},
                "reasoning": [],
                "context": {},
                "force_reset": True  # Signal to orchestrator
            }
        
        # Check if THIS MESSAGE is an image message (before merging context)
        # This must be checked BEFORE updating conversation_context
        is_current_image = context.get('has_image') and context.get('image_url') and context.get('message_type') == 'image'
        
        # Merge incoming context with stored context
        self.conversation_context.update(context)
        
        # Check if this is an image message - route to Cultural Agent
        if is_current_image:
            print(f"📸 Image message detected - routing to CulturalAgent")
            self._add_reasoning("Decision", "Image detected - delegating to CulturalAgent for analysis")
            
            # Delegate to Cultural Agent with image
            cultural_response = await self.delegate_to(
                agent_name="cultural",
                message=json.dumps({
                    "action": "analyze_image",
                    "image_url": context['image_url'],
                    "user_question": message
                }),
                orchestrator=orchestrator
            )
            
            # Extract location AND interests from analysis for potential booking
            analysis = cultural_response.get('analysis', {})
            location = analysis.get('location', 'Bangkok')  # Default to Bangkok for Thai temples
            
            # Nova Act already provides content_type - use it directly
            # This is semantic understanding from the AI, not keyword matching
            content_type = analysis.get('content_type', 'general')
            
            # Map Nova Act's content_type to guide interests
            # This mapping is based on Nova Act's semantic analysis
            interest_map = {
                'temple': 'temples',
                'beach': 'beaches',
                'market': 'markets',
                'food': 'food tours',
                'cultural_activity': 'cultural sites',
                'location': 'cultural sites',
                'general': 'cultural sites'
            }
            
            suggested_interest = interest_map.get(content_type, 'cultural sites')
            
            # Store in context for next interaction
            self.conversation_context['suggested_location'] = location
            self.conversation_context['suggested_interests'] = suggested_interest
            self.conversation_context['last_interaction_type'] = 'image_analysis'
            
            # Clear image flags so next message isn't treated as image
            self.conversation_context.pop('has_image', None)
            self.conversation_context.pop('image_url', None)
            self.conversation_context.pop('message_type', None)
            
            print(f"📍 Stored context - Location: {location}, Interests: {suggested_interest}")
            
            return {
                "message": cultural_response.get('message', 'I analyzed your image!'),
                "intent": {"type": "cultural_question"},
                "cultural_info": cultural_response,
                "reasoning": self.reasoning_steps,
                "context": self.conversation_context
            }
        
        # PRIORITY CHECK: Image analysis responses take precedence over registration
        # Check if user is responding affirmatively after image analysis FIRST
        if self.conversation_context.get('last_interaction_type') == 'image_analysis':
            print(f"🔍 Checking if user wants guide after image analysis")
            print(f"   User message: '{message}'")
            
            # Simple keyword matching for affirmative responses
            affirmative_keywords = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'please', 'find', 'search', 'show', 'guide']
            message_lower_check = message.lower().strip()
            
            wants_guide = any(keyword in message_lower_check for keyword in affirmative_keywords)
            
            if wants_guide:
                print("✅ User wants to book guide after image analysis - starting booking flow")
                
                # Pre-populate extracted with suggested location and interests from image
                extracted = {}
                if self.conversation_context.get('suggested_location'):
                    # Extract city from "Wat Phra Kaew, Bangkok" → "Bangkok"
                    suggested_location = self.conversation_context['suggested_location']
                    if ',' in suggested_location:
                        city = suggested_location.split(',')[-1].strip()
                    else:
                        city = suggested_location
                    extracted['location'] = city
                    print(f"📍 Pre-filling location from image: {city}")
                
                if self.conversation_context.get('suggested_interests'):
                    extracted['interests'] = self.conversation_context['suggested_interests']
                    print(f"🎯 Pre-filling interests from image: {extracted['interests']}")
                
                # Clear image analysis flag after first response to prevent interference with subsequent messages
                self.conversation_context.pop('last_interaction_type', None)
                
                # Treat as guide search intent
                intent = {
                    'type': 'guide_search',
                    'extracted': extracted
                }
                response = await self._handle_guide_search(message, intent, orchestrator)
                return response
            else:
                print("❌ User doesn't want guide - clearing image analysis context")
                # User said no or something else - clear the image analysis context
                self.conversation_context.pop('last_interaction_type', None)
                self.conversation_context.pop('suggested_location', None)
                self.conversation_context.pop('suggested_interests', None)
        
        # Check if we're in registration flow and user is confirming
        elif self.conversation_context.get('in_registration_flow'):
            if message_lower in ['yes', 'no', 'confirm', 'cancel', 'correct']:
                print("📝 User responding to registration - delegating to RegistrationAgent")
                registration_response = await self.delegate_to(
                    agent_name="registration",
                    message=message,
                    orchestrator=orchestrator,
                    context=self.conversation_context
                )
                # Clear registration flow if completed or canceled
                if registration_response.get('status') in ['success', 'cancelled']:
                    self.conversation_context.pop('in_registration_flow', None)
                # Convert any Decimal objects to float for JSON serialization
                def convert_decimals_to_float(obj):
                    """Recursively convert Decimals to float for JSON serialization"""
                    from decimal import Decimal
                    if isinstance(obj, Decimal):
                        return float(obj)
                    elif isinstance(obj, dict):
                        return {k: convert_decimals_to_float(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_decimals_to_float(v) for v in obj]
                    return obj
                
                response = {
                    "message": registration_response.get('message', 'Registration processed.'),
                    "intent": {"type": "guide_registration"},
                    "registration_info": convert_decimals_to_float(registration_response),
                    "reasoning": self.reasoning_steps,
                    "context": self.conversation_context
                }
                
                return convert_decimals_to_float(response)
        
        # Check for timeout (5 minutes = 300 seconds)
        import time
        current_time = time.time()
        last_interaction = self.conversation_context.get('last_interaction_time', current_time)
        # Convert to float in case it's a Decimal from DynamoDB
        last_interaction = float(last_interaction) if last_interaction else current_time
        time_diff = current_time - last_interaction
        
        if time_diff > 300:  # 5 minutes
            print(f"⏰ Context timeout ({time_diff:.0f}s > 300s) - resetting")
            self.conversation_context.clear()
            self.conversation_context['last_interaction_time'] = current_time
            return {
                "message": "Your session timed out. Let's start fresh! How can I help you today?",
                "intent": {"type": "general"},
                "reasoning": self.reasoning_steps,
                "context": {"last_interaction_time": current_time}
            }
        
        # Update last interaction time
        self.conversation_context['last_interaction_time'] = current_time
        
        # Add to history
        self.add_to_history("user", message)
        
        # Check if we're awaiting specific information
        if self.conversation_context.get('awaiting_location'):
            print("📍 User providing location")
            # Use AI to understand and correct location typos
            location_prompt = f"""Analyze this input: "{message}"

If it's a Thailand city name (even with typos), respond with the correct city name.
If it's NOT a city (like a date "12/12/2025" or number "1" or "2"), respond with "INVALID".

Valid Thailand cities: Bangkok, Phuket, Chiang Mai, Pattaya, Krabi, Hua Hin, Koh Samui, Ayutthaya

Examples:
- "bankok" → Bangkok
- "pucket" → Phuket
- "chaing mai" → Chiang Mai
- "12/12/2025" → INVALID
- "1" → INVALID

Respond with ONLY the corrected city name or "INVALID"."""
            
            corrected_location = self.call_bedrock(location_prompt, max_tokens=50).strip()
            
            if corrected_location.upper() == 'INVALID':
                # Not a valid location - ask again
                print(f"⚠️ '{message}' is not a valid location")
                return {
                    "message": "Please provide a city name in Thailand (e.g., Bangkok, Phuket, Chiang Mai, Pattaya, Krabi).",
                    "intent": {"type": "guide_search"},
                    "reasoning": self.reasoning_steps,
                    "context": self.conversation_context
                }
            
            # Use the corrected location
            search_criteria = self.conversation_context.get('search_criteria', {})
            search_criteria['location'] = corrected_location
            print(f"✅ Location corrected: '{message}' → '{corrected_location}'")
            intent = {
                'type': 'guide_search',
                'extracted': search_criteria
            }
            self.conversation_context['awaiting_location'] = False
        elif self.conversation_context.get('awaiting_customer_name'):
            print("👤 User providing name")
            customer_name = message.strip()
            
            # Get booking details from context
            guide_id = self.conversation_context.get('selected_guide_id', '')
            guide_name = self.conversation_context.get('selected_guide_name', '')
            booking_details = self.conversation_context.get('booking_details', {})
            
            # Show booking summary and ask for confirmation
            date = booking_details.get('date', 'requested date')
            location = booking_details.get('location', 'requested location')
            
            confirmation_message = f"""📋 *Booking Summary:*

👤 Name: {customer_name}
🗓️ Date: {date}
📍 Location: {location}
👨‍🏫 Guide: {guide_name}

Please confirm to proceed with booking. Reply 'yes' to confirm or 'no' to cancel."""
            
            # Update context BEFORE returning - CRITICAL for next message
            # DON'T clear context - just update the flags
            self.conversation_context['awaiting_customer_name'] = False  # Clear this flag
            self.conversation_context['awaiting_booking_confirmation'] = True
            self.conversation_context['customer_name'] = customer_name
            self.conversation_context['selected_guide_id'] = guide_id
            self.conversation_context['selected_guide_name'] = guide_name
            self.conversation_context['booking_details'] = booking_details
            print(f"🔄 Context updated - awaiting_booking_confirmation: {self.conversation_context.get('awaiting_booking_confirmation')}")
            
            return {
                "message": confirmation_message,
                "intent": {"type": "booking_confirmation"},
                "reasoning": self.reasoning_steps,
                "context": self.conversation_context
            }
        elif self.conversation_context.get('awaiting_booking_confirmation'):
            print("✅ User confirming/canceling booking")
            confirmation = message.strip().lower()
            
            if 'yes' in confirmation or 'confirm' in confirmation or 'ok' in confirmation:
                # User confirmed - proceed with booking
                guide_id = self.conversation_context.get('selected_guide_id', '')
                guide_name = self.conversation_context.get('selected_guide_name', '')
                customer_name = self.conversation_context.get('customer_name', '')
                booking_details = self.conversation_context.get('booking_details', {})
                
                self.conversation_context['awaiting_booking_confirmation'] = False
                
                # Execute the booking
                return await self._execute_confirmed_booking(
                    guide_id=guide_id,
                    guide_name=guide_name,
                    customer_name=customer_name,
                    booking_details=booking_details,
                    orchestrator=orchestrator
                )
            else:
                # User canceled - clear ALL booking-related context
                print("❌ Booking canceled - clearing context")
                self.conversation_context.clear()  # Clear everything
                return {
                    "message": "Booking canceled. Would you like to search for other guides?",
                    "intent": {"type": "general"},
                    "reasoning": self.reasoning_steps,
                    "context": {}
                }
        elif self.conversation_context.get('awaiting_interests'):
            print("🎯 User providing interests")
            # Extract interests from message
            search_criteria = self.conversation_context.get('search_criteria', {})
            search_criteria['interests'] = [message.strip()]
            intent = {
                'type': 'guide_search',
                'extracted': search_criteria
            }
            self.conversation_context['awaiting_interests'] = False
        elif self.conversation_context.get('awaiting_date'):
            print("📅 User providing date")
            # Extract date from message
            from datetime import datetime
            search_criteria = self.conversation_context.get('search_criteria', {})
            # Use AI to parse the date
            date_prompt = f"""Convert this date to YYYY-MM-DD format: '{message}'

Today is {datetime.now().strftime('%Y-%m-%d')}.

CRITICAL: Respond with ONLY the date in YYYY-MM-DD format. NO explanations, NO extra text.

Examples:
- Input: "12/12/2025" → Output: 2025-12-12
- Input: "December 15" → Output: 2025-12-15
- Input: "next Monday" → Output: 2025-10-13

Your response (date only):"""
            parsed_date = self.call_bedrock(date_prompt, max_tokens=20).strip()
            
            # Validate date is not in the past
            try:
                requested_date = datetime.strptime(parsed_date, '%Y-%m-%d')
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                if requested_date.date() < today.date():
                    print(f"⚠️ Date {parsed_date} is in the past")
                    return {
                        "message": f"The date {parsed_date} is in the past. Please provide a future date for your tour.",
                        "intent": {'type': 'guide_search', 'extracted': search_criteria},
                        "reasoning": self.reasoning_steps,
                        "context": {
                            "awaiting_date": True,
                            "search_criteria": search_criteria
                        }
                    }
            except Exception as e:
                print(f"⚠️ Date parsing error: {e}")
                return {
                    "message": "I couldn't understand that date format. Please provide a date like 'December 15' or 'next Monday'.",
                    "intent": {'type': 'guide_search', 'extracted': search_criteria},
                    "reasoning": self.reasoning_steps,
                    "context": {
                        "awaiting_date": True,
                        "search_criteria": search_criteria
                    }
                }
            
            search_criteria['date'] = parsed_date
            
            # Check if we have suggested_location from image analysis
            if self.conversation_context.get('suggested_location') and not search_criteria.get('location'):
                # Extract just the city name from "Wat Phra Kaew, Bangkok" → "Bangkok"
                suggested_location = self.conversation_context['suggested_location']
                # Split by comma and take the last part (usually the city)
                if ',' in suggested_location:
                    city = suggested_location.split(',')[-1].strip()
                else:
                    city = suggested_location
                search_criteria['location'] = city
                print(f"📍 Using location from image analysis: {city}")
            
            # Check if we have suggested_interests from image analysis
            if self.conversation_context.get('suggested_interests') and not search_criteria.get('interests'):
                search_criteria['interests'] = self.conversation_context['suggested_interests']
                print(f"🎯 Using interests from image analysis: {search_criteria['interests']}")
            
            intent = {
                'type': 'guide_search',
                'extracted': search_criteria
            }
            self.conversation_context['awaiting_date'] = False
        else:

            
            # Analyze intent normally with AI
            intent = await self._analyze_intent(message, self.conversation_context)
        
        self._add_reasoning("Intent Analysis", intent)
        
        # CRITICAL FIX: If there's no previous guide search, this CANNOT be a booking confirmation
        # Initial requests should always be guide_search, never booking_confirmation
        if (intent['type'] == 'booking_confirmation' and 
            not self.conversation_context.get('last_guide_search')):
            print(f"🔄 Converting booking_confirmation to guide_search - no previous guide context")
            intent['type'] = 'guide_search'
        
        # Route based on intent
        if intent['type'] == 'guide_registration':
            response = await self._handle_guide_registration(message, intent, orchestrator, context)
        elif intent['type'] == 'guide_search':
            response = await self._handle_guide_search(message, intent, orchestrator)
        elif intent['type'] == 'more_guides':
            response = await self._handle_more_guides(message, intent, orchestrator)
        elif intent['type'] == 'cultural_question':
            response = await self._handle_cultural_question(message, intent, orchestrator)
        elif intent['type'] == 'booking_confirmation':
            response = await self._handle_booking(message, intent, orchestrator)
        else:
            response = await self._handle_general_conversation(message, self.conversation_context)
            
            # Handle delegation from general conversation (like working Lambda)
            if response.get('delegate_to') == 'cultural':
                response = await self._handle_cultural_question(message, {"type": "cultural_question"}, orchestrator)
            elif response.get('delegate_to') == 'guide':
                # Extract criteria from message (like working Lambda)
                criteria = self._extract_criteria_from_message(message)
                response = await self._handle_guide_search(message, {"type": "guide_search", "extracted": criteria}, orchestrator)
            
        # Add to history
        self.add_to_history("assistant", response['message'])
        
        # Update stored context
        if 'context' in response:
            self.conversation_context.update(response['context'])
        
        # Always return current context
        response['context'] = self.conversation_context
        
        return response
        
    async def _analyze_intent(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user intent"""
        
        # Filter context to remove user_id and other sensitive info
        filtered_context = {k: v for k, v in context.items() 
                          if k not in ['user_id', 'timestamp', 'last_interaction_time']}
        
        prompt = f"""Analyze this tourist message and determine intent:

Message: "{message}"

Context: {json.dumps(filtered_context, indent=2)}

CRITICAL DISTINCTIONS:
- Location: CITY NAMES ONLY (Bangkok, Chiang Mai, Phuket, Pattaya, Krabi, etc.)
- Interests: ACTIVITY/TOUR TYPES (temple tours, beach tours, food tours, cultural tours, etc.)

Examples:
- "temple tour in Bangkok" → location: "Bangkok", interests: ["temple tours"]
- "I want a temple guide" → location: "" (use from context), interests: ["temple tours"]
- "beach guide in Phuket" → location: "Phuket", interests: ["beach tours"]
- "food tour Bangkok" → location: "Bangkok", interests: ["food tours"]

Determine:
1. Intent type: guide_search, cultural_question, booking_confirmation, guide_registration, more_guides, or general
2. Extracted information

GUIDE REGISTRATION DETECTION (HIGHEST PRIORITY):
- If user expresses desire to register, become, sign up, join, or apply as a guide
- This includes typos and variations like "beome a guide", "become guide", "want to be guide"
- This is guide_registration intent
- Examples: 
  * "3" or "option 3"
  * "register as a guide" 
  * "become a guide" or "beome a guide" (typo)
  * "I want to register"
  * "sign up as guide"
  * "join as guide"
  * "apply to be a guide"
  * "want to be a guide"

For guide_search, extract:
- location: CITY NAME ONLY (Bangkok, Chiang Mai, Phuket, etc.) - NOT activity types
- interests: ACTIVITY TYPES as array (["temple tours"], ["beach tours"], etc.)
- date: Tour date (ONLY if explicitly mentioned - do NOT invent dates)
- number_of_people: Number of people
- tour_type: Type of tour

CRITICAL: Only extract date if user explicitly mentions a date like "December 15", "next Monday", "tomorrow", etc. 
If no date is mentioned, leave date field empty or null.

CRITICAL: Extract customer names from patterns like:
- "My name is John" → customer_name: "John"
- "hi Sarah here" → customer_name: "Sarah" 
- "Adam is here" → customer_name: "Adam"
- "this is Mike" → customer_name: "Mike"

For booking_confirmation, extract:
- guide_name: Name of guide to book (e.g., "Anong", "Ratchanee", "book Ploy")
- guide_id: Guide ID if mentioned (format: guide_XXX)
- guide_selection_number: If user says "guide #1" or "I'll take guide 2", extract the number
- customer_name: Tourist's name (e.g., "Sarah Johnson", "My name is Adam", "hi John here", "Adam is here")
- date: Tour date
- number_of_people: Number of people
- tour_type: Type of tour

IMPORTANT BOOKING DETECTION:
- If user says just a guide name (e.g., "ratchanee", "Ploy", "Apinya"), this is booking_confirmation
- If user says "book [name]", "I want [name]", "[name] please", this is booking_confirmation
- If user is selecting a guide by number (e.g., "I'll take guide #1"), this is booking_confirmation

MORE GUIDES REQUEST:
- If user says "more", "more guides", "show more", "other options", set type to "more_guides"

Respond in JSON format:
{{
    "type": "guide_search|cultural_question|booking_confirmation|guide_registration|more_guides|general",
    "confidence": 0.0-1.0,
    "extracted": {{
        "guide_name": "...",
        "guide_id": "...",
        "customer_name": "...",
        "location": "Bangkok",
        "date": "2025-10-08",
        "number_of_people": 2,
        "interests": ["temple tours"],
        "tour_type": "temple tour",
        "other": {{}}
    }},
    "reasoning": "why you chose this intent"
}}"""

        response = self.call_bedrock(prompt, max_tokens=500)
        
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            intent = json.loads(response[json_start:json_end])
            return intent
        except:
            # Fallback
            return {
                "type": "general",
                "confidence": 0.5,
                "extracted": {},
                "reasoning": "Could not parse intent"
            }
            
    async def _handle_guide_search(
        self, 
        message: str, 
        intent: Dict[str, Any],
        orchestrator: Any
    ) -> Dict[str, Any]:
        """Handle guide search request"""
        
        print(f"🔍 TouristAgent: Detected guide search request")
        
        # Check if we have date - if not, ask for it
        extracted = intent.get('extracted', {})
        if not extracted.get('date'):
            print("📅 No date provided - asking for date")
            return {
                "message": "Great! When would you like to book a guide? Please provide the date (e.g., 'December 15' or 'next Monday').",
                "intent": intent,
                "reasoning": self.reasoning_steps,
                "context": {
                    "awaiting_date": True,
                    "search_criteria": extracted
                }
            }
        
        # Check if we have location - if not, ask for it
        if not extracted.get('location'):
            print("📍 No location provided - asking for location")
            return {
                "message": f"Perfect! For {extracted.get('date')}, which city would you like to visit? (e.g., Bangkok, Phuket, Chiang Mai, Pattaya)",
                "intent": intent,
                "reasoning": self.reasoning_steps,
                "context": {
                    "awaiting_location": True,
                    "search_criteria": extracted
                }
            }
        
        # Check if we have interests - if not, ask for them
        if not extracted.get('interests'):
            print("🎯 No interests provided - asking for interests")
            return {
                "message": f"Great! What activities interest you in {extracted.get('location')}? (e.g., temples, beaches, food tours, cultural sites)",
                "intent": intent,
                "reasoning": self.reasoning_steps,
                "context": {
                    "awaiting_interests": True,
                    "search_criteria": extracted
                }
            }
        
        self._add_reasoning("Decision", "Delegating to GuideAgent for matching")
        
        # Delegate to GuideAgent
        guide_response = await self.delegate_to(
            agent_name="guide",
            message=json.dumps({
                "action": "search_guides",
                "criteria": extracted
            }),
            orchestrator=orchestrator
        )
        
        # Format response for user
        response_text = self._format_guide_results(guide_response)
        
        # Store guide results and search criteria in context
        guides = guide_response.get('guides', [])
        
        return {
            "message": response_text,
            "intent": intent,
            "guide_results": guide_response,
            "reasoning": self.reasoning_steps,
            "context": {
                "last_guide_search": guides,
                "search_criteria": intent['extracted'],
                "search_date": intent['extracted'].get('date', ''),
                "search_location": intent['extracted'].get('location', ''),
                "guide_offset": 3  # Start at 3 so "more" shows guides 4-6
            }
        }
        
    async def _handle_more_guides(
        self,
        message: str,
        intent: Dict[str, Any],
        orchestrator: Any
    ) -> Dict[str, Any]:
        """Handle request for more guides"""
        
        print(f"🔄 TouristAgent: User wants more guides")
        print(f"📦 Current context: {self.conversation_context}")
        
        # Get previous search criteria
        search_criteria = self.conversation_context.get('search_criteria', {})
        
        if not search_criteria:
            return {
                "message": "Please tell me what location and interests you're looking for, and I'll find more guides for you!",
                "intent": intent,
                "reasoning": self.reasoning_steps
            }
        
        # Search again with same criteria but request more results
        current_offset = self.conversation_context.get('guide_offset', 3)
        print(f"📄 Current offset: {current_offset}, will search from offset {current_offset}")
        search_criteria['offset'] = current_offset
        
        guide_response = await self.delegate_to(
            agent_name="guide",
            message=json.dumps({
                "action": "search_guides",
                "criteria": search_criteria
            }),
            orchestrator=orchestrator
        )
        
        response_text = self._format_guide_results(guide_response)
        guides = guide_response.get('guides', [])
        
        # Increment offset for next "more" request
        next_offset = current_offset + 3
        print(f"✅ Returning {len(guides)} guides, next offset will be: {next_offset}")
        
        return {
            "message": response_text,
            "intent": intent,
            "guide_results": guide_response,
            "reasoning": self.reasoning_steps,
            "context": {
                "last_guide_search": guides,
                "search_criteria": search_criteria,
                "guide_offset": next_offset
            }
        }
    
    async def _handle_cultural_question(
        self,
        message: str,
        intent: Dict[str, Any],
        orchestrator: Any
    ) -> Dict[str, Any]:
        """Handle cultural question"""
        
        print(f"🏛️ TouristAgent: Detected cultural question")
        self._add_reasoning("Decision", "Delegating to CulturalAgent")
        
        # Delegate to CulturalAgent
        cultural_response = await self.delegate_to(
            agent_name="cultural",
            message=json.dumps({
                "action": "cultural_guidance",
                "user_question": message,
                "context": self.conversation_context
            }),
            orchestrator=orchestrator
        )
        
        # Format comprehensive cultural response with do's and don'ts
        formatted_message = self._format_cultural_response(cultural_response)
        
        return {
            "message": formatted_message,
            "intent": intent,
            "cultural_info": cultural_response,
            "reasoning": self.reasoning_steps
        }
    
    async def _handle_guide_registration(
        self,
        message: str,
        intent: Dict[str, Any],
        orchestrator: Any,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Handle guide registration request"""
        
        print(f"📝 TouristAgent: Detected guide registration request")
        self._add_reasoning("Decision", "Delegating to RegistrationAgent")
        
        # Clear any previous interaction types to prevent conflicts
        self.conversation_context.pop('last_interaction_type', None)
        self.conversation_context.pop('suggested_location', None)
        self.conversation_context.pop('suggested_interests', None)
        
        # Delegate to RegistrationAgent
        registration_response = await self.delegate_to(
            agent_name="registration",
            message=json.dumps({
                "action": "start_registration",
                "user_message": message
            }),
            orchestrator=orchestrator,
            context=context
        )
        
        # Merge registration context with conversation context
        registration_context = registration_response.get('context', {})
        self.conversation_context.update(registration_context)
        self.conversation_context['in_registration_flow'] = True
        
        # Convert any Decimal objects to float for JSON serialization
        def convert_decimals_to_float(obj):
            """Recursively convert Decimals to float for JSON serialization"""
            from decimal import Decimal
            if isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_decimals_to_float(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_decimals_to_float(v) for v in obj]
            return obj
        
        response = {
            "message": registration_response.get('message', 'Let me help you register as a guide!'),
            "intent": intent,
            "registration_info": convert_decimals_to_float(registration_response),
            "reasoning": self.reasoning_steps,
            "context": self.conversation_context
        }
        
        return convert_decimals_to_float(response)
        
    async def _handle_booking(
        self,
        message: str,
        intent: Dict[str, Any],
        orchestrator: Any
    ) -> Dict[str, Any]:
        """Handle booking confirmation"""
        
        print(f"📅 TouristAgent: Detected booking request")
        
        # Check if this is a false positive (user just said "yes" without context)
        message_lower = message.strip().lower()
        has_booking_context = (
            self.conversation_context.get('last_guide_search') or 
            self.conversation_context.get('suggested_location') or
            self.conversation_context.get('last_interaction_type') == 'image_analysis'
        )
        
        if message_lower in ['yes', 'no', 'ok', 'sure'] and not has_booking_context:
            print("⚠️ False booking detection - no guide context, treating as general")
            return await self._handle_general_conversation(message, self.conversation_context)
        
        self._add_reasoning("Decision", "Processing booking request")
        
        extracted = intent.get('extracted', {})
        guide_id = extracted.get('guide_id', '')
        guide_name = extracted.get('guide_name', '')
        
        # Check if user is selecting from previous guide search results
        last_guides = self.conversation_context.get('last_guide_search', [])
        
        if last_guides and not guide_id:
            # Ask AI to extract guide selection number from message
            selection_prompt = f"""The user previously saw {len(last_guides)} guide options.
            
User message: "{message}"

Is the user selecting one of these guides? If yes, which number (1-{len(last_guides)})?

Respond with ONLY a JSON object:
{{
    "is_selecting_guide": true/false,
    "guide_number": 1-{len(last_guides)} or null,
    "reasoning": "brief explanation"
}}"""
            
            selection_response = self.call_bedrock(selection_prompt, max_tokens=200)
            
            try:
                json_start = selection_response.find('{')
                json_end = selection_response.rfind('}') + 1
                selection_data = json.loads(selection_response[json_start:json_end])
                
                if selection_data.get('is_selecting_guide') and selection_data.get('guide_number'):
                    guide_num = int(selection_data['guide_number'])
                    
                    if 0 < guide_num <= len(last_guides):
                        selected_guide = last_guides[guide_num - 1]
                        guide_id = selected_guide.get('guideId', '')
                        guide_name = selected_guide.get('name', '')
                        print(f"✅ AI selected guide #{guide_num}: {guide_name} ({guide_id})")
                        
                        # Get the full search criteria from context
                        search_criteria = self.conversation_context.get('search_criteria', {})
                        if not extracted.get('date') and search_criteria.get('date'):
                            extracted['date'] = search_criteria['date']
                        if not extracted.get('location') and search_criteria.get('location'):
                            extracted['location'] = search_criteria['location']
                        if not extracted.get('interests') and search_criteria.get('interests'):
                            extracted['interests'] = search_criteria['interests']
            except Exception as e:
                print(f"⚠️  Could not parse guide selection: {e}")
        
        # If no guide_id but have guide_name, search for the guide
        if not guide_id and guide_name:
            print(f"🔍 Searching for guide: {guide_name}")
            # Search for guide by name
            import boto3
            from decimal import Decimal
            
            def convert_decimals(obj):
                if isinstance(obj, Decimal):
                    return float(obj)
                elif isinstance(obj, dict):
                    return {k: convert_decimals(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_decimals(v) for v in obj]
                return obj
            
            try:
                dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
                table = dynamodb.Table('thailand-guide-bot-dev-guides')
                response = table.scan()
                guides = response.get('Items', [])
                
                # Find guide by name (case-insensitive)
                for guide in guides:
                    if guide_name.lower() in guide.get('name', '').lower():
                        guide_id = guide.get('guideId', '')
                        guide_name = guide.get('name', guide_name)  # Use full name
                        print(f"✅ Found guide: {guide_name} ({guide_id})")
                        
                        # Get the full search criteria from context
                        search_criteria = self.conversation_context.get('search_criteria', {})
                        if not extracted.get('date') and search_criteria.get('date'):
                            extracted['date'] = search_criteria['date']
                        if not extracted.get('location') and search_criteria.get('location'):
                            extracted['location'] = search_criteria['location']
                        if not extracted.get('interests') and search_criteria.get('interests'):
                            extracted['interests'] = search_criteria['interests']
                        break
            except Exception as e:
                print(f"❌ Error searching for guide: {str(e)}")
        
        if not guide_id:
            return {
                "message": f"I couldn't find a guide named '{guide_name}'. Could you please select from the guides shown above or search for guides first.",
                "intent": intent,
                "reasoning": self.reasoning_steps
            }
        
        # Final fallback: Get search criteria from context if not in extracted
        if not extracted.get('date') or not extracted.get('location'):
            search_criteria = self.conversation_context.get('search_criteria', {})
            if not extracted.get('date') and search_criteria.get('date'):
                extracted['date'] = search_criteria['date']
                print(f"📅 Using date from context: {extracted['date']}")
            if not extracted.get('location') and search_criteria.get('location'):
                extracted['location'] = search_criteria['location']
                print(f"📍 Using location from context: {extracted['location']}")
            if not extracted.get('interests') and search_criteria.get('interests'):
                extracted['interests'] = search_criteria['interests']
                print(f"🎯 Using interests from context: {extracted['interests']}")
        
        # Check if we have customer name - if not, ask for it
        customer_name = extracted.get('customer_name', '')
        if not customer_name:
            print("👤 No customer name provided - asking for name")
            return {
                "message": f"Great choice! I'll help you book {guide_name}. What's your name?",
                "intent": intent,
                "reasoning": self.reasoning_steps,
                "context": {
                    "awaiting_customer_name": True,
                    "selected_guide_id": guide_id,
                    "selected_guide_name": guide_name,
                    "booking_details": extracted
                }
            }
        
        # Have customer name - show confirmation summary
        print(f"✅ Have customer name: {customer_name} - showing confirmation")
        confirmation_message = f"""📋 *Booking Summary:*

👤 Name: {customer_name}
🗓️ Date: {extracted.get('date', 'requested date')}
📍 Location: {extracted.get('location', 'requested location')}
👨‍🏫 Guide: {guide_name}

Please confirm to proceed with booking. Reply 'yes' to confirm or 'no' to cancel."""
        
        # Update context BEFORE returning
        self.conversation_context['awaiting_booking_confirmation'] = True
        self.conversation_context['selected_guide_id'] = guide_id
        self.conversation_context['selected_guide_name'] = guide_name
        self.conversation_context['customer_name'] = customer_name
        self.conversation_context['booking_details'] = extracted
        
        return {
            "message": confirmation_message,
            "intent": {"type": "booking_confirmation"},
            "reasoning": self.reasoning_steps,
            "context": self.conversation_context
        }
        
        # This code should never be reached - confirmation is required above
        print("⚠️ WARNING: Reached booking code without confirmation - this shouldn't happen")
        return {
            "message": "Please confirm your booking first.",
            "intent": intent,
            "reasoning": self.reasoning_steps
        }
    
    async def _execute_confirmed_booking(
        self,
        guide_id: str,
        guide_name: str,
        customer_name: str,
        booking_details: Dict[str, Any],
        orchestrator: Any
    ) -> Dict[str, Any]:
        """Execute the booking after user confirmation"""
        
        print(f"📝 Executing confirmed booking for {customer_name} with {guide_name}")
        
        # Prepare booking details
        prepared_details = {
            "date": booking_details.get('date', ''),
            "time": booking_details.get('time', 'morning'),
            "number_of_people": booking_details.get('number_of_people', 2),
            "tour_type": booking_details.get('tour_type', 'general'),
            "special_requests": booking_details.get('other', {})
        }
        
        # Delegate to BookingAgent
        booking_response = await self.delegate_to(
            agent_name="booking",
            message=json.dumps({
                "action": "create_booking",
                "guide_id": guide_id,
                "booking_details": prepared_details,
                "customer_name": customer_name,
                "user_id": booking_details.get('user_id', 'unknown')
            }),
            orchestrator=orchestrator
        )
        
        # Format booking confirmation message
        booking = booking_response.get('booking', {})
        
        # Include confirmation number if available
        confirmation_header = "✅ Booking Confirmed!"
        if booking.get('confirmation_number'):
            confirmation_header = f"✅ Booking Confirmed!\n📋 Booking ID: {booking.get('confirmation_number')}"
        
        confirmation_msg = f"""{confirmation_header}

{booking.get('booking_details', 'Your tour has been confirmed.')}

{booking.get('pricing_info', '')}

Next Steps:
"""
        for step in booking.get('next_steps', []):
            confirmation_msg += f"• {step}\n"
        
        if booking.get('contact_info'):
            confirmation_msg += f"\n📞 {booking.get('contact_info')}"
        
        # Add message about starting new booking
        confirmation_msg += f"\n\n💬 Ready for another booking? Just send me your next request!"
        
        # Clear context after successful booking
        print("✅ Booking complete - resetting context for next interaction")
        self.conversation_context = {}  # Complete reset
        
        # Also clear memory if available
        if hasattr(self, 'memory') and self.memory:
            try:
                await self.memory.clear_working_memory(booking_details.get('user_id', 'unknown'))
            except:
                pass
        
        return {
            "message": confirmation_msg,
            "intent": {"type": "booking_confirmation"},
            "booking_result": booking,
            "reasoning": self.reasoning_steps,
            "context": {}  # Clear context
        }
        
    async def _handle_general_conversation(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle general conversation using working Lambda logic"""
        
        print(f"💬 TouristAgent: General conversation")
        
        # Check if this is first interaction (no context) - CHECK THIS FIRST!
        if not self.conversation_context:
            print("🆕 First interaction - generating welcome message with AI")
            
            welcome_prompt = """Generate a friendly welcome message for Global Guide Bot with these 3 options:
1. Find a local guide
2. Answer cultural questions
3. Register as a guide

Format:
🌍 Welcome to Global Guide Bot!

I can help you with:

1️⃣ Find a local guide
2️⃣ Answer cultural questions  
3️⃣ Register as a guide

Keep it exactly in this format."""
            
            welcome_message = self.call_bedrock(welcome_prompt, max_tokens=200).strip()
            
            return {
                "message": welcome_message,
                "intent": {"type": "welcome"},
                "reasoning": self.reasoning_steps
            }
        
        message_lower = message.lower()
        
        # CRITICAL: Check conversation context FIRST before AI analysis
        # This prevents AI from overriding booking confirmation flows
        if (self.conversation_context.get('awaiting_booking_confirmation') or 
            self.conversation_context.get('awaiting_customer_name') or 
            self.conversation_context.get('awaiting_location')):
            # Skip AI analysis - handle context-specific flows first
            print(f"🔄 Context-driven flow detected: {list(self.conversation_context.keys())}")
            needs_cultural_intelligence = False
            needs_guide_matching = False
            needs_booking = False
            guide_analysis = {}
        else:
            # Let AI analyze the message for intent
            # No more keyword matching - AI handles all intent detection including "1", "2", "3"
            # Check if cultural intelligence is needed using AI analysis
            cultural_analysis = self._detect_cultural_needs_with_ai(message, self.conversation_context)
            needs_cultural_intelligence = cultural_analysis.get('needs_cultural_intelligence', False)
            
            # Check if guide matching is needed using AI analysis
            guide_analysis = self._detect_guide_intent_with_ai(message, self.conversation_context)
            needs_guide_matching = guide_analysis.get('needs_guide_matching', False)
            needs_booking = guide_analysis.get('needs_booking', False)
        
        # Handle booking confirmation first (before other context checks)
        # BUT only if we actually have previous guide context
        # AND the message doesn't look like a new guide search request
        message_has_location_date = any(city in message.lower() for city in ['bangkok', 'chiang mai', 'phuket', 'pattaya']) and any(date_indicator in message.lower() for date_indicator in ['2025', '2024', 'december', 'january', 'tomorrow', 'next week'])
        
        if (needs_booking and 
            guide_analysis.get('intent') == 'BOOKING_CONFIRMATION' and
            self.conversation_context.get('last_guide_search') and
            not message_has_location_date):  # Don't treat as booking if it has location+date
            print(f"🎯 AI detected booking confirmation: {guide_analysis}")
            # Create a proper booking intent and process it
            booking_intent_formatted = {
                'type': 'booking_confirmation',
                'extracted': {
                    'guide_name': self.conversation_context.get('suggested_guide_name', ''),
                    'date': self.conversation_context.get('search_date', ''),
                    'location': self.conversation_context.get('suggested_location', ''),
                    'customer_name': ''  # Always empty to force asking for name
                }
            }
            return await self._handle_booking(message, booking_intent_formatted, orchestrator)
        
        # Only proceed with AI analysis if not in a context-driven flow
        if not (self.conversation_context.get('awaiting_booking_confirmation') or 
                self.conversation_context.get('awaiting_customer_name') or 
                self.conversation_context.get('awaiting_location')):
            
            # Smart group detection (EXACT logic from working Lambda)
            group_indicators = {
                'couple': ['wife', 'husband', 'partner', 'girlfriend', 'boyfriend', 'romantic', 'anniversary', 'honeymoon'],
                'family': ['kids', 'children', 'family', 'son', 'daughter', 'parents'],
                'friends': ['friends', 'group of friends', 'buddies', 'mates'],
                'solo': ['solo', 'alone', 'myself', 'just me', 'by myself']
            }
            
            detected_group = None
            for group_type, indicators in group_indicators.items():
                if any(indicator in message_lower for indicator in indicators):
                    detected_group = group_type
                    break
            
            # Check if we have sufficient preferences for guide matching
            has_sufficient_preferences = (
                detected_group or
                'romantic' in message_lower or
                'sunset' in message_lower or
                'beach' in message_lower or
                'food' in message_lower or
                'bangkok' in message_lower or
                'phuket' in message_lower or
                'pattaya' in message_lower or
                'chiang mai' in message_lower
            )
            
            # Check if user is selecting a guide by name from previous results
            if self.conversation_context.get('last_guide_search'):
                # Use AI to detect if this is a guide booking attempt
                booking_intent = self._detect_booking_intent_with_ai(message, self.conversation_context)
                if booking_intent.get('type') == 'booking_confirmation':
                    print(f"🎯 AI detected guide booking intent: {booking_intent}")
                    # Create a proper booking intent and process it
                    booking_intent_formatted = {
                        'type': 'booking_confirmation',
                        'extracted': {
                            'guide_name': booking_intent.get('guide_name', ''),
                            'date': self.conversation_context.get('search_date', ''),
                            'location': self.conversation_context.get('search_location', ''),
                            'customer_name': ''  # Always empty to force asking for name
                        }
                    }
                    return await self._handle_booking(message, booking_intent_formatted, orchestrator)
            
            # PRIORITY 1: If cultural intelligence is needed, delegate to Cultural Agent (regardless of guide matching)
            if needs_cultural_intelligence:
                # Create enhanced message with AI analysis for cultural agent
                cultural_message = json.dumps({
                    "action": "cultural_guidance",
                    "user_question": message,
                    "context": self.conversation_context
                })
                
                return await self._handle_cultural_question(message, {"type": "cultural_question"}, orchestrator)
            
            # PRIORITY 2: If guide matching is needed OR we have sufficient preferences, delegate to Guide Agent
            if needs_guide_matching or has_sufficient_preferences:
                return {
                    "message": "I'll help you find the perfect guide! Let me search for guides that match your interests.",
                    "intent": {"type": "guide_search"},
                    "reasoning": self.reasoning_steps,
                    "delegate_to": "guide"
                }
            
            # Default friendly response - use AI to generate helpful response
            response_prompt = f"""User said: "{message}"

Generate a helpful response that guides them to use one of these options:
1. Find a local guide
2. Answer cultural questions
3. Register as a guide

Keep it friendly and brief."""
            
            response_text = self.call_bedrock(response_prompt, max_tokens=150).strip()
            
            return {
                "message": response_text,
                "intent": {"type": "general"},
                "reasoning": self.reasoning_steps
            }
        
    def _format_guide_results(self, guide_response: Dict[str, Any]) -> str:
        """Format guide results for user"""
        
        if not guide_response.get('guides'):
            return "I couldn't find any guides matching your criteria. Could you try different dates or locations?"
            
        guides = guide_response['guides'][:3]  # Top 3
        
        response = f"🌟 I found {len(guides)} great guide(s) for you!\n\n"
        
        for i, guide in enumerate(guides, 1):
            # Extract fields (handle different formats)
            specialties = guide.get('specialties', [])
            if isinstance(specialties, list) and specialties:
                specialty_text = ', '.join(specialties[:3])  # Show top 3 specialties
            else:
                specialty_text = 'General tours'
            
            rating = guide.get('rating', 4.5)
            experience = guide.get('experience', guide.get('experience_years', 5))
            price = guide.get('price_per_day', guide.get('price', 100))
            location = guide.get('location', 'Thailand')
            
            # Get review count
            review_count = guide.get('total_reviews', guide.get('review_count', guide.get('reviews', 0)))
            
            response += f"{i}. **{guide['name']}**\n"
            response += f"   📍 Location: {location}\n"
            response += f"   🎯 Specialties: {specialty_text}\n"
            response += f"   ⭐ {rating}/5 ({review_count} reviews) | {experience} years experience\n"
            response += f"   💰 ${price}/day (full day tour)\n"
            
            # Add video if available
            if guide.get('video_url'):
                response += f"   🎥 Video: {guide['video_url']}\n"
            
            # Add availability status
            if guide.get('available'):
                response += f"   ✅ Available on your dates\n"
            elif guide.get('availability_status'):
                response += f"   📅 {guide['availability_status']}\n"
            
            response += "\n"
            
        response += "💬 Reply with guide name to book (e.g., 'Itthipol')"
        
        return response
        
    def _extract_criteria_from_message(self, message: str) -> Dict[str, Any]:
        """Extract search criteria from message (like working Lambda)"""
        
        message_lower = message.lower()
        criteria = {}
        
        # Extract location
        locations = ['bangkok', 'phuket', 'pattaya', 'chiang mai', 'krabi', 'koh samui', 'ayutthaya']
        for location in locations:
            if location in message_lower:
                criteria['location'] = location.title()
                break
        
        # Extract interests using AI instead of keyword matching
        interests = self._extract_interests_with_ai(message, self.conversation_context)
        if interests:
            criteria['interests'] = interests
        
        # Extract group info
        if any(word in message_lower for word in ['couple', 'romantic', 'wife', 'husband', 'partner']):
            criteria['number_of_people'] = 2
            criteria['tour_type'] = 'romantic tour'
        elif any(word in message_lower for word in ['family', 'kids', 'children']):
            criteria['number_of_people'] = 4
            criteria['tour_type'] = 'family tour'
        elif any(word in message_lower for word in ['friends', 'group']):
            criteria['number_of_people'] = 4
            criteria['tour_type'] = 'group tour'
        else:
            criteria['number_of_people'] = 1
            criteria['tour_type'] = 'general tour'
        
        return criteria
    
    def _extract_interests_with_ai(self, message: str, context: Dict[str, Any] = None) -> List[str]:
        """
        Extract tourism interests using AI analysis instead of keyword matching
        Handles negation, context, and global tourism categories
        """
        # Build context-aware prompt
        context_info = ""
        if context and context.get('suggested_location'):
            context_info = f"Location context: {context['suggested_location']}\n"
        if context and context.get('conversation_history'):
            context_info += f"Previous conversation: {context.get('conversation_history', [])[-2:]}\n"
        
        interests_prompt = f"""You are an expert tourism analyst. Extract tourism interests from the user's message.

{context_info}User message: "{message}"

TOURISM CATEGORIES (Global):
• temple tours (religious sites, spiritual experiences)
• food tours (culinary experiences, cooking classes, street food)
• beach tours (coastal activities, water sports, islands)
• romantic tours (couples activities, sunset experiences, intimate settings)
• adventure tours (hiking, climbing, extreme sports, outdoor activities)
• cultural tours (museums, art, local traditions, festivals)
• shopping tours (markets, malls, local crafts, souvenirs)
• nightlife tours (bars, clubs, entertainment districts)
• wellness tours (spas, yoga, meditation, health retreats)
• photography tours (scenic spots, photo workshops, Instagram locations)
• nature tours (parks, wildlife, gardens, eco-tourism)
• historical tours (monuments, ancient sites, heritage locations)

IMPORTANT RULES:
1. Handle negation: "I don't like X" means EXCLUDE X
2. Consider context: "The temple was closed" is NOT interest in temples
3. Infer from activities: "sunset dinner" suggests romantic tours
4. Multiple interests allowed: "temples and food" = both categories
5. If unclear or no interests mentioned, return empty list
6. Confidence must be >0.7 to include an interest

Respond with ONLY valid JSON:
{{
  "interests": ["temple tours", "food tours"],
  "confidence_scores": {{"temple tours": 0.9, "food tours": 0.8}},
  "reasoning": "User mentioned visiting temples and trying local cuisine",
  "excluded_interests": ["beach tours"],
  "exclusion_reason": "User said they don't like beaches"
}}"""

        try:
            response = self.call_bedrock(interests_prompt, max_tokens=500)
            
            # Parse JSON response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                analysis = json.loads(response[json_start:json_end])
                
                # Validate and filter by confidence
                validated_interests = []
                for interest in analysis.get('interests', []):
                    confidence = analysis.get('confidence_scores', {}).get(interest, 0)
                    if confidence >= 0.7:
                        validated_interests.append(interest)
                
                # Log reasoning for debugging
                if analysis.get('reasoning'):
                    self._add_reasoning("AI Interest Extraction", {
                        "extracted_interests": validated_interests,
                        "reasoning": analysis['reasoning'],
                        "confidence_scores": analysis.get('confidence_scores', {}),
                        "excluded": analysis.get('excluded_interests', [])
                    })
                
                print(f"🤖 AI extracted interests: {validated_interests}")
                if analysis.get('reasoning'):
                    print(f"   Reasoning: {analysis['reasoning']}")
                
                return validated_interests
                
        except Exception as e:
            print(f"❌ AI interest extraction failed: {str(e)}")
            # Fallback to empty list rather than broken keyword matching
            return []
        
        return []
    
    def _detect_cultural_needs_with_ai(self, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Detect if user needs cultural guidance using AI analysis instead of keyword matching
        Works globally for any culture/country, not just Thailand
        """
        # Extract location context for cultural analysis
        location_context = ""
        if context and context.get('suggested_location'):
            location_context = f"Location: {context['suggested_location']}\n"
        elif context and context.get('search_criteria', {}).get('location'):
            location_context = f"Location: {context['search_criteria']['location']}\n"
        
        # Build conversation context
        conversation_context = ""
        if context and context.get('conversation_history'):
            recent_messages = context.get('conversation_history', [])[-3:]
            conversation_context = f"Recent conversation: {recent_messages}\n"
        
        cultural_prompt = f"""You are a global cultural intelligence expert. Analyze if this user needs cultural guidance.

{location_context}{conversation_context}User message: "{message}"

CULTURAL GUIDANCE CATEGORIES (Global):
• Religious etiquette (temples, mosques, churches, shrines, sacred sites)
• Social customs (greetings, gestures, personal space, eye contact)
• Dining etiquette (table manners, tipping, food customs, dietary restrictions)
• Dress codes (modest clothing, religious sites, business attire, cultural appropriateness)
• Business etiquette (meetings, negotiations, gift-giving, hierarchy)
• Festival/ceremony participation (proper behavior, participation rules, respect protocols)
• Language/communication (polite phrases, cultural sensitivity, taboo topics)
• Shopping customs (bargaining, payment methods, local practices)
• Transportation etiquette (public transport, taxi customs, traffic rules)
• Photography rules (where not to take photos, permission requirements)

URGENCY LEVELS:
• CRITICAL: Could cause serious offense or legal issues (religious disrespect, major taboos)
• HIGH: Important for positive experience (proper greetings, basic etiquette)
• MEDIUM: Helpful but not essential (local customs, minor etiquette)
• LOW: Nice to know information (cultural background, historical context)

DETECTION RULES:
1. Direct questions: "What should I wear to temples?" = HIGH urgency
2. Implicit needs: "Meeting locals tomorrow" = MEDIUM urgency cultural guidance needed
3. Potential mistakes: "Can I wear shorts everywhere?" = HIGH urgency
4. Context clues: Planning temple visits = religious etiquette needed
5. Negation handling: "I don't care about culture" = NO cultural guidance needed
6. Past tense: "The temple was beautiful" = NO guidance needed (already happened)
7. Greeting questions: "How do I greet", "How to say hello", "What is wai" = HIGH urgency
8. Behavior questions: "How do I behave", "What's appropriate", "Is it okay to" = HIGH urgency

Respond with ONLY valid JSON:
{{
  "needs_cultural_guidance": true/false,
  "urgency": "critical/high/medium/low",
  "cultural_topics": ["religious etiquette", "dress codes"],
  "reasoning": "User asking about temple visits requires dress code and behavior guidance",
  "suggested_guidance": "Provide temple etiquette and modest dress requirements",
  "confidence": 0.9
}}"""

        try:
            response = self.call_bedrock(cultural_prompt, max_tokens=400)
            
            # Parse JSON response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                analysis = json.loads(response[json_start:json_end])
                
                # Validate confidence threshold
                confidence = analysis.get('confidence', 0)
                needs_guidance = analysis.get('needs_cultural_guidance', False)
                
                if confidence >= 0.7 and needs_guidance:
                    # Log reasoning for debugging
                    self._add_reasoning("AI Cultural Detection", {
                        "needs_guidance": needs_guidance,
                        "urgency": analysis.get('urgency', 'medium'),
                        "topics": analysis.get('cultural_topics', []),
                        "reasoning": analysis.get('reasoning', ''),
                        "confidence": confidence
                    })
                    
                    print(f"🏛️ AI detected cultural guidance needed: {analysis.get('cultural_topics', [])}")
                    if analysis.get('reasoning'):
                        print(f"   Reasoning: {analysis['reasoning']}")
                        print(f"   Urgency: {analysis.get('urgency', 'medium').upper()}")
                    
                    return {
                        "needs_cultural_intelligence": True,
                        "urgency": analysis.get('urgency', 'medium'),
                        "topics": analysis.get('cultural_topics', []),
                        "guidance": analysis.get('suggested_guidance', ''),
                        "reasoning": analysis.get('reasoning', '')
                    }
                    
        except Exception as e:
            print(f"❌ AI cultural detection failed: {str(e)}")
            # Fallback to no cultural guidance rather than broken keyword matching
            return {"needs_cultural_intelligence": False}
        
        return {"needs_cultural_intelligence": False}
    
    def _detect_guide_intent_with_ai(self, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Detect guide-related intent using AI analysis instead of keyword matching
        Handles context, conversation history, and nuanced intent classification
        """
        # Build conversation context
        conversation_context = ""
        if context and context.get('conversation_history'):
            recent_messages = context.get('conversation_history', [])[-3:]
            conversation_context = f"Recent conversation: {recent_messages}\n"
        
        # Include previous guide interactions
        guide_context = ""
        if context and context.get('last_guide_search'):
            guide_context = f"Previous guide search results available: {len(context.get('last_guide_search', []))} guides\n"
        if context and context.get('selected_guide_id'):
            guide_context += f"Currently selected guide: {context.get('selected_guide_name', 'Unknown')}\n"
        
        # Include location context
        location_context = ""
        if context and context.get('suggested_location'):
            location_context = f"Location context: {context['suggested_location']}\n"
        elif context and context.get('search_criteria', {}).get('location'):
            location_context = f"Location: {context['search_criteria']['location']}\n"
        
        intent_prompt = f"""You are an expert travel intent classifier. Analyze the user's message to determine their guide-related intent.

{conversation_context}{guide_context}{location_context}User message: "{message}"

GUIDE-RELATED INTENT TYPES:
1. GUIDE_SEARCH: User wants to find/search for guides (HIGHEST PRIORITY)
   • "Find me a guide", "I need a local guide", "Show me tour guides"
   • "Looking for someone to show me around", "Need a local expert"
   • "I would like to book a guide to [location]" - initial request with location/date
   • "book a guide to Bangkok", "need guide for Chiang Mai", "guide for temple tour"
   • CRITICAL: Any message with location + date + activities = GUIDE_SEARCH
   • CRITICAL: If message contains location name (Bangkok, Chiang Mai, etc.) = GUIDE_SEARCH

2. GUIDE_INFO: User wants information about guides/guiding
   • "What do guides do?", "How much do guides cost?", "Guide requirements?"

3. GUIDE_BOOKING: User wants to book a specific guide
   • "Book guide #2", "I want Somchai", "Reserve the temple guide"

4. BOOKING_CONFIRMATION: User confirms/agrees to booking
   • "Yes", "Yes please", "Sure", "Okay", "I agree", "Let's do it"
   • "Book it", "Confirm", "Go ahead", "That sounds good"
   • CRITICAL: Only when previous message offered booking/guide services
   • NOT when user is making initial request with location/date/activities

5. GUIDE_COMPLAINT: User has issues with guides
   • "My guide was terrible", "The guide didn't show up", "Bad experience"

6. MORE_GUIDES: User wants additional guide options
   • "Show me more", "Any other guides?", "Different options?"

7. NOT_GUIDE_RELATED: Message not about tourism guides
   • "Guide me to the bathroom", "User guide for app", "Guide dog needed"
   • "The guide book says...", "TV guide", "Study guide"

CONTEXT ANALYSIS RULES:
1. Consider conversation history: If just showed guides, "more" likely means MORE_GUIDES
2. Past tense complaints: "guide was bad" = GUIDE_COMPLAINT, not search
3. Specific guide references: "guide #2" or names = GUIDE_BOOKING
4. Non-tourism context: bathroom, apps, books = NOT_GUIDE_RELATED
5. Question format: "What do guides..." = GUIDE_INFO
6. Action format: "Find me..." = GUIDE_SEARCH
7. BOOKING CONFIRMATION: If previous message offered booking and user says "yes/okay/sure" = BOOKING_CONFIRMATION
8. PRIORITY RULE: If message contains Thai city names (Bangkok, Chiang Mai, Phuket, Pattaya) + wants guide = GUIDE_SEARCH

CRITERIA EXTRACTION:
If intent is GUIDE_SEARCH, also extract search criteria:
• Location: city, area, region mentioned
• Interests: activities, attractions, experiences wanted
• Budget: price range, cost preferences
• Group size: solo, couple, family, group
• Date/time: when they want the guide
• Special requirements: language, expertise, accessibility

Respond with ONLY valid JSON:
{{
  "intent": "GUIDE_SEARCH",
  "confidence": 0.95,
  "reasoning": "User explicitly asking to find local guides for temple visits",
  "needs_guide_matching": true,
  "extracted_criteria": {{
    "location": "Bangkok",
    "interests": ["temple tours"],
    "budget": "under $100",
    "group_size": 2,
    "special_requirements": ["English speaking"]
  }},
  "urgency": "high"
}}"""

        try:
            response = self.call_bedrock(intent_prompt, max_tokens=500)
            
            # Parse JSON response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                analysis = json.loads(response[json_start:json_end])
                
                # Validate confidence threshold
                confidence = analysis.get('confidence', 0)
                intent = analysis.get('intent', 'NOT_GUIDE_RELATED')
                
                if confidence >= 0.7:
                    # Log reasoning for debugging
                    self._add_reasoning("AI Guide Intent Detection", {
                        "intent": intent,
                        "confidence": confidence,
                        "reasoning": analysis.get('reasoning', ''),
                        "extracted_criteria": analysis.get('extracted_criteria', {}),
                        "urgency": analysis.get('urgency', 'medium')
                    })
                    
                    # Determine if guide matching is needed
                    guide_search_intents = ['GUIDE_SEARCH', 'MORE_GUIDES']
                    booking_intents = ['GUIDE_BOOKING', 'BOOKING_CONFIRMATION']
                    needs_matching = intent in guide_search_intents
                    needs_booking = intent in booking_intents
                    
                    print(f"🎯 AI detected guide intent: {intent} (confidence: {confidence:.2f})")
                    if analysis.get('reasoning'):
                        print(f"   Reasoning: {analysis['reasoning']}")
                    
                    return {
                        "needs_guide_matching": needs_matching,
                        "needs_booking": needs_booking,
                        "intent": intent,
                        "confidence": confidence,
                        "reasoning": analysis.get('reasoning', ''),
                        "extracted_criteria": analysis.get('extracted_criteria', {}),
                        "urgency": analysis.get('urgency', 'medium')
                    }
                    
        except Exception as e:
            print(f"❌ AI guide intent detection failed: {str(e)}")
            # Fallback to no guide matching rather than broken keyword matching
            return {"needs_guide_matching": False, "intent": "UNKNOWN"}
        
        return {"needs_guide_matching": False, "intent": "NOT_GUIDE_RELATED"}
        
    def _detect_booking_intent_with_ai(self, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Detect if user is trying to book a specific guide"""
        
        # Get guide names from last search
        guide_names = []
        if context and context.get('last_guide_search'):
            guide_names = [guide.get('name', '') for guide in context['last_guide_search']]
        
        booking_prompt = f"""Analyze if the user is trying to book a specific guide.

User message: "{message}"

Available guides from previous search: {guide_names}

Is the user trying to book a guide? Look for:
1. Guide names mentioned (e.g., "Wichai", "Kanya", "Somchai")
2. Booking phrases (e.g., "I want", "book", "yes", "ok", "confirm")
3. Guide numbers (e.g., "guide 1", "#2", "first one")

Respond with ONLY valid JSON:
{{
  "type": "booking_confirmation",
  "confidence": 0.95,
  "guide_name": "Wichai Wira",
  "reasoning": "User mentioned guide name from available options"
}}

OR if not booking:
{{
  "type": "not_booking",
  "confidence": 0.90,
  "reasoning": "User asking for more information, not booking"
}}"""

        try:
            response = self.call_bedrock(booking_prompt, max_tokens=300)
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                analysis = json.loads(response[json_start:json_end])
                print(f"🎯 Booking intent analysis: {analysis}")
                return analysis
        except Exception as e:
            print(f"❌ Booking intent detection failed: {str(e)}")
        
        return {"type": "not_booking", "confidence": 0.0}
        
    def _format_cultural_response(self, cultural_response: Dict[str, Any]) -> str:
        """Format comprehensive cultural response with do's and don'ts"""
        try:
            message = "🏛️ *Thai Cultural Guidance*\n\n"
            
            # Main guidance
            if cultural_response.get('guidance'):
                message += f"{cultural_response['guidance']}\n\n"
            
            # Cultural context
            if cultural_response.get('cultural_context'):
                message += f"📚 *Cultural Context:*\n{cultural_response['cultural_context']}\n\n"
            
            # Do's (Recommendations)
            if cultural_response.get('recommendations'):
                recommendations = cultural_response['recommendations']
                if isinstance(recommendations, list) and recommendations:
                    message += "✅ *Do's:*\n"
                    for rec in recommendations:
                        message += f"• {rec}\n"
                    message += "\n"
            
            # Don'ts (Sensitivity Notes)
            if cultural_response.get('sensitivity_notes'):
                sensitivity_notes = cultural_response['sensitivity_notes']
                if isinstance(sensitivity_notes, list) and sensitivity_notes:
                    message += "❌ *Don'ts:*\n"
                    for note in sensitivity_notes:
                        message += f"• {note}\n"
                    message += "\n"
            
            # Regional notes
            if cultural_response.get('regional_notes'):
                message += f"📍 *Regional Notes:*\n{cultural_response['regional_notes']}\n\n"
            
            # Encouraging closing
            message += "🙏 Following these guidelines will help you show respect for Thai culture and have a more authentic experience!"
            
            return message
            
        except Exception as e:
            print(f"❌ Error formatting cultural response: {str(e)}")
            # Fallback to basic guidance
            return cultural_response.get('guidance', 'I can help you with Thai cultural guidance!')
    
    def _add_reasoning(self, step: str, details: Any):
        """Add reasoning step"""
        self.reasoning_steps.append({
            "agent": "TouristAgent",
            "step": step,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    async def handle_agent_message(self, from_agent: str, message: str) -> Dict[str, Any]:
        """Handle message from another agent"""
        # TouristAgent typically doesn't receive messages from other agents
        return {"status": "acknowledged"}
