"""
Example of how to integrate API tracking into a test.

This shows how to wrap your test functions to track:
- API usage (tokens, cost, model)
- Execution time
- Accuracy metrics
"""

import os
import sys
import asyncio
from typing import Dict, Any, List

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from src.idealista_scraper.idealista_data_manipulator import IdealistaDataManipulator
from src.utils import get_logger
from src.core.config import OPENAI_API_KEY
from openai import AsyncOpenAI
from src.utils.track_api_performance.track_api_usage import APITracker, save_test_run

logger = get_logger(__name__)


class TrackedOpenAIClient:
    """Wrapper around OpenAI client that tracks API usage"""
    
    def __init__(self, api_key: str, tracker: APITracker):
        self.client = AsyncOpenAI(api_key=api_key)
        self.tracker = tracker
    
    @property
    def chat(self):
        """Return tracked chat completions"""
        return TrackedChatCompletions(self.client, self.tracker)


class TrackedChatCompletions:
    """Tracked version of chat.completions"""
    
    def __init__(self, client: AsyncOpenAI, tracker: APITracker):
        self.client = client
        self.tracker = tracker
    
    async def create(self, **kwargs):
        """Tracked version of chat.completions.create"""
        response = await self.client.chat.completions.create(**kwargs)
        
        # Extract usage info
        if hasattr(response, 'usage') and response.usage:
            usage = response.usage
            model = kwargs.get('model', 'unknown')
            
            input_tokens = getattr(usage, 'prompt_tokens', 0) or 0
            output_tokens = getattr(usage, 'completion_tokens', 0) or 0
            
            self.tracker.track_api_call(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
        
        return response


async def example_tracked_test():
    """
    Example test function with tracking integrated.
    
    Replace your test logic here, but use TrackedOpenAIClient instead of AsyncOpenAI
    """
    listing_id = "34547389"
    
    # Initialize tracker
    tracker = APITracker(
        test_name="example_test",
        listing_id=listing_id
    )
    
    # Create tracked client
    tracked_client = TrackedOpenAIClient(OPENAI_API_KEY, tracker)
    
    # Load data
    manipulator = IdealistaDataManipulator(
        os.path.join(backend_dir, f"data/scraped_data/idealista_listing_{listing_id}.json")
    )
    gallery_items = manipulator.extract_gallery_urls()
    listing_data = manipulator.get_all_data()
    
    # Extract expected divisions
    expected_divisions = {}
    characteristics = listing_data.get('characteristics', [])
    property_specs = listing_data.get('propertySpecs', {})
    
    import re
    for char in characteristics:
        char_text = str(char).lower()
        match = re.search(r't(\d+)', char_text)
        if match:
            expected_divisions['bedroom'] = int(match.group(1))
            break
    
    if 'bedroom' not in expected_divisions and 'rooms' in property_specs:
        expected_divisions['bedroom'] = property_specs['rooms']
    
    for char in characteristics:
        char_text = str(char).lower()
        if 'casa de banho' in char_text or 'bathroom' in char_text:
            match = re.search(r'(\d+)\s*(?:casas?\s+de\s+banho|bathrooms?)', char_text)
            if match:
                expected_divisions['bathroom'] = int(match.group(1))
                break
    
    expected_divisions['kitchen'] = 1
    expected_divisions['living_room'] = 1
    
    # Your test logic here...
    # Use tracked_client instead of regular AsyncOpenAI client
    # Example:
    # response = await tracked_client.chat_completions_create(
    #     model="gpt-4o-mini",
    #     messages=[...]
    # )
    
    # Mock results for example
    results = {
        "bedroom": [
            {"division_id": "bedroom_1", "images": ["url1", "url2"]},
            {"division_id": "bedroom_2", "images": ["url3"]}
        ],
        "kitchen": [
            {"division_id": "kitchen_1", "images": ["url4"]}
        ]
    }
    
    # Save result file
    result_file = os.path.join(
        backend_dir,
        "data/image_grouper",
        f"example_result_{listing_id}.json"
    )
    import json
    with open(result_file, "w") as f:
        json.dump(results, f, indent=2)
    
    # Finalize tracking
    test_run = tracker.finalize(
        results=results,
        expected_divisions=expected_divisions,
        gallery_items=gallery_items,
        listing_data=listing_data,
        result_file=result_file
    )
    
    # Save tracking data
    save_test_run(test_run)
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST RUN SUMMARY")
    print("=" * 60)
    print(f"Test: {test_run.test_name}")
    print(f"Listing: {test_run.listing_id}")
    print(f"Execution Time: {test_run.execution_time_seconds:.2f}s")
    print(f"Total Cost: ${test_run.total_cost:.4f}")
    print(f"Total Tokens: {test_run.total_input_tokens + test_run.total_output_tokens:,}")
    print(f"  Input: {test_run.total_input_tokens:,}")
    print(f"  Output: {test_run.total_output_tokens:,}")
    print(f"API Calls: {len(test_run.api_calls)}")
    print(f"\nAccuracy:")
    print(f"  Division Count Accuracy: {test_run.accuracy.division_count_accuracy:.1%}")
    print(f"  Room Type Accuracy: {test_run.accuracy.room_type_accuracy:.1%}")
    print(f"\nExpected Divisions: {test_run.accuracy.expected_divisions}")
    print(f"Actual Divisions: {test_run.accuracy.actual_divisions}")


if __name__ == "__main__":
    asyncio.run(example_tracked_test())

