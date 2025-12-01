"""
ROOM SIGNATURE EXTRACTOR

GOAL => Classify images and extract visual room signatures (distinctive features)
        that identify specific physical rooms.

Extracts:
- Room type (bedroom, kitchen, bathroom, etc.)
- Room signature (wall color, floor, furniture, distinctive elements, etc.)
"""

import os
import sys
import json
import asyncio
from typing import List, Dict, Any

# Add the backend directory to the Python path so we can import src modules
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from src.utils import get_logger
from src.core.config import OPENAI_API_KEY
from openai import AsyncOpenAI

try:
    from openai import RateLimitError
except ImportError:
    # Fallback for different OpenAI library versions
    RateLimitError = None


class RoomSignatureExtractor:
    """
    Extracts room type and visual signatures from images using vision API.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.logger.info("Initializing RoomSignatureExtractor...")
        
        self.async_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        
        self.logger.info("RoomSignatureExtractor initialized successfully")
    
    async def extract_room_signature(
        self,
        image_url: str,
        description: str = "",
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Extract room type AND distinctive visual features (room signature).
        
        Args:
            image_url: URL of the image to analyze
            description: Optional description of the image
            max_retries: Maximum number of retry attempts
        
        Returns:
            {
                "room_type": "bedroom",
                "confidence": 0.9,
                "room_signature": {
                    "wall_color": "white",
                    "floor_type": "wood",
                    "furniture_style": "modern",
                    "distinctive_elements": ["blue curtains", "wooden bed frame"],
                    "color_scheme": "white and blue",
                    "window_style": "large window with white frame"
                }
            }
        """
        description_text = f"\nImage description: {description}" if description else ""
        
        prompt = f"""Analyze this real estate photo and provide BOTH:
            1. Room type classification
            2. Room signature: distinctive visual features that identify THIS SPECIFIC physical room

            For the room signature, describe distinctive features that would help identify if another photo shows the SAME physical room:
            - Wall color/pattern/texture
            - Floor type/color/material
            - Furniture style, colors, and distinctive pieces (bed sheets, curtains, lamps, etc.)
            - Window style/location/frame color
            - Decorative elements (paintings, plants, etc.)
            - Overall color scheme
            - Any unique architectural features or furniture arrangements

            Return ONLY valid JSON format (no markdown, no code blocks):
            {{
                "room_type": "bedroom",
                "confidence": 0.9,
                "signature": {{
                    "wall_color": "white",
                    "floor_type": "wood",
                    "furniture_style": "modern",
                    "distinctive_elements": ["blue curtains", "wooden bed frame", "white lamp"],
                    "color_scheme": "white and blue",
                    "window_style": "large window with white frame",
                    "decorative_elements": ["plant on windowsill"]
                }}
            }}

            Valid room types: kitchen, bathroom, living_room, bedroom, hallway, views, house_plan, common_areas, unknown

            {description_text}
        """
        
        for attempt in range(max_retries):
            try:
                # Use standard OpenAI Chat Completions API with vision
                response = await self.async_client.chat.completions.create(
                    model="gpt-4.1-mini",  # Using vision-capable model
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": image_url}
                                }
                            ]
                        }
                    ],
                    response_format={"type": "json_object"}  # Force JSON response
                )
                
                # Parse JSON response
                response_text = response.choices[0].message.content
                
                # Try to extract JSON from markdown code blocks if present
                if "```json" in response_text:
                    start = response_text.find("```json") + 7
                    end = response_text.find("```", start)
                    response_text = response_text[start:end].strip()
                elif "```" in response_text:
                    start = response_text.find("```") + 3
                    end = response_text.find("```", start)
                    response_text = response_text[start:end].strip()
                
                data = json.loads(response_text)
                
                room_type = data.get("room_type", "unknown").lower()
                confidence = float(data.get("confidence", 0.8))
                signature = data.get("signature", {})
                
                # Validate room type
                valid_types = {
                    "kitchen", "bathroom", "living_room", "bedroom",
                    "hallway", "views", "house_plan", "common_areas", "unknown"
                }
                
                if room_type not in valid_types:
                    room_type = "unknown"
                    confidence = 0.3
                
                return {
                    "room_type": room_type,
                    "confidence": confidence,
                    "room_signature": signature
                }
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse JSON response for {image_url}: {e}")
                if attempt < max_retries - 1:
                    continue
                return {
                    "room_type": "unknown",
                    "confidence": 0.0,
                    "room_signature": {}
                }
                
            except Exception as e:
                # Check if it's a rate limit error (429)
                is_rate_limit = (
                    (RateLimitError and isinstance(e, RateLimitError)) or
                    '429' in str(e) or
                    'rate_limit' in str(e).lower() or
                    'Rate limit' in str(e) or
                    (hasattr(e, 'status_code') and e.status_code == 429)
                )
                
                if is_rate_limit:
                    wait_time = (2 ** attempt) + 1
                    if attempt < max_retries - 1:
                        self.logger.warning(
                            f"Rate limit hit for {image_url} (attempt {attempt + 1}/{max_retries}). "
                            f"Waiting {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        self.logger.error(f"Rate limit exceeded after {max_retries} attempts")
                        return {
                            "room_type": "unknown",
                            "confidence": 0.0,
                            "room_signature": {}
                        }
                else:
                    self.logger.warning(f"Vision extraction failed for {image_url}: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1)
                        continue
                    return {
                        "room_type": "unknown",
                        "confidence": 0.0,
                        "room_signature": {}
                    }
        
        return {
            "room_type": "unknown",
            "confidence": 0.0,
            "room_signature": {}
        }
    
    async def extract_signatures_batch(
        self,
        gallery_items: List[Dict[str, str]],
        max_concurrency: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Extract room signatures for a batch of images.
        
        Args:
            gallery_items: List of {"url": "...", "description": "..."}
            max_concurrency: Max concurrent vision API calls
        
        Returns:
            List of enriched items with room_type, confidence, and room_signature
        """
        self.logger.info(f"Extracting room signatures for {len(gallery_items)} images...")
        
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def extract_with_semaphore(item):
            async with semaphore:
                result = await self.extract_room_signature(
                    item['url'],
                    item.get('description', '')
                )
                return result
        
        tasks = [extract_with_semaphore(item) for item in gallery_items]
        signature_results = await asyncio.gather(*tasks)
        
        # Enrich gallery items with signatures
        enriched_items = []
        for gallery_item, sig_result in zip(gallery_items, signature_results):
            enriched_item = {
                **gallery_item,
                "room_type": sig_result["room_type"],
                "confidence": sig_result["confidence"],
                "room_signature": sig_result["room_signature"],
                "gallery_index": len(enriched_items)
            }
            enriched_items.append(enriched_item)
        
        self.logger.info("Room signature extraction complete")
        
        return enriched_items


# Example usage
if __name__ == "__main__":
    async def test():
        extractor = RoomSignatureExtractor()
        
        # Test with a single image
        test_item = {
            "url": "https://example.com/image.jpg",
            "description": "Living room with modern furniture"
        }
        
        result = await extractor.extract_room_signature(
            test_item["url"],
            test_item["description"]
        )
        
        print("\n" + "=" * 60)
        print("EXTRACTION RESULT")
        print("=" * 60)
        print(f"Room Type: {result['room_type']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Signature: {json.dumps(result['room_signature'], indent=2)}")
    
    asyncio.run(test())

