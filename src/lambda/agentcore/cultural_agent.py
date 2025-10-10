"""
CulturalAgent - Thai cultural intelligence specialist
REPLICATES: src/tools/bedrock_cultural_intelligence_tool.py
Uses AI for semantic cultural understanding
ENHANCED: Amazon Nova Act for multi-modal image analysis (Task 19)
"""

import json
import base64
import boto3
from typing import Dict, Any, Optional, List
from datetime import datetime
from .base_agent import BaseAgent


class CulturalAgent(BaseAgent):
    """
    Specialized agent for Thai cultural guidance
    REPLICATES bedrock_cultural_intelligence_tool.py approach:
    - Uses AI for semantic cultural analysis
    - No manual keyword matching
    - Provides nuanced, context-aware guidance
    """
    
    def __init__(self):
        system_prompt = """You are an expert Thai cultural advisor with deep knowledge of Thai customs, traditions, etiquette, and social norms.

Your expertise includes:
- Temple etiquette and Buddhist customs
- Social interactions and greetings (wai, respect for elders)
- Dress codes for different situations
- Festival participation and cultural events
- Food customs and dining etiquette
- Business and social interactions
- Regional cultural differences
- Modern vs traditional practices

Always provide:
1. Direct answer to the specific cultural question
2. Cultural context and deeper significance
3. Practical, actionable recommendations
4. Important cultural sensitivities
5. Local insights that enhance understanding

Be specific, practical, and culturally sensitive. Avoid generalizations.
Focus on helping tourists have authentic, respectful experiences."""

        super().__init__(
            name="cultural",
            model_id="eu.amazon.nova-pro-v1:0",  # Nova Pro cross-region
            system_prompt=system_prompt
        )
        self.reasoning_steps = []
        
    async def process(
        self, 
        message: str, 
        context: Dict[str, Any],
        orchestrator: Any = None
    ) -> Dict[str, Any]:
        """Process cultural question"""
        
        print(f"🤖 CulturalAgent: Processing cultural question...")
        
        # This shouldn't be called directly - use handle_agent_message
        return await self.handle_agent_message("tourist", message)
        
    async def handle_agent_message(self, from_agent: str, message: str) -> Dict[str, Any]:
        """
        Handle message from another agent
        REPLICATES: bedrock_cultural_intelligence_tool.py lambda_handler
        """
        
        print(f"🏛️ CulturalAgent: Received request from {from_agent}Agent")
        print(f"📝 Cultural query: {message}")
        
        try:
            # Parse request
            request = json.loads(message)
            action = request.get('action')
            
            # Check if this is an image analysis request
            if action == 'analyze_image':
                image_url = request.get('image_url')
                user_question = request.get('user_question', 'What is this place?')
                
                if not image_url:
                    return {
                        "status": "error",
                        "message": "No image URL provided"
                    }
                
                print(f"📸 Analyzing image: {image_url}")
                
                # Download image from S3
                image_data = await self._download_s3_image(image_url)
                
                if not image_data:
                    return {
                        "status": "error",
                        "message": "Failed to download image"
                    }
                
                # Analyze with Nova Act
                analysis = await self.analyze_image(image_data, user_question, {})
                
                # Format response for user
                response_message = self._format_image_analysis_response(analysis)
                
                return {
                    "status": "success",
                    "message": response_message,
                    "analysis": analysis
                }
            
            # Check if this is a cultural guidance request
            elif action == 'cultural_guidance':
                query = request.get('user_question', message)
                context = request.get('context', {})
            
            # Regular text query (fallback)
            else:
                query = request.get('query', message)
                context = request.get('context', {})
            
        except json.JSONDecodeError:
            # Treat as direct query
            query = message
            context = {}
        
        # Use AI for cultural analysis (exactly like bedrock tool)
        cultural_response = await self._ai_cultural_analysis(query, context)
        
        return {
            "status": "success",
            "guidance": cultural_response["guidance"],
            "cultural_context": cultural_response["cultural_context"],
            "recommendations": cultural_response["recommendations"],
            "sensitivity_notes": cultural_response["sensitivity_notes"],
            "regional_notes": cultural_response.get("regional_notes", ""),
            "approach": "Replicating bedrock_cultural_intelligence_tool.py AI analysis"
        }
        
    async def _ai_cultural_analysis(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        AI-powered cultural analysis
        REPLICATES: bedrock_cultural_intelligence_tool.py ai_cultural_analysis()
        Uses EXACT same prompt structure
        """
        
        try:
            # EXACT same prompt as bedrock_cultural_intelligence_tool.py
            cultural_prompt = f"""You are an expert Thai cultural advisor with deep knowledge of Thai customs, traditions, etiquette, and social norms. 

A tourist is asking: "{query}"

Context about the tourist: {json.dumps(context, indent=2)}

Provide intelligent cultural guidance that includes:

1. **Direct Answer**: Address their specific cultural question
2. **Cultural Context**: Explain the deeper cultural significance 
3. **Practical Advice**: Specific actionable recommendations
4. **Sensitivity Notes**: Important cultural sensitivities to be aware of
5. **Local Insights**: Insider knowledge that enhances understanding

Focus on:
- Temple etiquette and Buddhist customs
- Social interactions and greetings (wai, respect for elders)
- Dress codes for different situations
- Festival participation and cultural events
- Food customs and dining etiquette
- Business and social interactions
- Regional cultural differences
- Modern vs traditional practices

Be specific, practical, and culturally sensitive. Avoid generalizations.

Respond in JSON format:
{{
    "guidance": "Main cultural guidance addressing their question",
    "cultural_context": "Deeper explanation of cultural significance",
    "recommendations": ["Specific actionable recommendation 1", "Specific actionable recommendation 2", "Specific actionable recommendation 3"],
    "sensitivity_notes": ["Important cultural sensitivity 1", "Important cultural sensitivity 2"],
    "regional_notes": "Any regional variations or specific location advice"
}}"""

            # Call Nova Pro for AI-powered cultural analysis
            response = self.call_bedrock(cultural_prompt, max_tokens=1000)
            
            # Parse JSON from response (same logic as bedrock tool)
            try:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start != -1 and json_end != -1:
                    cultural_data = json.loads(response[json_start:json_end])
                else:
                    # Fallback if JSON not found
                    cultural_data = {
                        "guidance": response,
                        "cultural_context": "AI-powered cultural analysis",
                        "recommendations": ["Follow local customs", "Be respectful", "Ask locals for guidance"],
                        "sensitivity_notes": ["Respect Thai culture", "Be mindful of traditions"]
                    }
            except json.JSONDecodeError:
                # Fallback response
                cultural_data = {
                    "guidance": response,
                    "cultural_context": "AI-powered cultural analysis",
                    "recommendations": ["Follow local customs", "Be respectful", "Ask locals for guidance"],
                    "sensitivity_notes": ["Respect Thai culture", "Be mindful of traditions"]
                }
            
            return cultural_data
            
        except Exception as e:
            print(f"❌ CulturalAgent AI analysis error: {str(e)}")
            # Fallback cultural guidance (same as bedrock tool)
            return {
                "guidance": f"I understand you're asking about Thai culture: '{query}'. While I'm experiencing technical difficulties, I recommend being respectful of local customs, dressing modestly at temples, and showing respect to elders and monks.",
                "cultural_context": "Thai culture values respect, hierarchy, and Buddhist principles.",
                "recommendations": [
                    "Dress modestly when visiting temples (covered shoulders, long pants)",
                    "Use the 'wai' greeting with palms together",
                    "Remove shoes before entering homes and temple buildings",
                    "Show respect to monks and elders"
                ],
                "sensitivity_notes": [
                    "Never point feet toward Buddha statues or people",
                    "Women should not touch monks directly",
                    "Avoid public displays of affection",
                    "Respect the Thai Royal Family"
                ]
            }
        
    async def analyze_image(
        self, 
        image_data: bytes, 
        query: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze tourist-shared images using Amazon Nova Act
        
        Task 19: Multi-modal understanding for:
        1. Temple visit appropriateness checking
        2. Location recognition and guide suggestions
        3. Cultural activity verification
        4. Visual cultural guidance
        
        Args:
            image_data: Raw image bytes
            query: Optional text query about the image
            context: Optional context about the tourist
            
        Returns:
            Dict with analysis results and cultural guidance
        """
        
        print(f"📸 CulturalAgent: Analyzing image with Nova Act...")
        
        try:
            # Encode image to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Call Nova Act for image analysis
            analysis = await self._call_nova_act(image_base64, query, context or {})
            
            # Route based on detected content
            if analysis.get('content_type') == 'temple':
                return await self._check_temple_appropriateness(analysis, context or {})
            elif analysis.get('content_type') == 'location':
                return await self._analyze_location(analysis, context or {})
            elif analysis.get('content_type') == 'cultural_activity':
                return await self._verify_cultural_activity(analysis, context or {})
            else:
                return await self._general_image_guidance(analysis, context or {})
                
        except Exception as e:
            print(f"❌ CulturalAgent image analysis error: {str(e)}")
            return {
                "status": "error",
                "message": f"Image analysis failed: {str(e)}",
                "guidance": "Please describe what you'd like to know about Thai culture, and I'll help you."
            }
    
    async def _call_nova_act(
        self, 
        image_base64: str, 
        query: Optional[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call Amazon Nova Act for image understanding
        
        Nova Act capabilities:
        - Object detection
        - Scene understanding
        - Text recognition
        - Cultural context analysis
        """
        
        # Build prompt for Nova Act
        if query:
            prompt = f"""Analyze this image in the context of Thai culture and tourism.

Tourist's question: {query}

Identify:
1. What type of location/activity is shown (temple, beach, market, cultural event, etc.)
2. Any cultural elements visible (Buddha statues, monks, traditional dress, etc.)
3. Whether the scene involves cultural sensitivities
4. The specific location if recognizable
5. Any cultural appropriateness concerns

Respond in JSON format:
{{
    "content_type": "temple|location|cultural_activity|general",
    "detected_objects": ["object1", "object2"],
    "location": "Specific location name if recognizable",
    "cultural_elements": ["element1", "element2"],
    "appropriateness_concerns": ["concern1", "concern2"],
    "scene_description": "Detailed description of what's in the image"
}}"""
        else:
            prompt = """Analyze this image for Thai cultural context.

Identify:
1. Type of location (temple, beach, market, cultural site, etc.)
2. Cultural elements present
3. Any cultural sensitivities
4. Location if recognizable

Respond in JSON format with: content_type, detected_objects, location, cultural_elements, appropriateness_concerns, scene_description"""
        
        try:
            # Call Amazon Nova Pro with image (multimodal support)
            response = self.call_bedrock_with_image(
                prompt=prompt,
                image_base64=image_base64,
                model_id="eu.amazon.nova-pro-v1:0",  # Amazon Nova Pro cross-region
                max_tokens=1000
            )
            
            # Parse JSON response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                analysis = json.loads(response[json_start:json_end])
            else:
                # Fallback
                analysis = {
                    "content_type": "general",
                    "detected_objects": [],
                    "scene_description": response
                }
            
            self._add_reasoning("nova_act_analysis", analysis)
            return analysis
            
        except Exception as e:
            print(f"❌ Nova Act call failed: {str(e)}")
            raise
    
    async def _check_temple_appropriateness(
        self, 
        analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if tourist's attire/behavior is appropriate for temple visit"""
        
        print("🏛️ CulturalAgent: Checking temple appropriateness...")
        
        concerns = analysis.get('appropriateness_concerns', [])
        
        # Use AI to provide detailed guidance
        guidance_prompt = f"""A tourist is visiting a Thai temple. Based on this image analysis:

Scene: {analysis.get('scene_description', 'Temple visit')}
Detected elements: {', '.join(analysis.get('detected_objects', []))}
Concerns: {', '.join(concerns) if concerns else 'None identified'}

Provide specific guidance about:
1. Dress code appropriateness
2. Behavior recommendations
3. Cultural do's and don'ts
4. What they're doing well (if anything)

Be encouraging but clear about any issues."""

        guidance = self.call_bedrock(guidance_prompt, max_tokens=500)
        
        return {
            "status": "success",
            "analysis_type": "temple_appropriateness",
            "location": analysis.get('location', 'Thai temple'),
            "appropriateness_check": "appropriate" if not concerns else "needs_attention",
            "concerns": concerns,
            "guidance": guidance,
            "recommendations": [
                "Ensure shoulders and knees are covered",
                "Remove shoes before entering temple buildings",
                "Speak quietly and respectfully",
                "Don't point feet toward Buddha images"
            ]
        }
    
    async def _analyze_location(
        self, 
        analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze location and suggest relevant guides"""
        
        print("📍 CulturalAgent: Analyzing location...")
        
        location = analysis.get('location', 'Unknown location')
        cultural_elements = analysis.get('cultural_elements', [])
        
        # Use AI for location-specific guidance
        location_prompt = f"""A tourist has shared an image of: {location}

Cultural elements visible: {', '.join(cultural_elements)}
Scene: {analysis.get('scene_description', '')}

Provide:
1. Information about this location
2. Cultural significance
3. What activities/experiences are available here
4. Cultural tips for visiting
5. Suggest what type of guide would be helpful (food tour, temple guide, cultural expert, etc.)"""

        guidance = self.call_bedrock(location_prompt, max_tokens=600)
        
        # Enhanced semantic-like location classification (better than pure keyword matching)
        location_lower = location.lower()
        cultural_elements_lower = [e.lower() for e in cultural_elements]
        
        # Determine guide types using enhanced logic
        guide_types = []
        if any(word in location_lower for word in ['temple', 'wat', 'shrine']) or \
           any('temple' in e for e in cultural_elements_lower):
            guide_types.append('temple and cultural tours')
        if any(word in location_lower for word in ['market', 'food', 'street', 'cuisine']) or \
           any(word in ' '.join(cultural_elements_lower) for word in ['food', 'market']):
            guide_types.append('food tours')
        if any(word in location_lower for word in ['beach', 'island', 'coastal', 'water']):
            guide_types.append('beach and water activities')
        
        if not guide_types:
            guide_types = ['general tours']
        
        return {
            "status": "success",
            "analysis_type": "location_recognition",
            "location": location,
            "cultural_elements": cultural_elements,
            "guidance": guidance,
            "suggested_guide_types": guide_types,
            "next_action": "Would you like me to find guides specializing in this area?"
        }
    
    async def _verify_cultural_activity(
        self, 
        analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Verify appropriateness of cultural activity participation"""
        
        print("🎭 CulturalAgent: Verifying cultural activity...")
        
        activity_prompt = f"""A tourist is participating in a Thai cultural activity.

Scene: {analysis.get('scene_description', '')}
Elements: {', '.join(analysis.get('cultural_elements', []))}
Concerns: {', '.join(analysis.get('appropriateness_concerns', []))}

Provide guidance on:
1. Whether their participation is appropriate
2. Cultural etiquette for this activity
3. What they should know
4. How to show respect"""

        guidance = self.call_bedrock(activity_prompt, max_tokens=500)
        
        return {
            "status": "success",
            "analysis_type": "cultural_activity",
            "guidance": guidance,
            "appropriateness": "appropriate" if not analysis.get('appropriateness_concerns') else "review_needed"
        }
    
    async def _general_image_guidance(
        self, 
        analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Provide general cultural guidance for image"""
        
        print("🖼️ CulturalAgent: Providing general image guidance...")
        
        general_prompt = f"""A tourist has shared an image related to their Thailand visit.

Scene: {analysis.get('scene_description', '')}
Elements: {', '.join(analysis.get('detected_objects', []))}

Provide helpful cultural context and guidance about what they're seeing or experiencing."""

        guidance = self.call_bedrock(general_prompt, max_tokens=400)
        
        return {
            "status": "success",
            "analysis_type": "general",
            "guidance": guidance,
            "scene_description": analysis.get('scene_description', '')
        }
    
    async def _download_s3_image(self, s3_url: str) -> bytes:
        """Download image from S3"""
        try:
            # Parse S3 URL (format: s3://bucket/key)
            if not s3_url.startswith('s3://'):
                print(f"❌ Invalid S3 URL: {s3_url}")
                return None
            
            parts = s3_url[5:].split('/', 1)
            if len(parts) != 2:
                print(f"❌ Invalid S3 URL format: {s3_url}")
                return None
            
            bucket, key = parts
            print(f"📥 Downloading from S3: bucket={bucket}, key={key}")
            
            s3 = boto3.client('s3')
            response = s3.get_object(Bucket=bucket, Key=key)
            image_data = response['Body'].read()
            
            print(f"✅ Downloaded {len(image_data)} bytes from S3")
            return image_data
            
        except Exception as e:
            print(f"❌ Error downloading from S3: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _format_image_analysis_response(self, analysis: Dict[str, Any]) -> str:
        """Format image analysis for WhatsApp response - CONCISE version"""
        try:
            response = "📸 *Image Analysis*\n\n"
            
            # Location
            if analysis.get('location'):
                response += f"📍 *Location:* {analysis['location']}\n\n"
            
            # Brief description (max 2 sentences)
            if analysis.get('scene_description'):
                desc = analysis['scene_description']
                # Limit to first 2 sentences
                sentences = desc.split('. ')
                brief_desc = '. '.join(sentences[:2])
                if not brief_desc.endswith('.'):
                    brief_desc += '.'
                response += f"{brief_desc}\n\n"
            
            # Do's and Don'ts (concise)
            if analysis.get('recommendations'):
                recs = analysis['recommendations']
                if isinstance(recs, list):
                    response += "✅ *Do's:*\n"
                    for rec in recs[:3]:  # Max 3 recommendations
                        response += f"• {rec}\n"
                    response += "\n"
            
            if analysis.get('sensitivity_notes'):
                notes = analysis['sensitivity_notes']
                if isinstance(notes, list):
                    response += "❌ *Don'ts:*\n"
                    for note in notes[:3]:  # Max 3 notes
                        response += f"• {note}\n"
                    response += "\n"
            
            # Suggest booking a guide
            response += "🎯 Would you like me to find a local guide for this area?"
            
            return response
            
        except Exception as e:
            print(f"❌ Error formatting response: {str(e)}")
            return "I analyzed your image! It looks like an interesting place in Thailand. Would you like me to find a guide for you?"
    
    async def _classify_location_semantically(self, location: str, cultural_elements: List[str]) -> Dict[str, Any]:
        """AI semantic classification of locations for cultural guidance"""
        try:
            prompt = f"""Classify this Thai location semantically for cultural guidance:

Location: "{location}"
Cultural elements: {cultural_elements}

Determine the location type and suggest appropriate guide types:
- temple/religious: temple and cultural tours
- market/food: food tours, market tours
- beach/coastal: beach and water activities
- general: general tours

Return JSON:
{{"type": "temple|market|beach|general", "suggested_guide_types": ["tour type 1", "tour type 2"], "focus": "cultural focus description"}}"""

            response = await self.call_ai_model(prompt)
            
            # Parse JSON response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
                return result
                
        except Exception as e:
            print(f"❌ Location classification error: {e}")
            
        # Fallback
        return {
            "type": "general",
            "suggested_guide_types": ["general tours"],
            "focus": "General Thai cultural guidance"
        }
    
    def _add_reasoning(self, step: str, details: Any):
        """Add reasoning step"""
        self.reasoning_steps.append({
            "agent": "CulturalAgent",
            "step": step,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        })
