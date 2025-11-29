"""
IMAGE PRE-GROUPER

GOAL => Group images by division BEFORE classification to ensure all images 
        of the same physical room (4-5 images) are grouped together
"""

import os
import sys
import re
import json
import asyncio
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from io import BytesIO
from PIL import Image
import imagehash


# Add the backend directory to the Python path so we can import src modules
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from src.idealista_scraper.idealista_data_manipulator import IdealistaDataManipulator
from src.utils import get_logger

from src.core.config import OPENAI_API_KEY
from .config import DESCRIPTION_MAPPING, GENERIC_DESCRIPTIONS

from openai import AsyncOpenAI
try:
    from openai import RateLimitError
except ImportError:
    # Fallback for different OpenAI library versions
    RateLimitError = None


class ImageGrouper:
    """
    Pre-groups images by division using multiple signals:
    - Idealista descriptions (Portuguese)
    - Vision model pre-classification
    - Gallery order
    - Visual similarity (pHash)
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.logger.info("Initializing ImageGrouper...")
        
        self.async_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        
        # Portuguese to room type mapping
        self.description_mapping = DESCRIPTION_MAPPING
        
        # Generic descriptions that should be ignored -> should we make a big 
        self.generic_descriptions = GENERIC_DESCRIPTIONS
        
        self.logger.info("ImageGrouper initialized successfully")

    def _parse_portuguese_description(self, description: str) -> Optional[str]:
        """
        Parse Portuguese descriptions to room types.
        
        Args:
            description: Description from Idealista (e.g., "Quarto", "Sala", "Photo")
        
        Returns:
            room_type or None if generic/unknown
        """
        if not description:
            return None
        
        description_lower = description.lower().strip()
        
        # Check if generic
        if description_lower in self.generic_descriptions:
            return None
        
        # Check mapping
        for key, room_type in self.description_mapping.items():
            if key in description_lower:
                return room_type
        
        return None
    
    # === STEP 1: Concurrent Image Classification using vision model OpenAI ===
    async def _pre_classify_room_type_vision(
        self, 
        image_url: str, 
        description: str,
        semaphore: asyncio.Semaphore,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Quick vision model pass to detect room type with retry logic for rate limits.
        
        Args:
            image_url: URL of the image
            description: Description from Idealista (for context)
            semaphore: Semaphore for concurrency control
            max_retries: Maximum number of retries for rate limit errors
        
        Returns:
            {"room_type": "bedroom", "confidence": 0.9}
        """
        async with semaphore:
            description_text = f"\nImage description: {description}" if description else ""
        
            prompt = f"""Classify real estate photos. Return ONLY the room_type.
            
                room_type? kitchen/bathroom/living_room/bedroom/hallway/views/house_plan/common_areas/unknown

                {description_text}
            """
            
            for attempt in range(max_retries):
                try:
                    response = await self.async_client.responses.create(
                        model="gpt-4.1-mini",
                        input=[{
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": prompt},
                                {"type": "input_image", "image_url": image_url}
                            ]
                        }]
                    )
                    
                    # The OpenAI Vision model likely returns plain text, not a JSON object.
                    # Attempt to parse as JSON first, else just treat output as a string.
                    try:
                        data = json.loads(response.output_text)
                        room_type = data["room_type"].lower()
                    except (json.JSONDecodeError, KeyError, TypeError):
                        # Try to extract the room_type from plain text output
                        room_type = response.output_text.strip().split()[0].lower()

                    # Validate room type
                    valid_types = {
                        "kitchen", "bathroom", "living_room", "bedroom", 
                        "hallway", "views", "house_plan", "common_areas", "unknown"
                    }
                    
                    if room_type not in valid_types:
                        room_type = "unknown"
                    
                    return {
                        "room_type": room_type,
                        "confidence": 0.8 if room_type != "unknown" else 0.3
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
                        # Extract retry-after from error message if available
                        retry_after = self._extract_retry_after(str(e))
                        wait_time = retry_after if retry_after else (2 ** attempt) + 1  # Exponential backoff
                        
                        if attempt < max_retries - 1:
                            self.logger.warning(
                                f"Rate limit hit for {image_url} (attempt {attempt + 1}/{max_retries}). "
                                f"Waiting {wait_time}s before retry..."
                            )
                            await asyncio.sleep(wait_time)
                            continue  # Retry the request
                        else:
                            self.logger.error(f"Rate limit exceeded after {max_retries} attempts for {image_url}")
                            return {"room_type": "unknown", "confidence": 0.0}
                    else:
                        # Non-rate-limit error
                        self.logger.warning(f"Vision pre-classification failed for {image_url}: {e}")
                        return {"room_type": "unknown", "confidence": 0.0}
            
            # If we exhausted all retries without returning
            return {"room_type": "unknown", "confidence": 0.0}
    
    def _extract_retry_after(self, error_message: str) -> Optional[float]:
        """
        Extract retry-after time from OpenAI rate limit error message.
        
        Args:
            error_message: Error message string
        
        Returns:
            Retry-after time in seconds, or None if not found
        """
        # Look for "Please try again in Xms" or "Please try again in Xs"
        match = re.search(r'Please try again in (\d+)(ms|s)', error_message)
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            if unit == 'ms':
                return value / 1000.0  # Convert ms to seconds
            return value
        return None
    
    async def _pre_classify_all_images(
        self, 
        gallery_items: List[Dict[str, str]],
        max_concurrency: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Pre-classify all images concurrently.
        
        Args:
            gallery_items: List of {"url": "...", "description": "..."}
            max_concurrency: Maximum concurrent requests
        
        Returns:
            gallery_items with added "vision_room_type" and "vision_confidence"
        """
        self.logger.info(f"Pre-classifying {len(gallery_items)} images with vision model...")
        
        semaphore = asyncio.Semaphore(max_concurrency)
        tasks = [
            self._pre_classify_room_type_vision(
                item['url'], 
                item.get('description', ''),
                semaphore
            )
            for item in gallery_items
        ]
        
        vision_results = await asyncio.gather(*tasks)
        
        # Enrich gallery items with vision results
        enriched_items = []
        for gallery_item, vision_result in zip(gallery_items, vision_results):
            enriched_item = {
                **gallery_item,
                "vision_room_type": vision_result["room_type"],
                "vision_confidence": vision_result["confidence"],
                "gallery_index": len(enriched_items)  # Track original order
            }
            enriched_items.append(enriched_item)
        
        self.logger.info("Vision pre-classification complete")
        return enriched_items
    

    # === STEP 2: pHash enrichment classification -> diff distance between images ===
    def _download_image_bytes(self, url: str) -> Optional[bytes]:
        """Download image bytes for pHash computation"""
        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code == 200:
                return resp.content
            return None
        except Exception as e:
            self.logger.warning(f"Failed to download image {url}: {e}")
            return None
    
    def _compute_phash(self, image_bytes: bytes) -> Optional[imagehash.ImageHash]:
        """Compute perceptual hash for visual similarity"""
        try:
            with Image.open(BytesIO(image_bytes)) as im:
                im = im.convert("RGB")
                return imagehash.phash(im)
        except Exception as e:
            self.logger.warning(f"Error computing pHash: {e}")
            return None
    
    def _enrich_with_phash(self, enriched_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Add pHash to enriched items for visual similarity comparison.
        
        Args:
            enriched_items: Items with vision classification
        
        Returns:
            Items with added "phash" field
        """
        self.logger.info("Computing visual similarity hashes (pHash)...")
        
        for item in enriched_items:
            image_url = item['url']
            img_bytes = self._download_image_bytes(image_url)
            if img_bytes:
                phash = self._compute_phash(img_bytes)
                item['phash'] = phash
            else:
                item['phash'] = None
        
        self.logger.info("Visual similarity hashes computed")
        return enriched_items
    

    # === STEP 3: Final decision on room type -> comparison description_listing & vision_model_output ===
    def _determine_room_type(self, item: Dict[str, Any]) -> tuple[str, float]:
        """
        Determine room type using description + vision fusion.
        
        Args:
            item: Enriched item with description, vision_room_type, etc.
        
        Returns:
            (room_type, confidence)
        """
        description = item.get('description', '')
        desc_room_type = self._parse_portuguese_description(description)
        vision_room_type = item.get('vision_room_type', 'unknown')
        vision_confidence = item.get('vision_confidence', 0.0)
        
        # If description is specific and valid (not generic/None)
        if desc_room_type:
            # If vision agrees, high confidence
            if vision_room_type == desc_room_type:
                return (desc_room_type, 0.95)
            # If vision disagrees, use vision (more reliable)
            elif vision_room_type != 'unknown':
                return (vision_room_type, 0.85)
            # If vision is unknown, trust description
            else:
                return (desc_room_type, 0.75)
        
        # Description is generic/unknown, use vision
        if vision_room_type != 'unknown':
            return (vision_room_type, vision_confidence)
        
        return ('unknown', 0.0)
    
    def _group_by_room_type(
        self, 
        enriched_items: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group images by room type using description + vision signals.
        
        Args:
            enriched_items: Items with vision classification and pHash
        
        Returns:
            {"bedroom": [img1, img2, ...], "kitchen": [img3, ...]}
        """
        self.logger.info("Grouping images by room type...")
        
        grouped = {}
        
        for item in enriched_items:
            room_type, confidence = self._determine_room_type(item)
            
            # Add confidence to item
            item['final_room_type'] = room_type
            item['room_type_confidence'] = confidence
            
            if room_type not in grouped:
                grouped[room_type] = []
            grouped[room_type].append(item)
        
        # Log grouping results
        for room_type, items in grouped.items():
            self.logger.info(f"  {room_type}: {len(items)} images")
        
        return grouped
    
    
    # === STEP 4: Division count expected -> How many bathrooms/rooms ===
    def _extract_expected_counts(self, listing_data: Dict[str, Any]) -> Dict[str, int]:
        """
        Extract expected room counts from listing (T3 = 3 bedrooms, etc.)
        
        Args:
            listing_data: Listing data from Idealista
        
        Returns:
            {"bedroom": 3, "bathroom": 2, ...}
        """
        expected = {}
        
        # Get from characteristics
        characteristics = listing_data.get('characteristics', [])
        property_specs = listing_data.get('propertySpecs', {})
        
        # Extract bedrooms from T3, T4, etc.
        for char in characteristics:
            char_text = str(char).lower()
            match = re.search(r't(\d+)', char_text)
            if match:
                expected['bedroom'] = int(match.group(1))
                break
        
        # Extract bedrooms from propertySpecs
        if 'bedroom' not in expected and 'rooms' in property_specs:
            expected['bedroom'] = property_specs['rooms']
        
        # Extract bathrooms
        for char in characteristics:
            char_text = str(char).lower()
            if 'casa de banho' in char_text or 'bathroom' in char_text:
                match = re.search(r'(\d+)\s*(?:casas?\s+de\s+banho|bathrooms?)', char_text) # the ? makes the char before optional
                if match:
                    expected['bathroom'] = int(match.group(1))
                    break
        
        # Single rooms
        expected['kitchen'] = 1
        expected['living_room'] = 1
        
        return expected


    # === STEP 5:  ===
    def _phash_distance(
        self, 
        phash1: Optional[imagehash.ImageHash], 
        phash2: Optional[imagehash.ImageHash]
    ) -> int:
        """Calculate pHash distance"""
        if phash1 is None or phash2 is None:
            return 999  # Very far if missing
        return phash1 - phash2
    
    def _cluster_within_room_type(
        self,
        room_type: str,
        images: List[Dict[str, Any]],
        expected_count: Optional[int] = None,
        phash_threshold: int = 15
    ) -> List[List[Dict[str, Any]]]:
        """
        Cluster images of same room type into divisions.
        Goal: Group all images of same physical room together (4-5 images per room).
        
        Strategy:
        1. Use gallery order (adjacent images = likely same room)
        2. Use visual similarity (pHash) for non-adjacent images
        3. Respect expected counts (T3 = 3 bedrooms)
        
        Args:
            room_type: Type of room (bedroom, kitchen, etc.)
            images: List of images of this room type
            expected_count: Expected number of divisions (e.g., 3 for T3 bedrooms)
            phash_threshold: pHash distance threshold for similarity
        
        Returns:
            List of clusters, each cluster is a list of images (one division)
        """
        if not images:
            return []
        
        # Sort by gallery order
        images.sort(key=lambda x: x.get('gallery_index', 9999))
        
        clusters: List[List[Dict[str, Any]]] = []
        current_cluster: List[Dict[str, Any]] = []
        
        for i, image in enumerate(images):
            if not current_cluster:
                # Start new cluster
                current_cluster = [image]
                continue
            
            # Check if should add to current cluster
            last_image = current_cluster[-1]
            last_index = last_image.get('gallery_index', 0)
            current_index = image.get('gallery_index', 0)
            
            # Check adjacency (within 2 positions = likely same room)
            is_adjacent = abs(current_index - last_index) <= 2
            
            # Check visual similarity (through distance of pHashes)
            phash_dist = self._phash_distance(
                last_image.get('phash'),
                image.get('phash')
            )
            is_similar = phash_dist <= phash_threshold
            
            # Add to current cluster if:
            # - Adjacent AND same type, OR
            # - Not adjacent BUT visually similar (same room, different angle)
            if is_adjacent or is_similar:
                current_cluster.append(image)
            else:
                # Start new cluster
                clusters.append(current_cluster)
                current_cluster = [image]
        
        # Add last cluster
        if current_cluster:
            clusters.append(current_cluster)
        
        # Apply expected count constraint
        if expected_count is not None and len(clusters) > expected_count:
            # Keep largest clusters (most images = most representative)
            clusters.sort(key=len, reverse=True)
            clusters = clusters[:expected_count]
            self.logger.info(
                f"  Capped {room_type} from {len(clusters) + (len(clusters) - expected_count)} "
                f"to {expected_count} divisions"
            )
        
        self.logger.info(
            f"  Created {len(clusters)} divisions for {room_type} "
            f"(avg {sum(len(c) for c in clusters) / len(clusters):.1f} images per division)"
        )
        
        return clusters
    
    
    async def group_images(
        self,
        gallery_items: List[Dict[str, str]],
        listing_data: Dict[str, Any],
        listing_id: str,
        max_concurrency: int = 3,
        phash_threshold: int = 15
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Main method: Group all images into divisions.
        
        Args:
            gallery_items: List of {"url": "...", "description": "..."}
            listing_data: Full listing data from Idealista
            listing_id: Listing ID
            max_concurrency: Max concurrent vision API calls
            phash_threshold: pHash distance threshold for similarity
        
        Returns:
        {
            "bedroom": [
                {
                    "division_id": "bedroom_1",
                    "room_type": "bedroom",
                    "images": [img1, img2, img3, img4],  # All 4-5 images of bedroom1
                    "gallery_indices": [5, 6, 7, 8]
                }
            ],
            "kitchen": [...],
            ...
        }
        """
        self.logger.info("=" * 60)
        self.logger.info("IMAGE PRE-GROUPING")
        self.logger.info("=" * 60)
        
        # Step 1: Pre-classify all images with vision model (concurrent)
        enriched_items = await self._pre_classify_all_images(
            gallery_items, 
            max_concurrency=max_concurrency
        )
        
        # Step 2: Enrich with pHash for visual similarity
        enriched_items = self._enrich_with_phash(enriched_items)
        
        # Step 3: Group by room type (description + vision fusion)
        grouped_by_type = self._group_by_room_type(enriched_items)
        
        # Step 4: Extract expected division counts 
        expected_counts = self._extract_expected_counts(listing_data)
        
        # Step 5: Cluster within each room type (order + similarity)
        result = {}
        for room_type, images in grouped_by_type.items():
            if room_type == 'unknown' or room_type == 'views' or room_type == 'house_plan':
                # Skip unknown/views/plans - they don't need divisions
                continue
            
            expected_count = expected_counts.get(room_type)
            clusters = self._cluster_within_room_type(
                room_type=room_type,
                images=images,
                expected_count=expected_count,
                phash_threshold=phash_threshold
            )
            
            # Format clusters as divisions
            divisions = []
            for idx, cluster in enumerate(clusters, 1):
                division = {
                    "division_id": f"{room_type}_{idx}",
                    "room_type": room_type,
                    "images": [img['url'] for img in cluster],
                    "gallery_indices": [img.get('gallery_index', 0) for img in cluster],
                    "num_images": len(cluster),
                    "source_items": cluster  # Keep full data for classification
                }
                divisions.append(division)
            
            result[room_type] = divisions
        
        self.logger.info("=" * 60)
        self.logger.info(f"Pre-grouping complete: {sum(len(v) for v in result.values())} divisions created")
        self.logger.info("=" * 60)

        # === Save result to json file in data/image_grouper folder for checking ===
        output_dir = os.path.join(os.path.dirname(__file__), "../../data/image_grouper")
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, f"image_grouping_result_{listing_id}.json")
        try:
            # Convert ImageHash objects to strings for JSON serialization
            serializable_result = self._make_json_serializable(result)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(serializable_result, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Image grouping result saved to {json_path}")
        except Exception as e:
            self.logger.error(f"Could not save image grouping result: {e}")

        return result
    
    def _make_json_serializable(self, obj: Any) -> Any:
        """
        Recursively convert ImageHash objects to strings for JSON serialization.
        
        Args:
            obj: Object that may contain ImageHash objects
        
        Returns:
            Object with ImageHash objects converted to strings
        """
        if isinstance(obj, imagehash.ImageHash):
            return str(obj)
        elif isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        else:
            return obj


# Example usage
if __name__ == "__main__":
    
    async def test():
        grouper = ImageGrouper()
        
        # Load test data
        listing_id = "34547389"
        manipulator = IdealistaDataManipulator(
            f"data/scraped_data/idealista_listing_{listing_id}.json"
        )
        gallery_items = manipulator.extract_gallery_urls()
        listing_data = manipulator.get_all_data()
        
        # Group images
        result = await grouper.group_images(
            gallery_items=gallery_items,
            listing_data=listing_data,
            listing_id=listing_id
        )
        
        # Print results
        print("\n" + "=" * 60)
        print("GROUPING RESULTS")
        print("=" * 60)
        for room_type, divisions in result.items():
            print(f"\n{room_type.upper()}: {len(divisions)} divisions")
            for div in divisions:
                print(f"  {div['division_id']}: {div['num_images']} images")
                print(f"    Indices: {div['gallery_indices']}")
    
    asyncio.run(test())

