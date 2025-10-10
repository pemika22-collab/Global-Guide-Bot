"""
Base Agent Class for AgentCore System
All specialized agents inherit from this
"""

import json
import boto3
from typing import Dict, Any, Optional
from datetime import datetime


class BaseAgent:
    """Base class for all AgentCore agents"""
    
    def __init__(self, name: str, model_id: str, system_prompt: str):
        """
        Initialize base agent
        
        Args:
            name: Agent name (e.g., 'tourist', 'guide', 'cultural', 'booking')
            model_id: Bedrock model ID
            system_prompt: System prompt defining agent behavior
        """
        self.name = name
        self.model_id = model_id
        self.system_prompt = system_prompt
        self.bedrock = boto3.client('bedrock-runtime', region_name='eu-west-1')
        self.conversation_history = []
        
    async def process(
        self, 
        message: str, 
        context: Dict[str, Any],
        orchestrator: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Process a message (to be implemented by subclasses)
        
        Args:
            message: User message or agent message
            context: Conversation context
            orchestrator: Reference to orchestrator for agent-to-agent communication
            
        Returns:
            Response dictionary with agent output
        """
        raise NotImplementedError("Subclasses must implement process()")
        
    def call_bedrock(self, prompt: str, max_tokens: int = 2000) -> str:
        """
        Call Bedrock API with the agent's model
        
        Args:
            prompt: User prompt
            max_tokens: Maximum tokens in response
            
        Returns:
            Model response text
        """
        try:
            # Prepare request based on model type
            if 'nova' in self.model_id.lower():
                # Nova Pro format
                request_body = {
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"text": prompt}]
                        }
                    ],
                    "system": [{"text": self.system_prompt}],
                    "inferenceConfig": {
                        "max_new_tokens": max_tokens,
                        "temperature": 0.7
                    }
                }
            else:
                # Claude format
                request_body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "system": self.system_prompt,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7
                }
            
            # Call Bedrock
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            if 'nova' in self.model_id.lower():
                # Nova Pro response format
                return response_body['output']['message']['content'][0]['text']
            else:
                # Claude response format
                return response_body['content'][0]['text']
                
        except Exception as e:
            print(f"❌ {self.name}Agent Bedrock error: {str(e)}")
            raise
            
    async def delegate_to(
        self, 
        agent_name: str, 
        message: str, 
        orchestrator: Any,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Delegate task to another agent
        
        Args:
            agent_name: Target agent name
            message: Message to send
            orchestrator: Orchestrator reference
            context: Shared context to pass to target agent
            
        Returns:
            Response from target agent
        """
        if not orchestrator:
            raise ValueError("Orchestrator required for delegation")
            
        print(f"🔄 {self.name}Agent → {agent_name}Agent: {message[:100]}...")
        
        return await orchestrator.agent_to_agent(
            from_agent=self.name,
            to_agent=agent_name,
            message=message,
            context=context
        )
        
    def add_to_history(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    def get_history_context(self, max_messages: int = 5) -> str:
        """Get recent conversation history as context"""
        recent = self.conversation_history[-max_messages:]
        return "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in recent
        ])
    
    def _detect_image_format(self, image_base64: str) -> str:
        """
        Detect image format from base64 data
        
        Args:
            image_base64: Base64-encoded image
            
        Returns:
            Image format: 'jpeg', 'png', 'gif', or 'webp'
        """
        import base64
        
        # Decode first few bytes to check magic numbers
        try:
            image_bytes = base64.b64decode(image_base64[:100])
            
            # Check magic numbers (file signatures)
            if image_bytes.startswith(b'\xff\xd8\xff'):
                return 'jpeg'
            elif image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
                return 'png'
            elif image_bytes.startswith(b'GIF87a') or image_bytes.startswith(b'GIF89a'):
                return 'gif'
            elif image_bytes.startswith(b'RIFF') and b'WEBP' in image_bytes[:20]:
                return 'webp'
            else:
                # Default to JPEG (most common from WhatsApp)
                return 'jpeg'
        except Exception:
            # If detection fails, default to JPEG
            return 'jpeg'
    
    def call_bedrock_with_image(
        self, 
        prompt: str, 
        image_base64: str,
        model_id: Optional[str] = None,
        max_tokens: int = 1000
    ) -> str:
        """
        Call Bedrock API with image input (for Nova Act/multimodal models)
        
        Automatically detects image format (JPEG, PNG, GIF, WebP) from base64 data.
        Supports images from WhatsApp, web uploads, or any source.
        
        Args:
            prompt: Text prompt
            image_base64: Base64-encoded image (any format)
            model_id: Optional model override (defaults to agent's model)
            max_tokens: Maximum tokens in response
            
        Returns:
            Model response text
        """
        try:
            # Use provided model or default to agent's model
            model = model_id or self.model_id
            
            # Auto-detect image format
            image_format = self._detect_image_format(image_base64)
            print(f"🖼️  Detected image format: {image_format}")
            
            # Nova models support multimodal input
            if 'nova' in model.lower():
                request_body = {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "image": {
                                        "format": image_format,  # Auto-detected format
                                        "source": {
                                            "bytes": image_base64
                                        }
                                    }
                                },
                                {
                                    "text": prompt
                                }
                            ]
                        }
                    ],
                    "system": [{"text": self.system_prompt}],
                    "inferenceConfig": {
                        "max_new_tokens": max_tokens,
                        "temperature": 0.7
                    }
                }
            else:
                # Claude 3 models also support images
                request_body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "system": self.system_prompt,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/png",
                                        "data": image_base64
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": prompt
                                }
                            ]
                        }
                    ],
                    "temperature": 0.7
                }
            
            # Call Bedrock
            response = self.bedrock.invoke_model(
                modelId=model,
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            if 'nova' in model.lower():
                return response_body['output']['message']['content'][0]['text']
            else:
                return response_body['content'][0]['text']
                
        except Exception as e:
            print(f"❌ {self.name}Agent Bedrock image call error: {str(e)}")
            raise
