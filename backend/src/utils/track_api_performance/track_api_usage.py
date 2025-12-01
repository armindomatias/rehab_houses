"""
API Usage and Accuracy Tracking System

Tracks:
- Model used
- Tokens (input/output)
- Cost
- Execution time
- Accuracy metrics (room type classification, division grouping)
"""

import os
import sys
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from collections import defaultdict

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from src.utils import get_logger

logger = get_logger(__name__)


# Model pricing per 1M tokens (as of 2024, update as needed)
MODEL_PRICING = {
    "gpt-4o": {
        "input": 2.50,  # $2.50 per 1M input tokens
        "output": 10.00  # $10.00 per 1M output tokens
    },
    "gpt-4o-mini": {
        "input": 0.15,
        "output": 0.60
    },
    "gpt-4.1-mini": {  # Assuming similar to gpt-4o-mini
        "input": 0.15,
        "output": 0.60
    },
    "gpt-4-turbo": {
        "input": 10.00,
        "output": 30.00
    }
}


@dataclass
class APIUsage:
    """Track a single API call"""
    model: str
    input_tokens: int
    output_tokens: int
    timestamp: str
    
    @property
    def cost(self) -> float:
        """Calculate cost for this API call"""
        if self.model not in MODEL_PRICING:
            logger.warning(f"Unknown model pricing for {self.model}, using gpt-4o-mini pricing")
            pricing = MODEL_PRICING.get("gpt-4o-mini", {"input": 0.15, "output": 0.60})
        else:
            pricing = MODEL_PRICING[self.model]
        
        input_cost = (self.input_tokens / 1_000_000) * pricing["input"]
        output_cost = (self.output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost


@dataclass
class AccuracyMetrics:
    """Track accuracy metrics"""
    total_images: int
    room_type_correct: int
    room_type_incorrect: int
    room_type_accuracy: float
    
    expected_divisions: Dict[str, int]  # room_type -> expected count
    actual_divisions: Dict[str, int]  # room_type -> actual count
    division_count_accuracy: float  # How many room types have correct division count
    
    # Manual review fields
    wrong_room_classifications: List[Dict[str, Any]]  # Images classified wrong
    wrong_divisions: List[Dict[str, Any]]  # Divisions that are wrong
    notes: str = ""  # Manual notes


@dataclass
class TestRun:
    """Complete test run tracking"""
    test_name: str
    listing_id: str
    start_time: str
    end_time: str
    execution_time_seconds: float
    
    api_calls: List[APIUsage]
    total_input_tokens: int
    total_output_tokens: int
    total_cost: float
    
    accuracy: AccuracyMetrics
    
    result_file: str  # Path to result JSON file


class APITracker:
    """Track API usage across test runs"""
    
    def __init__(self, test_name: str, listing_id: str):
        self.test_name = test_name
        self.listing_id = listing_id
        self.api_calls: List[APIUsage] = []
        self.start_time = time.time()
        self.start_timestamp = datetime.now().isoformat()
    
    def track_api_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ):
        """Track a single API call"""
        usage = APIUsage(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            timestamp=datetime.now().isoformat()
        )
        self.api_calls.append(usage)
        logger.debug(
            f"Tracked API call: {model}, "
            f"tokens: {input_tokens} in / {output_tokens} out, "
            f"cost: ${usage.cost:.6f}"
        )
    
    def calculate_accuracy(
        self,
        results: Dict[str, List[Dict[str, Any]]],
        expected_divisions: Dict[str, int],
        gallery_items: List[Dict[str, str]],
        listing_data: Dict[str, Any]
    ) -> AccuracyMetrics:
        """
        Calculate accuracy metrics.
        
        Args:
            results: Grouping results {room_type: [divisions]}
            expected_divisions: Expected division counts {room_type: count}
            gallery_items: Original gallery items
            listing_data: Listing data for ground truth
        """
        # For room type accuracy, we'd need the classifications
        # This is a simplified version - you may need to enhance based on your test structure
        total_images = len(gallery_items)
        
        # Count actual divisions
        actual_divisions = {}
        for room_type, divisions in results.items():
            actual_divisions[room_type] = len(divisions)
        
        # Calculate division count accuracy
        correct_counts = 0
        total_room_types = 0
        
        for room_type, expected_count in expected_divisions.items():
            if room_type in actual_divisions:
                if actual_divisions[room_type] == expected_count:
                    correct_counts += 1
                total_room_types += 1
        
        division_accuracy = (correct_counts / total_room_types) if total_room_types > 0 else 0.0
        
        # Room type accuracy - placeholder (you'll need to compare with ground truth)
        # For now, we'll leave this as 0 and you can fill it manually
        room_type_correct = 0
        room_type_incorrect = 0
        room_type_accuracy = 0.0
        
        return AccuracyMetrics(
            total_images=total_images,
            room_type_correct=room_type_correct,
            room_type_incorrect=room_type_incorrect,
            room_type_accuracy=room_type_accuracy,
            expected_divisions=expected_divisions,
            actual_divisions=actual_divisions,
            division_count_accuracy=division_accuracy,
            wrong_room_classifications=[],
            wrong_divisions=[],
            notes=""
        )
    
    def finalize(
        self,
        results: Dict[str, List[Dict[str, Any]]],
        expected_divisions: Dict[str, int],
        gallery_items: List[Dict[str, str]],
        listing_data: Dict[str, Any],
        result_file: str
    ) -> TestRun:
        """Finalize tracking and create TestRun object"""
        end_time = time.time()
        execution_time = end_time - self.start_time
        
        total_input = sum(call.input_tokens for call in self.api_calls)
        total_output = sum(call.output_tokens for call in self.api_calls)
        total_cost = sum(call.cost for call in self.api_calls)
        
        accuracy = self.calculate_accuracy(
            results,
            expected_divisions,
            gallery_items,
            listing_data
        )
        
        test_run = TestRun(
            test_name=self.test_name,
            listing_id=self.listing_id,
            start_time=self.start_timestamp,
            end_time=datetime.now().isoformat(),
            execution_time_seconds=execution_time,
            api_calls=self.api_calls,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_cost=total_cost,
            accuracy=accuracy,
            result_file=result_file
        )
        
        return test_run


def save_test_run(test_run: TestRun, output_dir: str = None):
    """Save test run to JSON file"""
    if output_dir is None:
        output_dir = os.path.join(backend_dir, "data/image_grouper")
    
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"test_tracking_{test_run.test_name}_{test_run.listing_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(output_dir, filename)
    
    # Convert to dict (dataclasses to dict)
    def convert_to_dict(obj):
        if hasattr(obj, '__dict__'):
            return {k: convert_to_dict(v) for k, v in obj.__dict__.items()}
        elif isinstance(obj, list):
            return [convert_to_dict(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: convert_to_dict(v) for k, v in obj.items()}
        else:
            return obj
    
    data = convert_to_dict(test_run)
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Test run tracking saved to {filepath}")
    return filepath


def load_all_test_runs(tracking_dir: str = None) -> List[Dict[str, Any]]:
    """Load all test run tracking files"""
    if tracking_dir is None:
        tracking_dir = os.path.join(backend_dir, "data/image_grouper")
    
    test_runs = []
    for filename in os.listdir(tracking_dir):
        if filename.startswith("test_tracking_") and filename.endswith(".json"):
            filepath = os.path.join(tracking_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    test_runs.append(json.load(f))
            except Exception as e:
                logger.warning(f"Failed to load {filename}: {e}")
    
    return test_runs


def compare_test_runs(test_runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compare multiple test runs and create summary"""
    if not test_runs:
        return {}
    
    comparison = {
        "summary": {
            "total_runs": len(test_runs),
            "tests": []
        }
    }
    
    for run in test_runs:
        test_info = {
            "test_name": run.get("test_name"),
            "listing_id": run.get("listing_id"),
            "execution_time_seconds": run.get("execution_time_seconds"),
            "total_cost": run.get("total_cost"),
            "total_tokens": run.get("total_input_tokens", 0) + run.get("total_output_tokens", 0),
            "accuracy": {
                "room_type_accuracy": run.get("accuracy", {}).get("room_type_accuracy", 0),
                "division_count_accuracy": run.get("accuracy", {}).get("division_count_accuracy", 0)
            },
            "api_calls_count": len(run.get("api_calls", [])),
            "result_file": run.get("result_file")
        }
        comparison["summary"]["tests"].append(test_info)
    
    # Sort by cost
    comparison["summary"]["tests"].sort(key=lambda x: x.get("total_cost", 0))
    
    return comparison


def create_comparison_report(output_file: str = None):
    """Create a comparison report of all test runs"""
    test_runs = load_all_test_runs()
    
    if not test_runs:
        print("No test runs found. Run some tests first!")
        return None
    
    comparison = compare_test_runs(test_runs)
    
    if output_file is None:
        output_file = os.path.join(
            backend_dir,
            "data/image_grouper",
            f"test_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Comparison report saved to {output_file}")
    
    # Print summary table
    print("\n" + "=" * 100)
    print("TEST RUNS COMPARISON")
    print("=" * 100)
    print(f"{'Test Name':<25} {'Listing':<12} {'Cost ($)':<10} {'Time (s)':<10} {'Tokens':<12} {'Calls':<6} {'Room Acc':<10} {'Div Acc':<10}")
    print("-" * 100)
    
    for test in comparison["summary"]["tests"]:
        print(
            f"{test['test_name']:<25} "
            f"{test['listing_id']:<12} "
            f"${test['total_cost']:<9.4f} "
            f"{test['execution_time_seconds']:<10.1f} "
            f"{test['total_tokens']:<12,} "
            f"{test['api_calls_count']:<6} "
            f"{test['accuracy']['room_type_accuracy']:<10.1%} "
            f"{test['accuracy']['division_count_accuracy']:<10.1%}"
        )
    
    print("=" * 100)
    
    # Find best by different metrics
    if len(test_runs) > 1:
        print("\nBest by metric:")
        best_cost = min(comparison["summary"]["tests"], key=lambda x: x['total_cost'])
        best_time = min(comparison["summary"]["tests"], key=lambda x: x['execution_time_seconds'])
        best_room_acc = max(comparison["summary"]["tests"], key=lambda x: x['accuracy']['room_type_accuracy'])
        best_div_acc = max(comparison["summary"]["tests"], key=lambda x: x['accuracy']['division_count_accuracy'])
        
        print(f"  Lowest Cost: {best_cost['test_name']} (${best_cost['total_cost']:.4f})")
        print(f"  Fastest: {best_time['test_name']} ({best_time['execution_time_seconds']:.1f}s)")
        print(f"  Best Room Accuracy: {best_room_acc['test_name']} ({best_room_acc['accuracy']['room_type_accuracy']:.1%})")
        print(f"  Best Division Accuracy: {best_div_acc['test_name']} ({best_div_acc['accuracy']['division_count_accuracy']:.1%})")
    
    return output_file


if __name__ == "__main__":
    # Example usage: create comparison report
    create_comparison_report()

