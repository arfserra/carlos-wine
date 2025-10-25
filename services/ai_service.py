# services/ai_service.py
import os
import base64
import json
import tempfile
from openai import OpenAI
from typing import Dict, Any, List, Optional

class OpenAIService:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the OpenAI service."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)
    
    def analyze_wine_label(self, image_data):
        """
        Analyze wine label from in-memory image data without writing to disk
        
        Args:
            image_data: The uploaded image data (bytes)
            
        Returns:
            Dict with analysis results
        """
        try:
            # Convert image data directly to base64
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Call OpenAI API with GPT-4o
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a wine expert assistant. Extract information from this wine label image."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text", 
                                "text": """Analyze this wine label and extract the following information:
        1. The full name of the wine as it appears on the label
        2. A comprehensive description that includes:
           - Producer/winery
           - Vintage
           - Wine type (red, white, rosé, etc.)
           - Grape varietal(s)
           - Region and country
           - Detailed tasting notes (use your wine knowledge to infer expected aromas, flavors, body, acidity, and finish)
           - Notable production methods or aging information
           - Other relevant details like classification, alcohol content, etc.
        
        Format as JSON with 'name' and 'description' fields.
        
        Make the description elegant and easy to read in natural language, not as a list of attributes."""
                            },
                            {
                                "type": "image_url", 
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                            }
                        ]
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=800
            )
            
            # Parse the response
            content = json.loads(response.choices[0].message.content)
            
            return {
                "success": True,
                "data": content,
                "usage": response.usage.total_tokens
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_storage_configuration(self, description: str) -> Dict[str, Any]:
        """
        Generate storage configuration from user description.
        
        Args:
            description: User's description of their wine storage setup
            
        Returns:
            Dict with storage configuration data
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a wine storage expert. Based on the user's description of their wine storage setup, create a detailed configuration including zones and positions. 

IMPORTANT: Return ONLY valid JSON. Do not include any markdown formatting, code blocks, or explanatory text. The response must be parseable JSON.

Return a JSON object with this exact structure:
{
    "description": "Brief description of the storage setup",
    "zones": [
        {
            "name": "Zone name (e.g., 'White Wine Zone', 'Red Wine Zone', 'Champagne Zone')",
            "description": "Description of this zone",
            "positions": [
                {
                    "identifier": "Position identifier (e.g., 'A1', 'B2', 'Top-Left')",
                    "description": "Description of this position"
                }
            ]
        }
    ],
    "total_positions": number
}

Create logical zones based on wine types and organize positions within each zone. Ensure all property names are in double quotes."""
                    },
                    {
                        "role": "user",
                        "content": f"Set up my wine storage based on this description: {description}"
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=1000
            )
            
            # Parse the JSON response with better error handling
            response_text = response.choices[0].message.content
            
            # Try to clean up common JSON issues
            response_text = response_text.strip()
            
            # Handle case where AI might return markdown code block
            if response_text.startswith("```json"):
                response_text = response_text[7:]  # Remove ```json
            if response_text.endswith("```"):
                response_text = response_text[:-3]  # Remove ```
            response_text = response_text.strip()
            
            try:
                content = json.loads(response_text)
            except json.JSONDecodeError as json_error:
                # If JSON parsing fails, try to extract JSON from the response
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    try:
                        content = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        raise json_error
                else:
                    raise json_error
            
            return {
                "success": True,
                "data": content,
                "usage": response.usage.total_tokens
            }
            
        except Exception as e:
            # Add debugging information for JSON parsing errors
            error_msg = str(e)
            if "JSON" in error_msg or "json" in error_msg:
                error_msg += f" (Raw response: {response.choices[0].message.content[:200]}...)" if 'response' in locals() else ""
            
            return {
                "success": False,
                "error": error_msg
            }
    
    def get_pairing_recommendation(self, food_input, wines: List[Dict[str, str]], is_image: bool = False) -> Dict[str, Any]:
        """Get wine pairing recommendations for food."""
        try:
            # Format the list of wines
            wines_text = "\n".join([f"{i+1}. {wine['name']}: {wine['description']}" 
                                  for i, wine in enumerate(wines)])
            
            messages = [
                {
                    "role": "system",
                    "content": "You are a wine pairing expert. Recommend wines from the user's collection that would pair well with their food. If there are no wines in the collection that are good suitable, suggest alternatives to buy."
                }
            ]
            
            if is_image:
                # Process directly from image data without temp files
                base64_image = base64.b64encode(food_input).decode('utf-8')
                
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Recommend 1-3 wines from my collection that would pair well with this food. Explain why each would be a good match.\n\nMy wine collection:\n{wines_text}"
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                })
            else:
                # Process as text description (unchanged)
                messages.append({
                    "role": "user",
                    "content": f"I'm planning to eat: {food_input}\n\nRecommend 1-3 wines from my collection that would pair well with this food. Explain why each would be a good match.\n\nMy wine collection:\n{wines_text}"
                })
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=800
            )
            
            return {
                "success": True,
                "recommendation": response.choices[0].message.content,
                "usage": response.usage.total_tokens
            }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }