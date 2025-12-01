# Tracking System: Complete Explanation

## 📐 How I Modeled It

### Design Philosophy

The system uses a **layered data structure** approach with three main components:

1. **Data Classes** (using `@dataclass`) - Immutable data structures
2. **Tracker Class** - Stateful tracking during test execution
3. **Utility Functions** - Save, load, and compare operations

### Data Model Hierarchy

```
TestRun (Top Level)
├── Metadata (test_name, listing_id, timestamps, execution_time)
├── API Usage Summary (total_tokens, total_cost)
├── API Calls (List of APIUsage objects)
│   ├── APIUsage #1
│   │   ├── model: "gpt-4o-mini"
│   │   ├── input_tokens: 5000
│   │   ├── output_tokens: 500
│   │   ├── timestamp: "2024-11-29T12:00:00"
│   │   └── cost: 0.0008 (calculated property)
│   └── APIUsage #2, #3, ...
└── AccuracyMetrics
    ├── Automatic metrics (division_count_accuracy)
    ├── Manual review fields (wrong_room_classifications, wrong_divisions)
    └── Expected vs Actual comparisons
```

### Key Design Decisions

#### 1. **Dataclasses for Type Safety**
```python
@dataclass
class APIUsage:
    model: str
    input_tokens: int
    output_tokens: int
    timestamp: str
    # cost is a @property (calculated, not stored)
```

**Why?** 
- Type hints for clarity
- Immutable structure prevents accidental modification
- Easy to convert to JSON
- Self-documenting code

#### 2. **Property for Cost Calculation**
```python
@property
def cost(self) -> float:
    # Calculates cost on-the-fly based on model pricing
```

**Why?**
- Cost depends on current pricing (may change)
- Don't store calculated values (single source of truth)
- Always up-to-date if pricing changes

#### 3. **Stateful Tracker Class**
```python
class APITracker:
    def __init__(self, test_name, listing_id):
        self.api_calls = []  # Accumulates during test
        self.start_time = time.time()  # Tracks execution
```

**Why?**
- Maintains state during test execution
- Easy to call `track_api_call()` multiple times
- Automatically calculates totals at the end

#### 4. **Separation of Concerns**
- **APITracker**: Collects data during execution
- **TestRun**: Final immutable snapshot
- **Utility functions**: Save/load/compare operations

---

## 🚀 How to Use It

### Step-by-Step Integration

#### Step 1: Import and Initialize

```python
from src.utils.track_api_performance.track_api_usage import (
    APITracker, 
    save_test_run,
    TrackedOpenAIClient
)

# At the start of your test function
tracker = APITracker(
    test_name="signature_grouping",  # Unique identifier
    listing_id="34547389"              # Which listing you're testing
)
```

**What happens:**
- Creates a new tracker instance
- Records start timestamp
- Initializes empty list for API calls

#### Step 2: Replace OpenAI Client

**Before:**
```python
self.async_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
response = await self.async_client.chat.completions.create(...)
```

**After:**
```python
# Option 1: Use TrackedOpenAIClient wrapper
tracked_client = TrackedOpenAIClient(OPENAI_API_KEY, tracker)
response = await tracked_client.chat.completions.create(...)

# Option 2: Manual tracking (if wrapper doesn't work)
response = await self.async_client.chat.completions.create(...)
# Then manually track:
tracker.track_api_call(
    model="gpt-4o-mini",
    input_tokens=response.usage.prompt_tokens,
    output_tokens=response.usage.completion_tokens
)
```

**What happens:**
- Every API call is automatically intercepted
- Usage info extracted from response
- Cost calculated based on model
- Added to tracker's `api_calls` list

#### Step 3: Extract Expected Divisions

```python
# From listing data, extract what you expect
expected_divisions = {
    "bedroom": 3,      # T3 = 3 bedrooms
    "bathroom": 2,     # 2 bathrooms
    "kitchen": 1,      # Always 1 kitchen
    "living_room": 1   # Always 1 living room
}
```

**Why?** Needed to calculate accuracy later.

#### Step 4: Run Your Test

```python
# Your normal test code here
results = await your_grouping_function(...)
```

#### Step 5: Finalize and Save

```python
# Save your results first
result_file = "data/image_grouper/test_result_34547389.json"
with open(result_file, "w") as f:
    json.dump(results, f)

# Finalize tracking (calculates everything)
test_run = tracker.finalize(
    results=results,                    # Your grouping results
    expected_divisions=expected_divisions,
    gallery_items=gallery_items,        # Original images
    listing_data=listing_data,           # Full listing data
    result_file=result_file             # Path to result JSON
)

# Save tracking data
save_test_run(test_run)
```

**What `finalize()` does:**
1. Calculates execution time (end - start)
2. Sums all tokens and costs
3. Calculates accuracy metrics
4. Creates immutable `TestRun` object

---

## 📊 Output Structure

### Individual Test Run JSON

**Filename:** `test_tracking_{test_name}_{listing_id}_{timestamp}.json`

**Full Structure:**

```json
{
  "test_name": "signature_grouping",
  "listing_id": "34547389",
  "start_time": "2024-11-29T12:00:00.123456",
  "end_time": "2024-11-29T12:00:45.789012",
  "execution_time_seconds": 45.665556,
  
  "api_calls": [
    {
      "model": "gpt-4o-mini",
      "input_tokens": 5234,
      "output_tokens": 487,
      "timestamp": "2024-11-29T12:00:01.234567",
      "cost": 0.000923
    },
    {
      "model": "gpt-4o-mini",
      "input_tokens": 5123,
      "output_tokens": 456,
      "timestamp": "2024-11-29T12:00:05.789012",
      "cost": 0.000901
    }
  ],
  
  "total_input_tokens": 125000,
  "total_output_tokens": 15000,
  "total_cost": 0.0234,
  
  "accuracy": {
    "total_images": 25,
    
    "room_type_correct": 0,
    "room_type_incorrect": 0,
    "room_type_accuracy": 0.0,
    
    "expected_divisions": {
      "bedroom": 3,
      "bathroom": 2,
      "kitchen": 1,
      "living_room": 1
    },
    
    "actual_divisions": {
      "bedroom": 3,
      "bathroom": 2,
      "kitchen": 1,
      "living_room": 1
    },
    
    "division_count_accuracy": 1.0,
    
    "wrong_room_classifications": [
      {
        "image_index": 5,
        "image_url": "https://...",
        "classified_as": "bedroom",
        "should_be": "living_room",
        "notes": "Misclassified due to similar furniture"
      }
    ],
    
    "wrong_divisions": [
      {
        "division_id": "bedroom_1",
        "room_type": "bedroom",
        "issue": "Contains images from bedroom_2",
        "image_indices": [8, 9, 10, 11],
        "notes": "Signature similarity too low, didn't group correctly"
      }
    ],
    
    "notes": "Overall good performance. Main issue: bedroom grouping too strict."
  },
  
  "result_file": "data/image_grouper/test_result_34547389.json"
}
```

### Field Explanations

#### Top Level
- **test_name**: Identifier for this test approach (e.g., "signature_grouping", "batch_grouping")
- **listing_id**: Which property listing was tested
- **start_time/end_time**: ISO format timestamps
- **execution_time_seconds**: Total wall-clock time

#### API Calls Array
Each object represents one API request:
- **model**: Which OpenAI model was used
- **input_tokens**: Tokens in the request (prompt + images)
- **output_tokens**: Tokens in the response
- **timestamp**: When this call was made
- **cost**: Calculated cost for this single call

#### Totals
- **total_input_tokens**: Sum of all input tokens
- **total_output_tokens**: Sum of all output tokens
- **total_cost**: Sum of all API call costs

#### Accuracy Object

**Automatic Metrics:**
- **total_images**: Number of images processed
- **division_count_accuracy**: Percentage of room types with correct division count
  - Formula: `(correct_room_types / total_room_types)`
  - Example: Expected 3 bedrooms, got 3 = correct. Expected 2 bathrooms, got 1 = wrong.
  - Result: 1/2 = 0.5 = 50%

**Manual Review Fields (Fill These In):**

1. **wrong_room_classifications**: Array of misclassified images
   ```json
   {
     "image_index": 5,
     "image_url": "https://...",
     "classified_as": "bedroom",
     "should_be": "living_room",
     "notes": "Why it was wrong"
   }
   ```

2. **wrong_divisions**: Array of incorrectly grouped divisions
   ```json
   {
     "division_id": "bedroom_1",
     "room_type": "bedroom",
     "issue": "Contains images from different bedrooms",
     "image_indices": [8, 9, 10, 11],
     "notes": "Should be split into bedroom_1 and bedroom_2"
   }
   ```

3. **notes**: Free-form text for overall observations

**Expected vs Actual:**
- **expected_divisions**: What you expect (from listing data)
- **actual_divisions**: What the test produced
- Compare these to see discrepancies

### Comparison Report JSON

**Filename:** `test_comparison_{timestamp}.json`

```json
{
  "summary": {
    "total_runs": 3,
    "tests": [
      {
        "test_name": "signature_grouping",
        "listing_id": "34547389",
        "execution_time_seconds": 45.2,
        "total_cost": 0.0234,
        "total_tokens": 140000,
        "api_calls_count": 25,
        "accuracy": {
          "room_type_accuracy": 0.92,
          "division_count_accuracy": 1.0
        },
        "result_file": "data/image_grouper/test_result_34547389.json"
      },
      {
        "test_name": "batch_grouping",
        "listing_id": "34547389",
        "execution_time_seconds": 12.5,
        "total_cost": 0.0456,
        "total_tokens": 180000,
        "api_calls_count": 6,
        "accuracy": {
          "room_type_accuracy": 0.88,
          "division_count_accuracy": 0.75
        },
        "result_file": "data/image_grouper/test_batch_34547389.json"
      }
    ]
  }
}
```

**What it shows:**
- Side-by-side comparison of all tests
- Sorted by cost (cheapest first)
- Easy to see which approach is best for each metric

---

## 🔍 Understanding the Output

### Cost Calculation

```
Cost per call = (input_tokens / 1,000,000) × input_price + (output_tokens / 1,000,000) × output_price

Example:
- Model: gpt-4o-mini
- Input: 5,000 tokens → (5000/1M) × $0.15 = $0.00075
- Output: 500 tokens → (500/1M) × $0.60 = $0.0003
- Total: $0.00105
```

### Accuracy Calculation

**Division Count Accuracy:**
```
For each room type:
  if actual_count == expected_count:
    correct += 1
  total += 1

accuracy = correct / total

Example:
  bedroom: expected 3, actual 3 → correct
  bathroom: expected 2, actual 1 → wrong
  kitchen: expected 1, actual 1 → correct
  living_room: expected 1, actual 1 → correct
  
  accuracy = 3/4 = 0.75 = 75%
```

**Room Type Accuracy:**
- Currently placeholder (0.0)
- You calculate manually by comparing classifications
- Fill in `wrong_room_classifications` array
- Then calculate: `correct / total_images`

---

## 📝 Manual Review Workflow

1. **Run your test** → Creates tracking JSON
2. **Open the result file** → Review actual groupings
3. **Compare with expected** → Identify errors
4. **Fill in manual fields:**
   - Add wrong classifications to `wrong_room_classifications`
   - Add wrong divisions to `wrong_divisions`
   - Add notes
5. **Recalculate accuracy** → Update `room_type_accuracy`
6. **Save the updated JSON** → Keep for comparison

---

## 🎯 Best Practices

1. **Use descriptive test names**: `signature_grouping`, `batch_grouping`, `single_request`
2. **Track consistently**: Always use the tracker for fair comparisons
3. **Fill accuracy manually**: Don't skip the manual review step
4. **Compare regularly**: Run comparison reports to see trends
5. **Test multiple listings**: One listing might be easier/harder than others

---

## 🔧 Troubleshooting

**Q: Cost seems wrong?**
- Check `MODEL_PRICING` dict has correct prices
- Verify model name matches exactly (case-sensitive)

**Q: Accuracy is 0?**
- Room type accuracy starts at 0 (you fill manually)
- Division accuracy should auto-calculate if expected_divisions is correct

**Q: API calls not tracked?**
- Make sure you're using `TrackedOpenAIClient` or calling `track_api_call()` manually
- Check that response has `usage` attribute

**Q: Comparison report empty?**
- Make sure tracking JSON files are in `data/image_grouper/`
- Files must start with `test_tracking_` and end with `.json`

