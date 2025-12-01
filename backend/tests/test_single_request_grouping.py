"""
Test file for single-request vision grouping.

Approach:
- Send ALL images in ONE API request
- Ask the vision model to:
  1. Classify each image by room type
  2. Group similar images into divisions (same physical room)
"""

import os
import sys
import json
import re
import asyncio
from typing import List, Dict, Any, Optional

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from src.idealista_scraper.idealista_data_manipulator import IdealistaDataManipulator
from src.utils import get_logger
from src.core.config import OPENAI_API_KEY
from openai import AsyncOpenAI

try:
    from openai import RateLimitError
except ImportError:
    RateLimitError = None


class SingleRequestGrouper:
    """
    Test implementation of single-request vision-based grouping.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.async_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    async def _classify_and_group_all_images(
        self,
        gallery_items: List[Dict[str, str]],
        listing_data: Dict[str, Any],
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Send all images in one request and ask model to classify and group them.
        
        Returns:
            {
                "images": [
                    {
                        "index": 0,
                        "url": "...",
                        "room_type": "bedroom",
                        "division_id": "bedroom_1"
                    },
                    ...
                ],
                "divisions": {
                    "bedroom_1": [0, 1, 2, 3],
                    "bedroom_2": [4, 5, 6],
                    ...
                }
            }
        """
        # Build content with all images
        image_contents = []
        image_urls = []
        
        for idx, item in enumerate(gallery_items):
            image_contents.append({
                "type": "image_url",
                "image_url": {"url": item['url']}
            })
            image_urls.append({
                "index": idx,
                "url": item['url'],
                "description": item.get('description', '')
            })
        
        # Extract listing info for context
        characteristics = listing_data.get('characteristics', [])
        property_specs = listing_data.get('propertySpecs', {})
        
        # Extract expected counts
        expected_bedrooms = None
        expected_bathrooms = None
        
        for char in characteristics:
            char_text = str(char).lower()
            match = re.search(r't(\d+)', char_text)
            if match:
                expected_bedrooms = int(match.group(1))
                break
        
        if expected_bedrooms is None and 'rooms' in property_specs:
            expected_bedrooms = property_specs['rooms']
        
        for char in characteristics:
            char_text = str(char).lower()
            if 'casa de banho' in char_text or 'bathroom' in char_text:
                match = re.search(r'(\d+)\s*(?:casas?\s+de\s+banho|bathrooms?)', char_text)
                if match:
                    expected_bathrooms = int(match.group(1))
                    break
        
        context_info = ""
        if expected_bedrooms:
            context_info += f"\n- Expected bedrooms: {expected_bedrooms}"
        if expected_bathrooms:
            context_info += f"\n- Expected bathrooms: {expected_bathrooms}"
        
        prompt = f"""You are analyzing {len(gallery_items)} real estate photos from a single property listing.

Your task:
1. Classify each image by room type (kitchen, bathroom, living_room, bedroom, hallway, views, house_plan, common_areas, unknown)
2. Group images into divisions where each division represents ONE physical room

Important rules:
- Images of the SAME physical room (different angles) should be in the SAME division
- Images of DIFFERENT physical rooms (even if same type) should be in DIFFERENT divisions
- For example, if there are 3 bedrooms, you should create 3 separate bedroom divisions
- Each division typically has 3-5 images showing different angles of the same room

Look for visual similarities to identify same room:
- Same furniture, decorations, wall colors
- Same floor patterns, window styles
- Same room layout and architectural features
- Same lighting fixtures, curtains, etc.

{context_info}

Return JSON format:
{{
    "classifications": [
        {{
            "image_index": 0,
            "room_type": "bedroom",
            "confidence": 0.9
        }},
        {{
            "image_index": 1,
            "room_type": "bedroom",
            "confidence": 0.9
        }},
        ...
    ],
    "divisions": [
        {{
            "division_id": "bedroom_1",
            "room_type": "bedroom",
            "image_indices": [0, 1, 2, 3]
        }},
        {{
            "division_id": "bedroom_2",
            "room_type": "bedroom",
            "image_indices": [4, 5, 6]
        }},
        {{
            "division_id": "kitchen_1",
            "room_type": "kitchen",
            "image_indices": [7, 8]
        }},
        ...
    ]
}}

Requirements:
- Every image must be classified (have an entry in classifications)
- Every image must be in exactly one division (appear in exactly one division's image_indices)
- Division IDs should follow pattern: {{room_type}}_{{number}} (e.g., bedroom_1, kitchen_1)
- Group similar images together (same physical room)
"""
        
        for attempt in range(max_retries):
            try:
                # Combine text prompt with all images
                content = [{"type": "text", "text": prompt}] + image_contents
                
                self.logger.info(f"Sending {len(gallery_items)} images in single request...")
                
                response = await self.async_client.chat.completions.create(
                    model="gpt-4o",  # Use most capable model for complex multi-image analysis
                    messages=[
                        {
                            "role": "user",
                            "content": content
                        }
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=4000  # Allow longer responses for many images
                )
                
                response_text = response.choices[0].message.content
                
                # Extract JSON if wrapped in markdown
                if "```json" in response_text:
                    start = response_text.find("```json") + 7
                    end = response_text.find("```", start)
                    response_text = response_text[start:end].strip()
                elif "```" in response_text:
                    start = response_text.find("```") + 3
                    end = response_text.find("```", start)
                    response_text = response_text[start:end].strip()
                
                data = json.loads(response_text)
                
                # Validate response
                classifications = data.get("classifications", [])
                divisions = data.get("divisions", [])
                
                # Check all images are classified
                classified_indices = set(c.get("image_index") for c in classifications)
                expected_indices = set(range(len(gallery_items)))
                missing_classifications = expected_indices - classified_indices
                
                if missing_classifications:
                    self.logger.warning(
                        f"Missing classifications for indices: {missing_classifications}. "
                        f"Adding default classifications."
                    )
                    for idx in missing_classifications:
                        classifications.append({
                            "image_index": idx,
                            "room_type": "unknown",
                            "confidence": 0.0
                        })
                
                # Check all images are in divisions
                all_grouped = set()
                for div in divisions:
                    all_grouped.update(div.get("image_indices", []))
                
                missing_from_divisions = expected_indices - all_grouped
                if missing_from_divisions:
                    self.logger.warning(
                        f"Images not in any division: {missing_from_divisions}. "
                        f"Creating individual divisions for them."
                    )
                    for idx in missing_from_divisions:
                        # Get room type from classification
                        classification = next(
                            (c for c in classifications if c.get("image_index") == idx),
                            {"room_type": "unknown"}
                        )
                        room_type = classification.get("room_type", "unknown")
                        divisions.append({
                            "division_id": f"{room_type}_orphan_{idx}",
                            "room_type": room_type,
                            "image_indices": [idx]
                        })
                
                # Check for duplicates
                all_indices_in_divisions = []
                for div in divisions:
                    all_indices_in_divisions.extend(div.get("image_indices", []))
                
                duplicates = []
                seen = set()
                for idx in all_indices_in_divisions:
                    if idx in seen:
                        duplicates.append(idx)
                    seen.add(idx)
                
                if duplicates:
                    self.logger.warning(f"Duplicate image indices in divisions: {duplicates}")
                
                return {
                    "classifications": classifications,
                    "divisions": divisions,
                    "total_images": len(gallery_items)
                }
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse JSON response: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                    continue
                # Fallback: create one division per image
                return self._create_fallback_result(gallery_items)
                
            except Exception as e:
                is_rate_limit = (
                    (RateLimitError and isinstance(e, RateLimitError)) or
                    '429' in str(e) or
                    'rate_limit' in str(e).lower() or
                    'Rate limit' in str(e) or
                    (hasattr(e, 'status_code') and e.status_code == 429)
                )
                
                if is_rate_limit:
                    wait_time = min((2 ** attempt) * 10, 120)  # Longer waits for large requests
                    if attempt < max_retries - 1:
                        self.logger.warning(
                            f"Rate limit hit (attempt {attempt + 1}/{max_retries}). "
                            f"Waiting {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        self.logger.error(f"Rate limit exceeded after {max_retries} attempts")
                        return self._create_fallback_result(gallery_items)
                else:
                    self.logger.warning(f"Request failed: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
                        continue
                    return self._create_fallback_result(gallery_items)
        
        return self._create_fallback_result(gallery_items)
    
    def _create_fallback_result(self, gallery_items: List[Dict[str, str]]) -> Dict[str, Any]:
        """Create fallback result with one division per image."""
        classifications = []
        divisions = []
        
        for idx, item in enumerate(gallery_items):
            classifications.append({
                "image_index": idx,
                "room_type": "unknown",
                "confidence": 0.0
            })
            divisions.append({
                "division_id": f"unknown_{idx}",
                "room_type": "unknown",
                "image_indices": [idx]
            })
        
        return {
            "classifications": classifications,
            "divisions": divisions,
            "total_images": len(gallery_items)
        }
    
    async def test_group_images(
        self,
        gallery_items: List[Dict[str, str]],
        listing_data: Dict[str, Any],
        listing_id: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Main method: Single request to classify and group all images.
        """
        self.logger.info("=" * 60)
        self.logger.info("SINGLE-REQUEST VISION GROUPING TEST")
        self.logger.info("=" * 60)
        self.logger.info(f"Processing {len(gallery_items)} images in ONE request...")
        
        # Single request for all images
        result_data = await self._classify_and_group_all_images(
            gallery_items,
            listing_data
        )
        
        classifications = result_data["classifications"]
        divisions = result_data["divisions"]
        
        self.logger.info(f"\nReceived {len(classifications)} classifications")
        self.logger.info(f"Received {len(divisions)} divisions")
        
        # Log classification distribution
        from collections import Counter
        room_type_counts = Counter(c.get("room_type", "unknown") for c in classifications)
        self.logger.info("\nRoom type distribution:")
        for room_type, count in sorted(room_type_counts.items()):
            self.logger.info(f"  {room_type}: {count} images")
        
        # Format result by room type
        result = {}
        
        for div in divisions:
            room_type = div.get("room_type", "unknown")
            if room_type in ['unknown', 'views', 'house_plan']:
                continue
            
            if room_type not in result:
                result[room_type] = []
            
            # Get image URLs for this division
            image_indices = div.get("image_indices", [])
            division_images = []
            for idx in image_indices:
                if 0 <= idx < len(gallery_items):
                    division_images.append({
                        "url": gallery_items[idx]['url'],
                        "gallery_index": idx,
                        "description": gallery_items[idx].get('description', '')
                    })
            
            division_obj = {
                "division_id": div.get("division_id", f"{room_type}_unknown"),
                "room_type": room_type,
                "images": [img['url'] for img in division_images],
                "gallery_indices": [img['gallery_index'] for img in division_images],
                "num_images": len(division_images)
            }
            
            result[room_type].append(division_obj)
        
        # Log results
        self.logger.info("\n" + "=" * 60)
        self.logger.info("GROUPING RESULTS")
        self.logger.info("=" * 60)
        for room_type, divs in result.items():
            self.logger.info(f"\n{room_type.upper()}: {len(divs)} divisions")
            for div in divs:
                self.logger.info(
                    f"  {div['division_id']}: {div['num_images']} images "
                    f"(indices: {div['gallery_indices']})"
                )
        
        # Save full result with classifications
        output_dir = os.path.join(backend_dir, "data/image_grouper")
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, f"test_single_request_grouping_{listing_id}.json")
        
        full_result = {
            "result": result,
            "raw_response": {
                "classifications": classifications,
                "divisions": divisions,
                "total_images": len(gallery_items)
            }
        }
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(full_result, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"\nFull result saved to {json_path}")
        
        return result


async def main():
    """Test the single-request grouping."""
    grouper = SingleRequestGrouper()
    
    # Load test data
    listing_id = "34547389"
    manipulator = IdealistaDataManipulator(
        os.path.join(backend_dir, f"data/scraped_data/idealista_listing_{listing_id}.json")
    )
    gallery_items = manipulator.extract_gallery_urls()
    listing_data = manipulator.get_all_data()
    
    # Test grouping
    result = await grouper.test_group_images(
        gallery_items=gallery_items,
        listing_data=listing_data,
        listing_id=listing_id
    )
    
    # Print summary
    print("\n" + "=" * 60)
    print("SINGLE-REQUEST GROUPING RESULTS")
    print("=" * 60)
    for room_type, divisions in result.items():
        print(f"\n{room_type.upper()}: {len(divisions)} divisions")
        for div in divisions:
            print(f"  {div['division_id']}: {div['num_images']} images")
            print(f"    Indices: {div['gallery_indices']}")


if __name__ == "__main__":
    asyncio.run(main())

