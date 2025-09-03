"""
DIVISION CLASSIFIER

GOAL => use vision models to create inputs for the remodelation/investment calculator 
"""

# == Import Libraries == 
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv
import os
import time
import logging
from datetime import datetime
import json
import asyncio
from typing import List, Dict, Any, Optional
import re
import requests

try:
    from src.idealista_data_manipulator import IdealistaDataManipulator
except ImportError:
    from idealista_data_manipulator import IdealistaDataManipulator

class DivisionClassifier:
    
    def __init__(self):

        self.logger = self._setup_logging()
        self.logger.info("Initializing DivisionClassifier...")

        self._load_environment_variables()

        self.client = OpenAI(api_key=self.openai_api_key)
        self.async_client = AsyncOpenAI(api_key=self.openai_api_key)

    # Logger setup
    def _setup_logging(self):
        """Setup logging configuration with both file and console handlers"""
        # Create logs directory if it doesn't exist
        #os.makedirs('logs', exist_ok=True)
        
        # Create a timestamp for the log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        #log_filename = f"logs/division_classifier_{timestamp}.log"
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                #logging.FileHandler(log_filename),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)

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

    filename = "idealista_listing_34219509.json"
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