"""
IMAGE GROUPER

GOAL => Group images by division using room signatures to ensure all images 
        of the same physical room (4-5 images) are grouped together

Uses room signature-based grouping approach:
- Compares room signatures to identify same physical room
- Groups images into divisions based on signature similarity
"""

import os
import sys
import re
import json
from typing import List, Dict, Any, Optional

# Add the backend directory to the Python path so we can import src modules
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from src.utils import get_logger


class ImageGrouper:
    """
    Groups images by division using room signature-based approach:
    - Compares room signatures to identify same physical room
    - Groups images into divisions based on signature similarity
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.logger.info("Initializing ImageGrouper (signature-based)...")
        self.logger.info("ImageGrouper initialized successfully")
    
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
    
    def _extract_expected_counts(self, listing_data: Dict[str, Any]) -> Dict[str, int]:
        """
        Extract expected room counts from listing (T3 = 3 bedrooms, etc.)
        
        Args:
            listing_data: Listing data from Idealista (can be dict or list)
        
        Returns:
            {"bedroom": 3, "bathroom": 2, ...}
        """
        expected = {}
        
        # Handle both list and dict formats - recursively unwrap lists until we get a dict
        while isinstance(listing_data, list):
            if len(listing_data) > 0:
                # Extract the first element, which should be the listing dict
                listing_data = listing_data[0]
            else:
                # Empty list, return defaults
                expected['kitchen'] = 1
                expected['living_room'] = 1
                return expected
        
        # Ensure we have a dict at this point
        if not isinstance(listing_data, dict):
            # If it's not a dict, return defaults
            expected['kitchen'] = 1
            expected['living_room'] = 1
            return expected
        
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
    
    def group_images(
        self,
        enriched_items: List[Dict[str, Any]],
        listing_data: Dict[str, Any],
        listing_id: str,
        signature_similarity_threshold: float = 0.5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Main method: Group all images into divisions using room signatures.
        
        Args:
            enriched_items: List of items with room_type, confidence, and room_signature already extracted
            listing_data: Full listing data from Idealista
            listing_id: Listing ID
            signature_similarity_threshold: Signature similarity threshold for clustering
        
        Returns:
        {
            "bedroom": [
                {
                    "division_id": "bedroom_1",
                    "room_type": "bedroom",
                    "images": [img1, img2, img3, img4],  # All 4-5 images of bedroom1
                    "gallery_indices": [5, 6, 7, 8],
                    "num_images": 4,
                    "source_items": [...]  # Full enriched items for classification
                }
            ],
            "kitchen": [...],
            ...
        }
        """
        self.logger.info("=" * 60)
        self.logger.info("IMAGE GROUPING (SIGNATURE-BASED)")
        self.logger.info("=" * 60)
        
        # Step 1: Group by room type
        grouped_by_type = {}
        for item in enriched_items:
            room_type = item.get('room_type', 'unknown')
            if room_type not in grouped_by_type:
                grouped_by_type[room_type] = []
            grouped_by_type[room_type].append(item)
        
        # Log room type distribution
        self.logger.info("\nRoom type distribution:")
        for room_type, items in grouped_by_type.items():
            self.logger.info(f"  {room_type}: {len(items)} images")
        
        # Step 2: Extract expected counts
        expected_counts = self._extract_expected_counts(listing_data)
        
        # Step 3: Cluster within each room type using signatures
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
                    "source_items": cluster  # Keep full data for classification
                }
                divisions.append(division)
            
            result[room_type] = divisions
        
        self.logger.info("=" * 60)
        self.logger.info(f"Grouping complete: {sum(len(v) for v in result.values())} divisions created")
        self.logger.info("=" * 60)
        
        # Save result to json file in data/image_grouper folder for checking
        output_dir = os.path.join(os.path.dirname(__file__), "../../data/image_grouper")
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, f"image_grouping_result_{listing_id}.json")
        try:
            # Convert signatures to serializable format
            serializable_result = self._make_json_serializable(result)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(serializable_result, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Image grouping result saved to {json_path}")
        except Exception as e:
            self.logger.error(f"Could not save image grouping result: {e}")
        
        return result
    
    def _make_json_serializable(self, obj: Any) -> Any:
        """
        Recursively convert objects to JSON-serializable format.
        
        Args:
            obj: Object that may contain non-serializable objects
        
        Returns:
            Object with all values JSON-serializable
        """
        if isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            return str(obj)


# Example usage
if __name__ == "__main__":
    from src.idealista_scraper.idealista_data_manipulator import IdealistaDataManipulator
    from src.division_grouper.room_signature_extractor import RoomSignatureExtractor
    import asyncio
    
    async def test():
        # Load test data
        listing_id = "34547389"
        manipulator = IdealistaDataManipulator(
            f"data/scraped_data/idealista_listing_{listing_id}.json"
        )
        gallery_items = manipulator.extract_gallery_urls()
        listing_data = manipulator.get_all_data()
        
        # Step 1: Extract signatures
        extractor = RoomSignatureExtractor()
        enriched_items = await extractor.extract_signatures_batch(gallery_items)
        
        # Step 2: Group images
        grouper = ImageGrouper()
        result = grouper.group_images(
            enriched_items=enriched_items,
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
