"""
Test file for room signature-based image grouping.

This tests the concept of extracting visual room signatures from images
and using them to group images of the same physical room.
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


class RoomSignatureGrouper:
    """
    Test implementation of room signature-based grouping.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.async_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    async def _extract_room_signature_vision(
        self,
        image_url: str,
        description: str,
        semaphore: asyncio.Semaphore,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Extract room type AND distinctive visual features (room signature).
        
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
        async with semaphore:
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
                    # Check if it's a rate limit error
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
    
    def _compare_room_signatures(
        self,
        sig1: Dict[str, Any],
        sig2: Dict[str, Any]
    ) -> float:
        """
        Compare two room signatures and return similarity score (0-1).
        Higher score = more likely same physical room.
        """
        if not sig1 or not sig2:
            return 0.0
        
        score = 0.0
        total_weight = 0.0
        
        # High weight: distinctive elements (curtains, furniture, etc.) - most reliable
        if "distinctive_elements" in sig1 and "distinctive_elements" in sig2:
            elems1 = set(str(e).lower() for e in sig1["distinctive_elements"])
            elems2 = set(str(e).lower() for e in sig2["distinctive_elements"])
            if elems1 or elems2:
                overlap = len(elems1 & elems2)
                union = len(elems1 | elems2)
                jaccard = overlap / union if union > 0 else 0
                score += jaccard * 0.4
                total_weight += 0.4
        
        # Medium weight: color scheme
        if "color_scheme" in sig1 and "color_scheme" in sig2:
            scheme1 = str(sig1["color_scheme"]).lower()
            scheme2 = str(sig2["color_scheme"]).lower()
            if scheme1 == scheme2:
                score += 0.25
            elif scheme1 and scheme2:
                # Partial match (e.g., "white and blue" vs "white blue")
                words1 = set(scheme1.split())
                words2 = set(scheme2.split())
                overlap = len(words1 & words2)
                union = len(words1 | words2)
                if union > 0:
                    score += (overlap / union) * 0.15
            total_weight += 0.25
        
        # Medium weight: wall and floor
        wall_match = (
            sig1.get("wall_color") and sig2.get("wall_color") and
            str(sig1["wall_color"]).lower() == str(sig2["wall_color"]).lower()
        )
        floor_match = (
            sig1.get("floor_type") and sig2.get("floor_type") and
            str(sig1["floor_type"]).lower() == str(sig2["floor_type"]).lower()
        )
        if wall_match:
            score += 0.15
        if floor_match:
            score += 0.15
        total_weight += 0.3
        
        # Low weight: window style
        if "window_style" in sig1 and "window_style" in sig2:
            window1 = str(sig1["window_style"]).lower()
            window2 = str(sig2["window_style"]).lower()
            if window1 == window2:
                score += 0.05
            total_weight += 0.05
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def _cluster_with_signatures(
        self,
        room_type: str,
        images: List[Dict[str, Any]],
        expected_count: Optional[int] = None,
        signature_similarity_threshold: float = 0.5
    ) -> List[List[Dict[str, Any]]]:
        """
        Cluster images of same room type using room signatures.
        
        Strategy:
        1. For each image, find the cluster with highest signature similarity
        2. If similarity >= threshold, add to that cluster
        3. Otherwise, check gallery adjacency as fallback
        4. If no match, start new cluster
        """
        if not images:
            return []
        
        # Sort by gallery order
        images.sort(key=lambda x: x.get('gallery_index', 9999))
        
        clusters: List[List[Dict[str, Any]]] = []
        
        for image in images:
            best_cluster_idx = None
            best_similarity = 0.0
            
            # Find best matching cluster using signature similarity
            for idx, cluster in enumerate(clusters):
                # Compare with all images in cluster (any match = same room)
                for cluster_img in cluster:
                    sig1 = image.get('room_signature', {})
                    sig2 = cluster_img.get('room_signature', {})
                    similarity = self._compare_room_signatures(sig1, sig2)
                    
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_cluster_idx = idx
            
            # Add to best cluster if similarity is high enough
            if best_cluster_idx is not None and best_similarity >= signature_similarity_threshold:
                clusters[best_cluster_idx].append(image)
                self.logger.debug(
                    f"  Added image {image.get('gallery_index')} to cluster {best_cluster_idx} "
                    f"(similarity: {best_similarity:.2f})"
                )
            else:
                # Start new cluster (no gallery proximity fallback)
                clusters.append([image])
                self.logger.debug(
                    f"  Started new cluster for image {image.get('gallery_index')} "
                    f"(best similarity: {best_similarity:.2f})"
                )
        
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
    
    async def test_group_images(
        self,
        gallery_items: List[Dict[str, str]],
        listing_data: Dict[str, Any],
        listing_id: str,
        max_concurrency: int = 3,
        signature_similarity_threshold: float = 0.5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Test method: Group images using room signatures.
        """
        self.logger.info("=" * 60)
        self.logger.info("ROOM SIGNATURE-BASED GROUPING TEST")
        self.logger.info("=" * 60)
        
        # Step 1: Extract room signatures for all images
        self.logger.info(f"Extracting room signatures for {len(gallery_items)} images...")
        
        semaphore = asyncio.Semaphore(max_concurrency)
        tasks = [
            self._extract_room_signature_vision(
                item['url'],
                item.get('description', ''),
                semaphore
            )
            for item in gallery_items
        ]
        
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
        
        # Step 4: Cluster within each room type using signatures
        result = {}
        for room_type, images in grouped_by_type.items():
            if room_type in ['unknown', 'views', 'house_plan']:
                continue
            
            expected_count = expected_counts.get(room_type)
            clusters = self._cluster_with_signatures(
                room_type=room_type,
                images=images,
                expected_count=expected_count,
                signature_similarity_threshold=signature_similarity_threshold
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
                    "signatures": [img.get('room_signature', {}) for img in cluster]  # For debugging
                }
                divisions.append(division)
            
            result[room_type] = divisions
        
        self.logger.info("=" * 60)
        self.logger.info(f"Grouping complete: {sum(len(v) for v in result.values())} divisions created")
        self.logger.info("=" * 60)
        
        # Save result
        output_dir = os.path.join(backend_dir, "data/image_grouper")
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, f"test_signature_grouping_{listing_id}.json")
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Test result saved to {json_path}")
        
        return result


async def main():
    """Test the room signature grouping."""
    grouper = RoomSignatureGrouper()
    
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
        max_concurrency=3,
        signature_similarity_threshold=0.5
    )
    
    # Print results
    print("\n" + "=" * 60)
    print("SIGNATURE-BASED GROUPING RESULTS")
    print("=" * 60)
    for room_type, divisions in result.items():
        print(f"\n{room_type.upper()}: {len(divisions)} divisions")
        for div in divisions:
            print(f"  {div['division_id']}: {div['num_images']} images")
            print(f"    Indices: {div['gallery_indices']}")
            # Show signature details for first image
            if div['signatures']:
                sig = div['signatures'][0]
                print(f"    Signature: {sig.get('color_scheme', 'N/A')}, "
                      f"elements: {sig.get('distinctive_elements', [])[:2]}")


if __name__ == "__main__":
    asyncio.run(main())

