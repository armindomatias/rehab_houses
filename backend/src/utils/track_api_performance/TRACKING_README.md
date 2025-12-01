# API Usage and Accuracy Tracking System

This system tracks API usage, costs, execution time, and accuracy metrics for your image grouping tests.

## Features

- **API Usage Tracking**: Model, input/output tokens, cost per call
- **Execution Time**: Total time for test run
- **Accuracy Metrics**: 
  - Room type classification accuracy
  - Division grouping accuracy (correct number of divisions)
  - Manual review fields for wrong decisions
- **Comparison Reports**: Compare multiple test runs side-by-side

## Quick Start

### 1. Integrate Tracking into Your Test

```python
from track_api_usage import APITracker, save_test_run, TrackedOpenAIClient

# Initialize tracker
tracker = APITracker(
    test_name="signature_grouping",  # Name your test
    listing_id="34547389"
)

# Use tracked client instead of regular OpenAI client
tracked_client = TrackedOpenAIClient(OPENAI_API_KEY, tracker)

# Your test code here...
# Use tracked_client.chat_completions_create() instead of client.chat.completions.create()

# At the end, finalize and save
test_run = tracker.finalize(
    results=your_results,
    expected_divisions=expected_divisions,
    gallery_items=gallery_items,
    listing_data=listing_data,
    result_file="path/to/result.json"
)

save_test_run(test_run)
```

### 2. View Comparison Report

```bash
cd backend
python -c "from tests.track_api_usage import create_comparison_report; create_comparison_report()"
```

Or run:
```bash
python tests/track_api_usage.py
```

## Output Files

### Individual Test Run
Saved as: `test_tracking_{test_name}_{listing_id}_{timestamp}.json`

Contains:
- Test metadata (name, listing ID, timestamps)
- Execution time
- All API calls with tokens and costs
- Total cost and token usage
- Accuracy metrics
- Link to result file

### Comparison Report
Saved as: `test_comparison_{timestamp}.json`

Contains:
- Summary of all test runs
- Side-by-side comparison
- Best performers by metric

## Accuracy Metrics

### Automatic Metrics

1. **Division Count Accuracy**: 
   - Compares expected vs actual number of divisions per room type
   - Example: Expected 3 bedrooms, got 3 = 100% for bedrooms

2. **Room Type Accuracy**: 
   - Currently placeholder (0%) - you fill manually
   - Compare classifications with ground truth

### Manual Review Fields

In the JSON file, you'll find:
- `wrong_room_classifications`: List of images classified incorrectly
- `wrong_divisions`: List of divisions that are wrong
- `notes`: Your manual notes

Fill these in to track specific errors.

## Example JSON Structure

```json
{
  "test_name": "signature_grouping",
  "listing_id": "34547389",
  "execution_time_seconds": 45.2,
  "total_cost": 0.0234,
  "total_input_tokens": 125000,
  "total_output_tokens": 15000,
  "api_calls": [
    {
      "model": "gpt-4o-mini",
      "input_tokens": 5000,
      "output_tokens": 500,
      "cost": 0.0008,
      "timestamp": "2024-11-29T12:00:00"
    }
  ],
  "accuracy": {
    "total_images": 25,
    "room_type_accuracy": 0.0,
    "division_count_accuracy": 0.75,
    "expected_divisions": {"bedroom": 3, "bathroom": 2},
    "actual_divisions": {"bedroom": 3, "bathroom": 2},
    "wrong_room_classifications": [],
    "wrong_divisions": [],
    "notes": ""
  }
}
```

## Model Pricing

Current pricing (update in `MODEL_PRICING` dict if needed):
- `gpt-4o`: $2.50/$10.00 per 1M tokens (input/output)
- `gpt-4o-mini`: $0.15/$0.60 per 1M tokens
- `gpt-4.1-mini`: $0.15/$0.60 per 1M tokens (assumed)

## Tips

1. **Name your tests clearly**: Use descriptive names like `signature_grouping`, `batch_grouping`, `single_request`

2. **Fill accuracy manually**: After reviewing results, update:
   - `wrong_room_classifications`: Add objects like `{"image_index": 5, "classified_as": "bedroom", "should_be": "living_room"}`
   - `wrong_divisions`: Add objects describing wrong groupings
   - `notes`: Add any observations

3. **Compare regularly**: Run comparison reports to see which approach works best

4. **Track multiple listings**: Test on different listings to see consistency

## Integration Checklist

- [ ] Import `APITracker` and `TrackedOpenAIClient`
- [ ] Initialize tracker at start of test
- [ ] Replace `AsyncOpenAI` with `TrackedOpenAIClient`
- [ ] Extract expected divisions from listing data
- [ ] Call `tracker.finalize()` at end
- [ ] Call `save_test_run()` to save tracking data
- [ ] Review and fill accuracy fields manually
- [ ] Run comparison report to analyze results

