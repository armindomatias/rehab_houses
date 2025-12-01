"""
Test file for vision-based batch grouping.

Approach:
1. Classify each image individually to get room type (one request per image)
2. For each room type, send ALL images in a single batch request
3. Ask the vision model to group similar images into divisions
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


class VisionBatchGrouper:
    """
    Test implementation of batch vision-based grouping.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.async_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    async def _classify_room_type(
        self,
        image_url: str,
        description: str,
        semaphore: asyncio.Semaphore,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Classify a single image to get room type.
        
        Returns:
            {"room_type": "bedroom", "confidence": 0.9}
        """
        async with semaphore:
            description_text = f"\nImage description: {description}" if description else ""
            
            prompt = f"""Classify this real estate photo. Return ONLY the room_type.

                room_type? kitchen/bathroom/living_room/bedroom/hallway/views/house_plan/common_areas/unknown

                Return JSON format:
                {{
                    "room_type": "bedroom",
                    "confidence": 0.9
                }}

                {description_text}
            """
            
            for attempt in range(max_retries):
                try:
                    response = await self.async_client.chat.completions.create(
                        model="gpt-4.1-mini",
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
                        response_format={"type": "json_object"}
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
                    
                    room_type = data.get("room_type", "unknown").lower()
                    confidence = float(data.get("confidence", 0.8))
                    
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
                        "confidence": confidence
                    }
                    
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Failed to parse JSON response: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1)
                        continue
                    return {"room_type": "unknown", "confidence": 0.0}
                    
                except Exception as e:
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
                                f"Rate limit hit (attempt {attempt + 1}/{max_retries}). "
                                f"Waiting {wait_time}s..."
                            )
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            self.logger.error(f"Rate limit exceeded after {max_retries} attempts")
                            return {"room_type": "unknown", "confidence": 0.0}
                    else:
                        self.logger.warning(f"Classification failed: {e}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(1)
                            continue
                        return {"room_type": "unknown", "confidence": 0.0}
            
            return {"room_type": "unknown", "confidence": 0.0}
    
    async def _group_images_by_vision(
        self,
        images: List[Dict[str, Any]],
        room_type: str,
        max_retries: int = 3
    ) -> List[List[int]]:
        """
        Send all images of a room type to vision model and ask it to group them.
        
        Args:
            images: List of image dicts with 'url' and 'gallery_index'
            room_type: Type of room (bedroom, kitchen, etc.)
        
        Returns:
            List of groups, where each group is a list of gallery_indices
            Example: [[0, 1, 2], [5, 6]] means images 0,1,2 are one division, 5,6 are another
        """
        if len(images) == 0:
            return []
        if len(images) == 1:
            return [[images[0]['gallery_index']]]
        
        # Build prompt with all image URLs
        image_contents = []
        image_indices = []
        
        for img in images:
            image_contents.append({
                "type": "image_url",
                "image_url": {"url": img['url']}
            })
            image_indices.append(img['gallery_index'])
        
        prompt = f"""You are analyzing {len(images)} photos of a {room_type} from a real estate listing.

These photos may show:
- The SAME physical room from different angles (should be grouped together)
- DIFFERENT physical rooms of the same type (should be in separate groups)

For example, if this is a T3 apartment with 3 bedrooms, you might see:
- 4-5 photos of bedroom 1 (different angles) -> Group 1
- 4-5 photos of bedroom 2 (different angles) -> Group 2  
- 4-5 photos of bedroom 3 (different angles) -> Group 3

Your task: Group the images into divisions where each division represents one physical room.

Look for:
- Same furniture, decorations, wall colors, floor patterns
- Same room layout and architectural features
- Similar lighting and window styles

Return JSON format:
{{
    "divisions": [
        {{
            "division_id": "division_1",
            "image_indices": [0, 1, 2, 3]
        }},
        {{
            "division_id": "division_2", 
            "image_indices": [4, 5, 6]
        }}
    ]
}}

The image_indices should correspond to the order you received the images (0 = first image, 1 = second, etc.).
Each image should appear in exactly one division.
"""
        
        for attempt in range(max_retries):
            try:
                # Combine text prompt with all images
                content = [{"type": "text", "text": prompt}] + image_contents
                
                response = await self.async_client.chat.completions.create(
                    model="gpt-4o",  # Use more capable model for complex multi-image analysis
                    messages=[
                        {
                            "role": "user",
                            "content": content
                        }
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=2000  # Allow longer responses for multiple divisions
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
                divisions = data.get("divisions", [])
                
                # Convert image indices back to gallery indices
                result = []
                for div in divisions:
                    div_indices = div.get("image_indices", [])
                    # Map back to actual gallery indices
                    gallery_indices = [image_indices[i] for i in div_indices if 0 <= i < len(image_indices)]
                    if gallery_indices:
                        result.append(gallery_indices)
                
                # Validate: all images should be in exactly one division
                all_grouped = set()
                for group in result:
                    all_grouped.update(group)
                
                # Check if any images are missing
                all_expected = set(image_indices)
                missing = all_expected - all_grouped
                if missing:
                    self.logger.warning(
                        f"Some images not grouped for {room_type}: {missing}. "
                        f"Creating individual divisions for them."
                    )
                    for idx in missing:
                        result.append([idx])
                
                # Check for duplicates
                duplicates = []
                seen = set()
                for group in result:
                    for idx in group:
                        if idx in seen:
                            duplicates.append(idx)
                        seen.add(idx)
                
                if duplicates:
                    self.logger.warning(f"Duplicate image indices found: {duplicates}")
                
                return result
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse JSON response for {room_type}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                    continue
                # Fallback: each image in its own division
                return [[img['gallery_index']] for img in images]
                
            except Exception as e:
                is_rate_limit = (
                    (RateLimitError and isinstance(e, RateLimitError)) or
                    '429' in str(e) or
                    'rate_limit' in str(e).lower() or
                    'Rate limit' in str(e) or
                    (hasattr(e, 'status_code') and e.status_code == 429)
                )
                
                if is_rate_limit:
                    wait_time = min((2 ** attempt) * 5, 60)  # Longer waits for batch requests
                    if attempt < max_retries - 1:
                        self.logger.warning(
                            f"Rate limit hit for {room_type} grouping (attempt {attempt + 1}/{max_retries}). "
                            f"Waiting {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        self.logger.error(f"Rate limit exceeded for {room_type}")
                        # Fallback: each image in its own division
                        return [[img['gallery_index']] for img in images]
                else:
                    self.logger.warning(f"Grouping failed for {room_type}: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
                        continue
                    # Fallback: each image in its own division
                    return [[img['gallery_index']] for img in images]
        
        # Final fallback
        return [[img['gallery_index']] for img in images]
    
    async def test_group_images(
        self,
        gallery_items: List[Dict[str, str]],
        listing_data: Dict[str, Any],
        listing_id: str,
        max_concurrency: int = 3
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Main method: Classify then batch-group images.
        """
        self.logger.info("=" * 60)
        self.logger.info("VISION BATCH-BASED GROUPING TEST")
        self.logger.info("=" * 60)
        
        # Step 1: Classify all images individually
        self.logger.info(f"Step 1: Classifying {len(gallery_items)} images...")
        
        semaphore = asyncio.Semaphore(max_concurrency)
        tasks = [
            self._classify_room_type(
                item['url'],
                item.get('description', ''),
                semaphore
            )
            for item in gallery_items
        ]
        
        classification_results = await asyncio.gather(*tasks)
        
        # Enrich gallery items with classifications
        enriched_items = []
        for gallery_item, class_result in zip(gallery_items, classification_results):
            enriched_item = {
                **gallery_item,
                "room_type": class_result["room_type"],
                "confidence": class_result["confidence"],
                "gallery_index": len(enriched_items)
            }
            enriched_items.append(enriched_item)
        
        self.logger.info("Classification complete")
        
        # Log distribution
        from collections import Counter
        room_type_counts = Counter(item['room_type'] for item in enriched_items)
        self.logger.info("\nRoom type distribution:")
        for room_type, count in sorted(room_type_counts.items()):
            self.logger.info(f"  {room_type}: {count} images")
        
        # Step 2: Group by room type
        grouped_by_type = {}
        for item in enriched_items:
            room_type = item.get('room_type', 'unknown')
            if room_type not in grouped_by_type:
                grouped_by_type[room_type] = []
            grouped_by_type[room_type].append(item)
        
        # Step 3: Extract expected counts
        expected_counts = {}
        characteristics = listing_data.get('characteristics', [])
        property_specs = listing_data.get('propertySpecs', {})
        
        # Extract bedrooms from T3, T4, etc.
        for char in characteristics:
            char_text = str(char).lower()
            match = re.search(r't(\d+)', char_text)
            if match:
                expected_counts['bedroom'] = int(match.group(1))
                break
        
        if 'bedroom' not in expected_counts and 'rooms' in property_specs:
            expected_counts['bedroom'] = property_specs['rooms']
        
        # Extract bathrooms
        for char in characteristics:
            char_text = str(char).lower()
            if 'casa de banho' in char_text or 'bathroom' in char_text:
                match = re.search(r'(\d+)\s*(?:casas?\s+de\s+banho|bathrooms?)', char_text)
                if match:
                    expected_counts['bathroom'] = int(match.group(1))
                    break
        
        expected_counts['kitchen'] = 1
        expected_counts['living_room'] = 1
        
        # Step 4: Batch-group each room type using vision model
        self.logger.info("\nStep 2: Batch-grouping images by room type...")
        result = {}
        
        for room_type, images in grouped_by_type.items():
            if room_type in ['unknown', 'views', 'house_plan']:
                self.logger.info(f"Skipping {room_type}: {len(images)} images")
                continue
            
            if len(images) == 0:
                continue
            
            self.logger.info(f"\nGrouping {room_type}: {len(images)} images")
            expected_count = expected_counts.get(room_type)
            if expected_count:
                self.logger.info(f"  Expected divisions: {expected_count}")
            
            # Send all images to vision model for grouping
            division_groups = await self._group_images_by_vision(images, room_type)
            
            # Format as divisions
            divisions = []
            for idx, group_indices in enumerate(division_groups, 1):
                # Get full image data for these indices
                group_images = [
                    img for img in images 
                    if img['gallery_index'] in group_indices
                ]
                
                division = {
                    "division_id": f"{room_type}_{idx}",
                    "room_type": room_type,
                    "images": [img['url'] for img in group_images],
                    "gallery_indices": group_indices,
                    "num_images": len(group_images)
                }
                divisions.append(division)
            
            result[room_type] = divisions
            
            self.logger.info(f"  Created {len(divisions)} divisions")
            for div in divisions:
                self.logger.info(f"    {div['division_id']}: {div['num_images']} images (indices: {div['gallery_indices']})")
        
        self.logger.info("=" * 60)
        self.logger.info(f"Grouping complete: {sum(len(v) for v in result.values())} divisions created")
        self.logger.info("=" * 60)
        
        # Save result
        output_dir = os.path.join(backend_dir, "data/image_grouper")
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, f"test_vision_batch_grouping_{listing_id}.json")
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Test result saved to {json_path}")
        
        return result


async def main():
    """Test the vision batch grouping."""
    grouper = VisionBatchGrouper()
    
    # Load test data
    listing_id = "34082358"
    manipulator = IdealistaDataManipulator(
        os.path.join(backend_dir, f"data/scraped_data/idealista_listing_{listing_id}.json")
    )
    gallery_items = manipulator.extract_gallery_urls()
    listing_data = manipulator.get_all_data()
    
    # Test grouping
    result = await grouper.test_group_images(
        gallery_items=gallery_items,
        listing_data=listing_data,
        listing_id=listing_id,
        max_concurrency=3
    )
    
    # Print results
    print("\n" + "=" * 60)
    print("VISION BATCH GROUPING RESULTS")
    print("=" * 60)
    for room_type, divisions in result.items():
        print(f"\n{room_type.upper()}: {len(divisions)} divisions")
        for div in divisions:
            print(f"  {div['division_id']}: {div['num_images']} images")
            print(f"    Indices: {div['gallery_indices']}")


if __name__ == "__main__":
    asyncio.run(main())

