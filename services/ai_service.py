# services/ai_service.py
import os
import base64
import json
import tempfile
import re
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

CRITICAL REQUIREMENTS:
- Return ONLY valid JSON with no additional text
- Use double quotes for all strings
- Escape any quotes within string values using backslash
- Do not include newlines within string values
- Keep descriptions short and simple
- Ensure all strings are properly terminated

Return a JSON object with this exact structure:
{
    "description": "Brief description of the storage setup",
    "zones": [
        {
            "name": "Zone name",
            "description": "Zone description",
            "positions": [
                {
                    "identifier": "Position ID",
                    "description": "Position description"
                }
            ]
        }
    ],
    "total_positions": number
}

Create logical zones based on wine types and organize positions within each zone."""
                    },
                    {
                        "role": "user",
                        "content": f"Set up my wine storage based on this description: {description}"
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=1000
            )
            
            # Parse the JSON response with robust error handling
            response_text = response.choices[0].message.content
            
            # Clean up the response
            response_text = response_text.strip()
            
            # Handle markdown code blocks
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Try multiple parsing strategies
            content = None
            
            # Strategy 1: Direct JSON parsing
            try:
                content = json.loads(response_text)
            except json.JSONDecodeError:
                # Strategy 2: Try to fix common issues
                try:
                    # Replace problematic characters that might break JSON
                    fixed_text = response_text
                    # Remove any trailing commas before closing braces/brackets
                    fixed_text = re.sub(r',(\s*[}\]])', r'\1', fixed_text)
                    # Fix unescaped newlines in strings
                    fixed_text = re.sub(r'"([^"]*)\n([^"]*)"', r'"\1\\n\2"', fixed_text)
                    content = json.loads(fixed_text)
                except json.JSONDecodeError:
                    # Strategy 3: Extract JSON object using regex
                    try:
                        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                        if json_match:
                            content = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        # Strategy 4: Create a fallback structure
                        # Extract description if possible
                        description = "Wine Storage"
                        try:
                            desc_match = re.search(r'"description"\s*:\s*"([^"]*)"', response_text)
                            if desc_match:
                                description = desc_match.group(1)
                        except:
                            pass
                        
                        # Create a simple fallback structure
                        content = {
                            "description": description,
                            "zones": [
                                {
                                    "name": "General Storage",
                                    "description": "General wine storage area",
                                    "positions": [
                                        {"identifier": "A1", "description": "Position A1"},
                                        {"identifier": "A2", "description": "Position A2"},
                                        {"identifier": "B1", "description": "Position B1"},
                                        {"identifier": "B2", "description": "Position B2"}
                                    ]
                                }
                            ],
                            "total_positions": 4
                        }
            
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