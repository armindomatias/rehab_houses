"""
DIVISION CLASSIFIER

GOAL => use vision models to create inputs for the remodelation/investment calculator 
"""

# == Import Libraries == 
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv
import os
import time
from datetime import datetime
import json
import asyncio
from typing import List, Dict, Any, Optional
import re
import requests

from src.idealista_scraper.idealista_data_manipulator import IdealistaDataManipulator
from src.utils import get_logger

class DivisionClassifier:
    
    def __init__(self):

        self.logger = get_logger(__name__)
        self.logger.info("Initializing DivisionClassifier...")

        self._load_environment_variables()

        self.client = OpenAI(api_key=self.openai_api_key)
        self.async_client = AsyncOpenAI(api_key=self.openai_api_key)

    def _load_environment_variables(self):
        """Load and validate environment variables"""
        self.logger.info("Loading environment variables...")
        load_dotenv()

        self.openai_api_key = os.getenv("OPENAI_API_KEY")

        # Log environment variable status
        if self.openai_api_key:
            self.logger.info("OPENAI_API_KEY loaded successfully")
        else:
            self.logger.warning("OPENAI_API_KEY not found in environment variables")
        
    def _open_prompt(self):
        self.logger.info("Loading system prompt from file")
        try:
            with open("prompts/division_classifier.txt", "r", encoding="utf-8") as f:
                prompt = f.read()
            self.logger.debug(f"System prompt loaded, length: {len(prompt)} characters")

            return prompt
        except Exception as e:
            self.logger.error(f"Failed to load system prompt: {e}")
            raise

    # Request the classification of one image (sync)
    def request_classification(self, gallery_items: list):
        """Request a vision classification per division using idealista gallery items (sync).

        NOTE: This method keeps the original signature but only uses the first gallery item.
        Prefer using classify_images_concurrently for batches.
        """

        if not gallery_items:
            raise ValueError("gallery_items must contain at least one item")

        gallery_item = gallery_items[0]
        image_url = gallery_item['url']
        description = gallery_item.get('description', '')

        self.logger.info("Starting OpenAI request (sync)...")
        start_time = time.time()

        model = "gpt-4.1-mini"
        system_prompt = self._open_prompt()

        # Build content so the model echoes room_url in JSON
        description_text = f"\nImage description (likely in Portuguese from Portugal): {description}" if description else ""
        input_content = [
            {"type": "input_text", "text": f"room_url: {image_url}{description_text}\nReturn only the JSON, no prose.\n" + system_prompt},
            {"type": "input_image", "image_url": image_url},
        ]

        try:
            response = self.client.responses.create(
                model=model,
                # Why everything as user? 
                input=[{"role": "user", "content": input_content}],
            )

            elapsed_time = time.time() - start_time
            self.logger.info(f"OpenAI request completed in {elapsed_time:.2f} seconds")
            return response.output_text

        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error(f"OpenAI request failed after {elapsed_time:.2f} seconds: {str(e)}")
            raise

    async def _classify_one_async(self, gallery_item: Dict[str, str], model: str, semaphore: asyncio.Semaphore, max_retries: int = 3, backoff_base: float = 1.5) -> Optional[Dict[str, Any]]:
        """Classify a single image using the async client with retries and return parsed JSON."""
        image_url = gallery_item['url']
        description = gallery_item.get('description', '')
        
        system_prompt = self._open_prompt()
        
        # Include description in the prompt if available to help with classification
        description_text = f"\nImage description (likely in Portuguese from Portugal): {description}" if description else ""
        
        input_content = [
            {"type": "input_text", "text": f"room_url: {image_url}{description_text}\nReturn only the JSON, no prose.\n" + system_prompt},
            {"type": "input_image", "image_url": image_url},
        ]

        attempt = 0
        while attempt < max_retries:
            attempt += 1
            try:
                async with semaphore:
                    start_time = time.time()
                    response = await self.async_client.responses.create(
                        model=model,
                        input=[{"role": "user", "content": input_content}],
                    )
                    elapsed_time = time.time() - start_time
                    self.logger.info(f"Classified image in {elapsed_time:.2f}s: {image_url}")

                parsed = self._parse_json_safely(response.output_text)
                if parsed is None:
                    raise ValueError("Failed to parse JSON from model output")
                # Ensure room_url and description are present
                parsed.setdefault("room_url", image_url)
                if description:
                    parsed.setdefault("image_description", description)
                return parsed
            except Exception as e:
                wait_s = backoff_base ** attempt
                self.logger.warning(f"Attempt {attempt}/{max_retries} failed for {image_url}: {e}. Retrying in {wait_s:.1f}s...")
                await asyncio.sleep(wait_s)

        self.logger.error(f"All retries failed for image: {image_url}")
        return None

    def _parse_json_safely(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract and parse the first JSON object in text. Returns None if not found."""
        if not text:
            return None
        # Try direct parse first
        try:
            return json.loads(text)
        except Exception:
            pass
        # Fallback: extract the first {...} block
        try:
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                return json.loads(match.group(0))
        except Exception:
            return None
        return None

    async def classify_images_concurrently(
        self,
        gallery_items: List[Dict[str, str]],
        listing_id: str,
        output_jsonl_filename: Optional[str] = None,
        output_aggregated_filename: Optional[str] = None,
        max_concurrency: int = 5,
        model: str = "gpt-4.1-mini",
    ) -> Dict[str, Any]:
        """Classify many images concurrently and write results quickly.

        - Streams results to JSONL as they are produced (one JSON object per line)
        - Builds an aggregated structure keyed by room_type
        - Each gallery_item should contain 'url' and 'description' keys
        - Creates a separate folder for each listing

        Args:
            gallery_items: List of dictionaries with 'url' and 'description' keys
            listing_id: The listing ID to create a folder for
            output_jsonl_filename: Optional filename for JSONL output
            output_aggregated_filename: Optional filename for aggregated JSON output
            max_concurrency: Maximum number of concurrent requests
            model: OpenAI model to use for classification
        """

        if not gallery_items:
            return {}

        # Create listing-specific folder
        listing_folder = os.path.join("data", "image_analysis", listing_id)
        os.makedirs(listing_folder, exist_ok=True)
        
        jsonl_path = None
        if output_jsonl_filename:
            jsonl_path = os.path.join(listing_folder, output_jsonl_filename)
            # Truncate/create file
            with open(jsonl_path, "w", encoding="utf-8") as f:
                f.write("")

        semaphore = asyncio.Semaphore(max_concurrency)
        tasks = [self._classify_one_async(item, model, semaphore) for item in gallery_items]

        aggregated: Dict[str, List[Dict[str, Any]]] = {}
        completed = 0
        # Loop over tasks returning something if completed the previous task and then do other tasks such as saving data so no data is lost if something breaks (while other non completed are doing as well)
        for coro in asyncio.as_completed(tasks):
            result = await coro
            completed += 1
            if result is None:
                continue
            # Write to JSONL as we go
            if jsonl_path:
                with open(jsonl_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
            # Aggregate by room_type
            room_type = result.get("room_type", "unknown")
            aggregated.setdefault(room_type, []).append(result)
            if completed % 5 == 0:
                self.logger.info(f"Progress: {completed}/{len(gallery_items)} classified")

        # Save aggregated if requested
        if output_aggregated_filename:
            aggregated_path = os.path.join(listing_folder, output_aggregated_filename)
            with open(aggregated_path, "w", encoding="utf-8") as f:
                json.dump(aggregated, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Aggregated results saved to: {aggregated_path}")

        return aggregated

    async def _classify_division_async(
        self,
        division: Dict[str, Any],
        model: str,
        semaphore: asyncio.Semaphore,
        max_retries: int = 3,
        backoff_base: float = 1.5
    ) -> Optional[Dict[str, Any]]:
        """
        Classify a division (group of images representing one physical room).
        
        Args:
            division: Division dict with 'division_id', 'room_type', 'images' (list of URLs)
            model: Model name to use
            semaphore: Semaphore for concurrency control
            max_retries: Maximum retry attempts
            backoff_base: Backoff multiplier
        
        Returns:
            Classification result with division_id and all images included
        """
        division_id = division.get('division_id', 'unknown')
        room_type = division.get('room_type', 'unknown')
        image_urls = division.get('images', [])
        
        if not image_urls:
            self.logger.warning(f"Division {division_id} has no images, skipping")
            return None
        
        system_prompt = self._open_prompt()
        
        # Build prompt for multiple images of the same room
        images_text = "\n".join([f"Image {i+1}: {url}" for i, url in enumerate(image_urls)])
        prompt_text = f"""Analyze these {len(image_urls)} images of the SAME physical room (different angles/views).

Division ID: {division_id}
Room Type: {room_type}
Images:
{images_text}

These images show different angles/views of the same room. Analyze ALL images together to get a comprehensive assessment of the room. Consider all visible elements across all images.

Return only the JSON, no prose.
{system_prompt}"""
        
        # Build content with all images
        input_content = [{"type": "input_text", "text": prompt_text}]
        for img_url in image_urls:
            input_content.append({"type": "input_image", "image_url": img_url})
        
        attempt = 0
        while attempt < max_retries:
            attempt += 1
            try:
                async with semaphore:
                    start_time = time.time()
                    response = await self.async_client.responses.create(
                        model=model,
                        input=[{"role": "user", "content": input_content}],
                    )
                    elapsed_time = time.time() - start_time
                    self.logger.info(f"Classified division {division_id} ({len(image_urls)} images) in {elapsed_time:.2f}s")

                parsed = self._parse_json_safely(response.output_text)
                if parsed is None:
                    raise ValueError("Failed to parse JSON from model output")
                
                # Add division metadata
                parsed['division_id'] = division_id
                parsed['room_type'] = room_type
                parsed['images'] = image_urls  # Include all images in the division
                parsed['num_images'] = len(image_urls)
                
                return parsed
            except Exception as e:
                wait_s = backoff_base ** attempt
                self.logger.warning(
                    f"Attempt {attempt}/{max_retries} failed for division {division_id}: {e}. "
                    f"Retrying in {wait_s:.1f}s..."
                )
                await asyncio.sleep(wait_s)

        self.logger.error(f"All retries failed for division: {division_id}")
        return None

    async def classify_divisions_concurrently(
        self,
        image_grouping: Dict[str, List[Dict[str, Any]]],
        listing_id: str,
        output_jsonl_filename: Optional[str] = None,
        output_aggregated_filename: Optional[str] = None,
        max_concurrency: int = 5,
        model: str = "gpt-4.1-mini",
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Classify divisions (groups of images) concurrently.
        
        Uses the output from image_grouping where each division contains multiple images
        of the same physical room. Classifies each division as a whole.
        
        Args:
            image_grouping: Dict from ImageGrouper with structure:
                {
                    "bedroom": [
                        {
                            "division_id": "bedroom_1",
                            "room_type": "bedroom",
                            "images": [url1, url2, url3, ...],
                            ...
                        }
                    ],
                    ...
                }
            listing_id: The listing ID
            output_jsonl_filename: Optional filename for JSONL output
            output_aggregated_filename: Optional filename for aggregated JSON output
            max_concurrency: Maximum number of concurrent requests
            model: OpenAI model to use for classification
        
        Returns:
            Aggregated results organized by room_type, with each division containing
            its classification and all its images
        """
        if not image_grouping:
            self.logger.warning("image_grouping is empty, nothing to classify")
            return {}
        
        # Create listing-specific folder
        listing_folder = os.path.join("data", "image_analysis", listing_id)
        os.makedirs(listing_folder, exist_ok=True)
        
        jsonl_path = None
        if output_jsonl_filename:
            jsonl_path = os.path.join(listing_folder, output_jsonl_filename)
            with open(jsonl_path, "w", encoding="utf-8") as f:
                f.write("")
        
        # Flatten all divisions into a list
        all_divisions = []
        for room_type, divisions in image_grouping.items():
            if room_type in ["views", "house_plan", "common_areas", "unknown"]:
                continue
            all_divisions.extend(divisions)
        
        if not all_divisions:
            self.logger.warning("No divisions to classify")
            return {}
        
        self.logger.info(f"Classifying {len(all_divisions)} divisions with max_concurrency={max_concurrency}")
        
        semaphore = asyncio.Semaphore(max_concurrency)
        tasks = [self._classify_division_async(div, model, semaphore) for div in all_divisions]
        
        aggregated: Dict[str, List[Dict[str, Any]]] = {}
        completed = 0
        
        for coro in asyncio.as_completed(tasks):
            result = await coro
            completed += 1
            if result is None:
                continue
            
            # Write to JSONL as we go
            if jsonl_path:
                with open(jsonl_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
            
            # Aggregate by room_type
            room_type = result.get("room_type", "unknown")
            aggregated.setdefault(room_type, []).append(result)
            
            if completed % 3 == 0:
                self.logger.info(f"Progress: {completed}/{len(all_divisions)} divisions classified")
        
        # Save aggregated if requested
        if output_aggregated_filename:
            aggregated_path = os.path.join(listing_folder, output_aggregated_filename)
            with open(aggregated_path, "w", encoding="utf-8") as f:
                json.dump(aggregated, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Aggregated results saved to: {aggregated_path}")
        
        self.logger.info(f"Classification complete: {len(aggregated)} room types, {sum(len(v) for v in aggregated.values())} divisions")
        return aggregated

    # Save the classification data
    def save_classification_data(self, property_data: dict, listing_id: str, filename: str):
        """Save property data to JSON file in a listing-specific folder"""
        try:
            # Create listing-specific folder
            listing_folder = os.path.join("data", "image_analysis", listing_id)
            os.makedirs(listing_folder, exist_ok=True)
            
            filepath = os.path.join(listing_folder, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(property_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Data saved to: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to save data: {str(e)}")
            return None

# Main execution
if __name__ == "__main__":
    division_classifier = DivisionClassifier()

    filename = "idealista_listing_34458598.json"
    filepath = f"data/scraped_data/"

    manipulator = IdealistaDataManipulator(json_file_path=f"{filepath}{filename}")

    gallery_items = manipulator.extract_gallery_urls()

    # Derive base name for outputs
    base_name = os.path.splitext(os.path.basename(filename))[0]
    # Extract listing ID from filename (e.g., "34357924" from "idealista_listing_34357924")
    listing_id = base_name.replace("idealista_listing_", "")
    jsonl_name = f"{base_name}_classifications.jsonl"
    aggregated_name = f"{base_name}_classifications_aggregated.json"

    # Run concurrent classification
    aggregated = asyncio.run(
        division_classifier.classify_images_concurrently(
            gallery_items=gallery_items,
            listing_id=listing_id,
            output_jsonl_filename=jsonl_name,
            output_aggregated_filename=aggregated_name,
            max_concurrency=5,
        )
    )

    # Also save using existing saver for compatibility
    division_classifier.save_classification_data(
        property_data=aggregated,
        listing_id=listing_id,
        filename=f"{base_name}_classifications_compact.json",
    )