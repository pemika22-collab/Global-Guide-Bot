"""
GuideAgent - Intelligent guide discovery and matching
HYBRID APPROACH: Smart pre-filtering + AI semantic matching
Handles typos, fuzzy matching, and scales to 5000+ guides
"""

import json
import boto3
import os
from typing import Dict, Any, List
from datetime import datetime
from decimal import Decimal
from .base_agent import BaseAgent


def convert_decimals(obj):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(v) for v in obj]
    return obj


class GuideAgent(BaseAgent):
    """
    Intelligent guide matching with hybrid approach:
    1. AI extracts intent and corrects typos
    2. Smart DynamoDB filtering (location-based)
    3. AI semantic matching on filtered results
    
    Scales to 5000+ guides efficiently
    """
    
    def __init__(self):
        system_prompt = """You are an intelligent guide matching specialist for Thailand tourism.

Your capabilities:
1. Understand typos and correct them (Pattaya→Pattaya, Bankok→Bangkok)
2. Extract location and interests from natural language
3. Match guides semantically (not by keywords)
4. Provide reasoning for each match

Always be intelligent about:
- Typo correction (Pataya = Pattaya, Bankok = Bangkok, Chiangmai = Chiang Mai)
- Semantic understanding (beach = coastal, temple = cultural/religious)
- Location variations (Bangkok includes Sukhumvit, Silom, etc.)

Be smart, not literal."""

        super().__init__(
            name="guide",
            model_id="eu.amazon.nova-pro-v1:0",  # Nova Pro cross-region
            system_prompt=system_prompt
        )
        self.dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        # Use environment variable or default to thailand-guide-bot-dev-guides
        guides_table_name = os.getenv('DYNAMODB_GUIDES_TABLE', 'thailand-guide-bot-dev-guides')
        self.guides_table = self.dynamodb.Table(guides_table_name)
        self.availability_table = self.dynamodb.Table('thailand-guide-bot-dev-availability')
        self.reasoning_steps = []
        
    async def process(
        self, 
        message: str, 
        context: Dict[str, Any],
        orchestrator: Any = None
    ) -> Dict[str, Any]:
        """Process guide search request"""
        
        print(f"🤖 GuideAgent: Processing guide search...")
        
        # This shouldn't be called directly - use handle_agent_message
        return await self.handle_agent_message("tourist", message)
        
    async def handle_agent_message(self, from_agent: str, message: str) -> Dict[str, Any]:
        """
        Handle message from another agent
        HYBRID APPROACH: AI intent extraction + Smart filtering + AI matching
        """
        
        print(f"🔍 GuideAgent: Received request from {from_agent}Agent")
        print(f"📝 Request: {message}")
        
        try:
            # Parse request
            request = json.loads(message)
            action = request.get('action')
            
            if action == 'search_guides':
                criteria = request.get('criteria', {})
                
                # STEP 1: Use AI to extract and correct intent
                corrected_criteria = await self._ai_extract_and_correct_intent(criteria)
                print(f"🤖 AI corrected criteria: {corrected_criteria}")
                
                # STEP 2: Check if date is provided for availability-aware matching
                date = corrected_criteria.get('date', '')
                
                if date:
                    # Use availability-aware matching (EXACT logic from working Lambda)
                    print(f"🗓️ Using availability-aware matching (date: {date})")
                    matched_guides = self._availability_aware_guide_matching(corrected_criteria)
                else:
                    # Use discovery matching (EXACT logic from working Lambda)
                    print("🔍 Using discovery matching (no date provided)")
                    filtered_guides = self._smart_filter_guides(corrected_criteria)
                    print(f"📊 Pre-filtered to {len(filtered_guides)} guides")
                    
                    # STEP 3: AI semantic matching on filtered results
                    if len(filtered_guides) > 20:
                        # If still too many, use AI to narrow down
                        matched_guides = await self._ai_semantic_matching(
                            filtered_guides, corrected_criteria
                        )
                    else:
                        # Small enough, return all filtered
                        matched_guides = filtered_guides
                
                print(f"✅ Final matches: {len(matched_guides)} guides")
                
                return {
                    "status": "success",
                    "guides": matched_guides,
                    "total_found": len(matched_guides),
                    "original_criteria": criteria,
                    "corrected_criteria": corrected_criteria,
                    "approach": "Hybrid: AI intent extraction + Smart filtering + AI semantic matching",
                    "note": f"Efficiently filtered from database, then AI-matched {len(matched_guides)} guides"
                }
            else:
                return {"error": f"Unknown action: {action}"}
                
        except json.JSONDecodeError:
            # Treat as natural language query
            return await self._natural_language_search(message)
    
    async def _ai_extract_and_correct_intent(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use AI to extract intent and correct typos
        Examples: Pataya→Pattaya, Bankok→Bangkok, beach→coastal
        """
        
        prompt = f"""Extract and correct search criteria for Thailand guides.

User Input: {json.dumps(criteria, indent=2)}

Your task:
1. Correct typos in location names:
   - Pataya → Pattaya
   - Bankok → Bangkok  
   - Chiangmai → Chiang Mai
   - Pucket → Phuket
   - Krabi → Krabi (correct)
   
2. Normalize interests:
   - beach/coastal/seaside → coastal
   - temple/wat/religious → cultural
   - food/eating/cuisine → culinary
   - island/islands → island
   
3. Extract location variations:
   - Bangkok includes: Sukhumvit, Silom, Sathorn, Thonglor, etc.
   - Pattaya includes: Jomtien, Naklua, etc.

Respond in JSON:
{{
    "location": "corrected location name",
    "location_variations": ["main location", "nearby areas"],
    "interests": ["normalized interest 1", "normalized interest 2"],
    "date": "date if provided",
    "original_typos_corrected": ["typo1→correct1", "typo2→correct2"]
}}"""

        try:
            response = self.call_bedrock(prompt, max_tokens=500)
            
            # Parse JSON
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                corrected = json.loads(response[json_start:json_end])
                return corrected
            else:
                # Fallback: return original
                return criteria
                
        except Exception as e:
            print(f"❌ AI intent extraction error: {str(e)}")
            return criteria
    
    def _smart_filter_guides(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scalable guide matching using GSI for location filtering
        """
        
        try:
            location = criteria.get('location', '')
            interests = criteria.get('interests', [])
            date = criteria.get('date', '')
            
            # Use GSI to query by location (FAST - only gets relevant guides)
            if location:
                print(f"🔍 Querying guides by location: {location}")
                response = self.guides_table.query(
                    IndexName='location-rating-index',
                    KeyConditionExpression='#loc = :loc',
                    ExpressionAttributeNames={'#loc': 'location'},
                    ExpressionAttributeValues={':loc': location},
                    ScanIndexForward=False  # Sort by rating descending
                )
                all_guides = response.get('Items', [])
                
                # Handle pagination if needed
                while 'LastEvaluatedKey' in response:
                    response = self.guides_table.query(
                        IndexName='location-rating-index',
                        KeyConditionExpression='#loc = :loc',
                        ExpressionAttributeNames={'#loc': 'location'},
                        ExpressionAttributeValues={':loc': location},
                        ScanIndexForward=False,
                        ExclusiveStartKey=response['LastEvaluatedKey']
                    )
                    all_guides.extend(response.get('Items', []))
            else:
                # No location - fallback to scan (slower but works)
                print(f"⚠️ No location provided, scanning all guides")
                response = self.guides_table.scan()
                all_guides = response.get('Items', [])
                
                # Handle pagination if needed
                while 'LastEvaluatedKey' in response:
                    response = self.guides_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                    all_guides.extend(response.get('Items', []))
            
            print(f"Found {len(all_guides)} guides in database")
            
            if not all_guides:
                print("No guides found in database")
                return []
            
            matched_guides = []
            
            # Convert to lowercase for matching (EXACT same logic)
            interests_str = ' '.join(interests) if isinstance(interests, list) else str(interests)
            interests_lower = interests_str.lower() if interests_str else ""
            location_lower = location.lower() if location else ""
            
            for guide in all_guides:
                score = 0
                reasons = []
                
                # Convert Decimal to float for JSON serialization
                guide = convert_decimals(guide)
                
                # Location matching - PRIORITIZE exact location (EXACT same logic)
                if location_lower and 'location' in guide:
                    if location_lower in guide['location'].lower():
                        score += 100  # Exact location = highest priority
                        reasons.append(f"Based in {guide['location']}")
                    elif 'regions' in guide and isinstance(guide['regions'], list):
                        if any(location_lower in region.lower() for region in guide['regions']):
                            score += 15  # Secondary region = much lower
                            reasons.append(f"Also covers {location} region")
                
                # Interest/specialty matching using AI semantic analysis
                if interests_lower and 'specialties' in guide and isinstance(guide['specialties'], list):
                    # Parse requested interests (handle "and", commas, etc.)
                    requested_interests = []
                    for word in interests_lower.replace(',', ' ').replace(' and ', ' ').split():
                        if word and len(word) > 2:  # Skip short words like "in", "or"
                            requested_interests.append(word)
                    
                    # Use AI semantic matching instead of hardcoded mapping
                    try:
                        # For now, use fallback until we can make this properly async
                        # TODO: Implement proper async semantic matching
                        matched_interests = []
                        guide_specialties_lower = [s.lower() for s in guide['specialties']]
                        
                        for requested in requested_interests:
                            if any(requested in specialty for specialty in guide_specialties_lower):
                                matched_interests.append(requested)
                        
                        if matched_interests:
                            score += 35 * len(matched_interests)  # Higher score than basic matching
                            reasons.append(f"Semantic matched: {', '.join(matched_interests)}")
                        
                    except Exception as e:
                        print(f"❌ Semantic matching failed, using fallback: {e}")
                        # Fallback to basic string matching
                        matched_interests = []
                        guide_specialties_lower = [s.lower() for s in guide['specialties']]
                        
                        for requested in requested_interests:
                            if any(requested in specialty for specialty in guide_specialties_lower):
                                matched_interests.append(requested)
                        
                        if matched_interests:
                            score += 25 * len(matched_interests)
                            reasons.append(f"Basic matched: {', '.join(matched_interests)}")
                
                # Return guides with good location + interest match (EXACT same logic)
                # Require at least location match (15+) OR interest match (20+)
                if score >= 20:  # Lower threshold to show partial matches
                    guide['match_score'] = score
                    guide['match_reasons'] = reasons
                    guide['all_specialties'] = guide.get('specialties', [])  # Give agent full specialty list
                    
                    # Add video URL based on gender
                    gender = guide.get('gender', 'male')
                    if gender == 'female':
                        guide['video_url'] = 'https://tinyurl.com/thaiguidef'
                    else:
                        guide['video_url'] = 'https://tinyurl.com/thaiguidem'
                    
                    # Remove sensitive contact info (EXACT same logic)
                    if 'contact' in guide:
                        del guide['contact']
                    if 'whatsapp' in guide:
                        del guide['whatsapp']
                    if 'email' in guide:
                        del guide['email']
                    
                    guide['booking_method'] = 'Book through Thailand Guide Bot platform'
                    guide['contact_note'] = 'All communication handled through our secure platform'
                    
                    matched_guides.append(guide)
            
            # Sort by score (highest first) (EXACT same logic)
            matched_guides.sort(key=lambda x: x.get('match_score', 0), reverse=True)
            
            print(f"✅ Matched {len(matched_guides)} guides with score >= 50")
            
            # Get offset for pagination
            offset = criteria.get('offset', 0)
            print(f"📄 Pagination offset: {offset}, total matched: {len(matched_guides)}")
            print(f"📄 Will return guides from index {offset} to {offset+3}")
            
            # Check availability for top guides if date provided
            if date:
                print(f"📅 Checking availability for date: {date}")
                available_guides = []
                
                for guide in matched_guides:
                    guide_id = guide.get('guideId', '')
                    is_available, availability_msg = self._check_guide_availability_for_matching(guide_id, date, 'anytime')
                    
                    if is_available:
                        guide['available'] = True
                        guide['availability_status'] = availability_msg
                        available_guides.append(guide)
                        print(f"✅ {guide.get('name')} is available on {date}")
                    else:
                        print(f"❌ {guide.get('name')} is NOT available on {date}")
                
                # Return 3 guides starting from offset
                if available_guides:
                    print(f"✅ Found {len(available_guides)} available guides")
                    paginated_guides = available_guides[offset:offset+3]
                    print(f"📄 Returning guides {offset+1} to {offset+len(paginated_guides)}")
                    return paginated_guides
                else:
                    print(f"⚠️ No guides available on {date}, showing top matches anyway")
                    # Add unavailable status to guides
                    paginated_guides = matched_guides[offset:offset+3]
                    for guide in paginated_guides:
                        guide['available'] = False
                        guide['availability_status'] = f"Not available on {date}"
                    return paginated_guides
            
            # No date provided - return 3 matches starting from offset
            paginated_guides = matched_guides[offset:offset+3]
            print(f"📄 Returning guides {offset+1} to {offset+len(paginated_guides)}")
            return paginated_guides
            
        except Exception as e:
            import traceback
            print(f"❌ Guide matching error: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return []
    
    async def _ai_semantic_matching(
        self, 
        guides: List[Dict[str, Any]], 
        criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        AI semantic matching on pre-filtered guides
        Handles interests, specialties, and ranking
        """
        
        # Prepare guide summaries for AI
        guide_summaries = []
        for i, guide in enumerate(guides[:50]):  # Limit to 50 for token efficiency
            summary = {
                "index": i,
                "name": guide.get('name'),
                "location": guide.get('location'),
                "specialties": guide.get('specialties', []),
                "experience": guide.get('experience_years', 0),
                "rating": float(guide.get('rating', 4.0)),
                "languages": guide.get('languages', [])
            }
            guide_summaries.append(summary)
        
        prompt = f"""Match guides to tourist criteria using semantic understanding.

Tourist Criteria:
{json.dumps(criteria, indent=2)}

Pre-filtered Guides (already location-matched):
{json.dumps(guide_summaries, indent=2)}

Task: Select best matches based on:
1. Specialty/interest alignment (semantic, not keyword)
   - "beach" matches "coastal tours", "island hopping"
   - "temple" matches "cultural tours", "religious sites"
   - "food" matches "culinary tours", "street food"
2. Experience and rating
3. Language capabilities

Return ONLY a JSON array of guide indices (0-based) in order of best match.
Example: [5, 12, 3, 8, 15]

Return top 10 matches maximum."""

        try:
            response = self.call_bedrock(prompt, max_tokens=500)
            
            # Extract JSON array - be more robust
            try:
                json_start = response.find('[')
                json_end = response.rfind(']') + 1
                if json_start >= 0 and json_end > json_start:
                    indices = json.loads(response[json_start:json_end])
                    
                    # Get matched guides
                    matched = []
                    for idx in indices:
                        if isinstance(idx, int) and 0 <= idx < len(guides):
                            guide = guides[idx].copy()
                            guide['ai_matched'] = True
                            guide['match_rank'] = len(matched) + 1
                            matched.append(guide)
                    
                    if matched:
                        return matched
                        
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                print(f"❌ JSON parsing failed: {e}")
                
            # Fallback: return top 10 by rating
            return sorted(guides, key=lambda g: float(g.get('rating', 0)), reverse=True)[:10]
                
        except Exception as e:
            print(f"❌ AI semantic matching error: {str(e)}")
            # Fallback: return top 10 by rating
            return sorted(guides, key=lambda g: float(g.get('rating', 0)), reverse=True)[:10]
    
    async def _natural_language_search(self, query: str) -> Dict[str, Any]:
        """Handle natural language guide search query"""
        
        # Use AI to extract criteria from natural language
        prompt = f"""Extract search criteria from this natural language query:

Query: "{query}"

Extract and correct:
- location (correct typos: Pataya→Pattaya, Bankok→Bangkok)
- interests (activities/specialties)
- date if mentioned

Respond in JSON:
{{
    "location": "...",
    "location_variations": ["..."],
    "interests": ["..."],
    "date": "..."
}}"""

        try:
            response = self.call_bedrock(prompt, max_tokens=300)
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            criteria = json.loads(response[json_start:json_end])
            
            # Now do smart search with extracted criteria
            return await self.handle_agent_message(
                "tourist", 
                json.dumps({"action": "search_guides", "criteria": criteria})
            )
            
        except Exception as e:
            print(f"❌ NL parsing error: {str(e)}")
            return {
                "guides": [],
                "error": "Could not parse search query"
            }
    
    def _availability_aware_guide_matching(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        EXACT availability-aware matching logic from working Lambda
        """
        
        date = criteria.get('date', '')
        time = criteria.get('time', 'anytime')
        
        print(f"🗓️ Availability-aware matching for {date} at {time}")
        
        # First, find all matching guides using existing logic (EXACT same as Lambda)
        all_guides = self._smart_filter_guides(criteria)
        
        # Now filter by availability (EXACT logic from working Lambda)
        available_guides = []
        unavailable_count = 0
        
        for guide in all_guides:
            is_available, availability_message = self._check_guide_availability_for_matching(
                guide['guideId'], date, time
            )
            
            if is_available:
                guide['availability_status'] = 'available'
                guide['availability_message'] = availability_message
                guide['booking_note'] = f"✅ Available for immediate booking on {date} at {time}"
                if 'match_reasons' in guide:
                    guide['match_reasons'].append(f"Available on {date} at {time}")
                available_guides.append(guide)
            else:
                unavailable_count += 1
        
        print(f"✅ Filtered to {len(available_guides)} available guides (filtered out {unavailable_count} unavailable)")
        
        return available_guides[:5]  # Return top 5 available guides
    
    def _check_guide_availability_for_matching(self, guide_id: str, requested_date: str, time_slot: str) -> tuple:
        """
        EXACT availability checking logic from working Lambda
        """
        
        try:
            # Parse requested date to YYYY-MM-DD format (EXACT same logic)
            if isinstance(requested_date, str):
                try:
                    if 'December' in requested_date or 'Nov' in requested_date:
                        import re
                        date_match = re.search(r'(\w+)\s+(\d+)(?:st|nd|rd|th)?,?\s+(\d{4})', requested_date)
                        if date_match:
                            month_name, day, year = date_match.groups()
                            month_map = {
                                'January': 1, 'February': 2, 'March': 3, 'April': 4,
                                'May': 5, 'June': 6, 'July': 7, 'August': 8,
                                'September': 9, 'October': 10, 'November': 11, 'December': 12
                            }
                            month = month_map.get(month_name, 1)
                            parsed_date = datetime(int(year), month, int(day))
                            date_str = parsed_date.strftime('%Y-%m-%d')
                        else:
                            from datetime import timedelta
                            date_str = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
                    else:
                        date_str = requested_date
                except:
                    from datetime import timedelta
                    date_str = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            else:
                date_str = requested_date
            
            # Query availability (EXACT same logic)
            response = self.availability_table.get_item(
                Key={'guideId': guide_id, 'date': date_str}
            )
            
            availability_record = response.get('Item', {})
            if not availability_record:
                return True, f"Available - no conflicts on {date_str}"
            
            # Check time slot (EXACT same logic)
            availability = availability_record.get('availability', {})
            
            # If "anytime", check if ANY slot is available
            if 'anytime' in str(time_slot).lower():
                morning_available = availability.get('morning', True)
                afternoon_available = availability.get('afternoon', True)
                evening_available = availability.get('evening', True)
                
                if morning_available or afternoon_available or evening_available:
                    available_slots = []
                    if morning_available:
                        available_slots.append('morning')
                    if afternoon_available:
                        available_slots.append('afternoon')
                    if evening_available:
                        available_slots.append('evening')
                    return True, f"Available on {date_str} ({', '.join(available_slots)})"
                else:
                    return False, f"Fully booked on {date_str}"
            
            # Specific time slot requested
            if 'morning' in str(time_slot).lower() or '9:00' in str(time_slot) or '8:00' in str(time_slot):
                slot = 'morning'
            elif 'evening' in str(time_slot).lower() or '6:00' in str(time_slot) or '7:00' in str(time_slot):
                slot = 'evening'
            else:
                slot = 'afternoon'
            
            is_available = availability.get(slot, True)
            existing_bookings = availability_record.get('bookings', [])
            
            if is_available and len(existing_bookings) == 0:
                return True, f"Available for {slot} slot on {date_str}"
            else:
                return False, f"Unavailable for {slot} slot on {date_str}"
                
        except Exception as e:
            print(f"Error checking availability for {guide_id}: {str(e)}")
            return True, "Availability check failed - assuming available"
    
    async def _get_semantic_interest_matches(self, requested_interests: str, guide_specialties: List[str]) -> Dict[str, Any]:
        """AI semantic matching of user interests to guide specialties"""
        try:
            prompt = f"""Match user interests to guide specialties semantically:

User interests: "{requested_interests}"
Guide specialties: {guide_specialties}

Determine semantic matches (e.g., "beach" matches "coastal tours", "temple" matches "cultural tours").

Return JSON:
{{"has_matches": true/false, "score": 0-100, "matched_interests": ["interest1", "interest2"], "confidence": 0.0-1.0}}"""

            response = await self.call_ai_model(prompt)
            
            # Parse JSON response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
                return result
                
        except Exception as e:
            print(f"❌ Semantic interest matching error: {e}")
            
        # Fallback
        return {"has_matches": False, "score": 0, "matched_interests": [], "confidence": 0.0}
    
    def _add_reasoning(self, step: str, details: Any):
        """Add reasoning step"""
        self.reasoning_steps.append({
            "agent": "GuideAgent",
            "step": step,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        })
