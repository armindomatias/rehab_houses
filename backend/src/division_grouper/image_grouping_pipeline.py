"""
IMAGE GROUPING PIPELINE

GOAL => Coordinate the full image grouping pipeline:
        1. Extract room signatures (classification)
        2. Group images by division (grouping)

This script orchestrates both steps to group images by division.
"""

import os
import sys
import asyncio
from typing import List, Dict, Any

# Add the backend directory to the Python path so we can import src modules
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from src.division_grouper.room_signature_extractor import RoomSignatureExtractor
from src.division_grouper.image_grouper import ImageGrouper
from src.utils import get_logger


class ImageGroupingPipeline:
    """
    Pipeline that coordinates image classification and grouping.
    """
    
    def __init__(self, max_concurrency: int = 3, signature_similarity_threshold: float = 0.5):
        """
        Initialize the pipeline.
        
        Args:
            max_concurrency: Max concurrent vision API calls for signature extraction
            signature_similarity_threshold: Signature similarity threshold for clustering
        """
        self.logger = get_logger(__name__)
        self.logger.info("Initializing ImageGroupingPipeline...")
        
        self.extractor = RoomSignatureExtractor()
        self.grouper = ImageGrouper()
        self.max_concurrency = max_concurrency
        self.signature_similarity_threshold = signature_similarity_threshold
        
        self.logger.info("ImageGroupingPipeline initialized successfully")
    
    async def process(
        self,
        gallery_items: List[Dict[str, str]],
        listing_data: Dict[str, Any],
        listing_id: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Process images through the full pipeline: extract signatures and group.
        
        Args:
            gallery_items: List of {"url": "...", "description": "..."}
            listing_data: Full listing data from Idealista
            listing_id: Listing ID
        
        Returns:
        {
            "bedroom": [
                {
                    "division_id": "bedroom_1",
                    "room_type": "bedroom",
                    "images": [img1, img2, img3, img4],
                    "gallery_indices": [5, 6, 7, 8],
                    "num_images": 4,
                    "source_items": [...]
                }
            ],
            "kitchen": [...],
            ...
        }
        """
        self.logger.info("=" * 60)
        self.logger.info("IMAGE GROUPING PIPELINE")
        self.logger.info("=" * 60)
        
        # Step 1: Extract room signatures
        self.logger.info("\n[STEP 1] Extracting room signatures...")
        enriched_items = await self.extractor.extract_signatures_batch(
            gallery_items,
            max_concurrency=self.max_concurrency
        )
        
        # Step 2: Group images by division
        self.logger.info("\n[STEP 2] Grouping images by division...")
        result = self.grouper.group_images(
            enriched_items=enriched_items,
            listing_data=listing_data,
            listing_id=listing_id,
            signature_similarity_threshold=self.signature_similarity_threshold
        )
        
        self.logger.info("\n" + "=" * 60)
        self.logger.info("PIPELINE COMPLETE")
        self.logger.info("=" * 60)
        
        return result


# Example usage
if __name__ == "__main__":
    from src.idealista_scraper.idealista_data_manipulator import IdealistaDataManipulator
    
    async def test():
        pipeline = ImageGroupingPipeline(
            max_concurrency=3,
            signature_similarity_threshold=0.5
        )
        
        # Load test data
        listing_id = "34547389"
        manipulator = IdealistaDataManipulator(
            f"data/scraped_data/idealista_listing_{listing_id}.json"
        )
        gallery_items = manipulator.extract_gallery_urls()
        listing_data = manipulator.get_all_data()
        
        # Process through pipeline
        result = await pipeline.process(
            gallery_items=gallery_items,
            listing_data=listing_data,
            listing_id=listing_id
        )
        
        # Print results
        print("\n" + "=" * 60)
        print("PIPELINE RESULTS")
        print("=" * 60)
        for room_type, divisions in result.items():
            print(f"\n{room_type.upper()}: {len(divisions)} divisions")
            for div in divisions:
                print(f"  {div['division_id']}: {div['num_images']} images")
                print(f"    Indices: {div['gallery_indices']}")
    
    asyncio.run(test())

