"""
REHAB CALCULATOR

GOAL => make the calculators per house/apartment of remodelation costs
"""

import json
import os
from typing import Dict, List, Any, Optional, Tuple
from math import sqrt

def painting_room_calculator(length_m2, width_m2, windows, paint_quality="standard", num_coats=2, include_ceiling=True, pay_painting=True):
    """
    Calculate comprehensive cost for painting a room
    
    Args:
        length_m2: Room length in meters
        width_m2: Room width in meters
        windows: Number of windows
        paint_quality: Quality level ("basic", "standard", "premium")
        num_coats: Number of paint coats (typically 2-3)
        include_ceiling: Whether to paint the ceiling
        pay_painting: Whether to include painting workforce costs
    
    Returns:
        Total cost for room painting project
    """
    
    # Calculate areas
    floor_m2 = length_m2 * width_m2
    room_height = 2.5  # Standard ceiling height
    walls_m2 = 2 * room_height * (length_m2 + width_m2)  # 4 walls
    
    # Window and door area deductions
    windows_m2 = windows * 1.5  # Average window size 1.5m²
    doors_m2 = 2.0  # Standard door size
    paintable_walls_m2 = walls_m2 - windows_m2 - doors_m2
    
    # Total paintable area
    if include_ceiling:
        total_paintable_m2 = paintable_walls_m2 + floor_m2  # ceiling = floor area
    else:
        total_paintable_m2 = paintable_walls_m2
    
    # Paint costs per liter by quality
    paint_costs_per_liter = {
        "basic": 25,      # €20-30/L basic paint
        "standard": 35,   # €30-40/L standard quality  
        "premium": 50     # €45-55/L premium paint
    }
    
    paint_cost_per_liter = paint_costs_per_liter.get(paint_quality, 35)
    
    # Paint coverage and consumption
    coverage_per_liter = 10  # m² per liter (varies by surface)
    total_paint_liters = (total_paintable_m2 * num_coats) / coverage_per_liter
    
    # Primer cost (essential for good finish)
    primer_liters = total_paintable_m2 / coverage_per_liter
    primer_cost_per_liter = 20
    
    # Painting tools and accessories
    brushes_rollers = 30  # Quality brushes and rollers
    plastic_sheets = 10   # Floor and furniture protection
    painter_tape = 12     # Masking tape
    cleaning_supplies = 8  # Cleaners, rags, etc.
    
    # Calculate total material costs
    paint_cost = total_paint_liters * paint_cost_per_liter
    primer_cost = primer_liters * primer_cost_per_liter
    tools_accessories = brushes_rollers + plastic_sheets + painter_tape + cleaning_supplies
    
    # Error margin includes sanding materials, filler, putty, and other prep costs
    error_margin = 0.15  # 20% margin for painting projects (includes prep materials)
    cost_materials = (paint_cost + primer_cost + tools_accessories) * (1 + error_margin)
    
    # Workforce costs if requested
    if pay_painting:
        # Different rates for preparation vs painting
        sanding_prep_hours = total_paintable_m2 * 0.15  # 0.15h per m² for prep
        painting_hours = total_paintable_m2 * num_coats * 0.12  # 0.12h per m² per coat
        
        hourly_rate = 25  # €20-30/hour for painting work
        cost_workforce = (sanding_prep_hours + painting_hours) * hourly_rate
    else:
        cost_workforce = 0
    
    total_cost = cost_materials + cost_workforce
    
    return total_cost


def floor_replacement_calculator(length_m2, width_m2, floor_type="laminate", pay_installation=True):
    """
    Calculate cost for floor replacement
    
    Args:
        length_m2: Room length in meters
        width_m2: Room width in meters  
        floor_type: Type of flooring ("laminate", "vinyl", "ceramic", "hardwood", "parquet")
        pay_installation: Whether to include installation workforce costs
    
    Returns:
        Total cost for floor replacement
    """
    
    # Calculate floor area
    floor_area_m2 = length_m2 * width_m2
    
    # Flooring material costs per m2 (EUR)
    flooring_costs = {
        "laminate": 25,      # 20-30 EUR/m2
        "vinyl": 30,         # 25-35 EUR/m2  
        "ceramic": 35,       # 30-40 EUR/m2
        "hardwood": 60,      # 50-70 EUR/m2
        "parquet": 50        # 40-60 EUR/m2
    }
    
    # Get cost per m2 for selected flooring type
    cost_flooring_m2 = flooring_costs.get(floor_type, 25)
    
    # Additional materials (underlayment, trim, adhesive, etc.)
    additional_materials_cost_m2 = 8  # ~5-10 EUR/m2
    
    # Error margin for waste and miscalculations
    error_margin = 0.15  # 15% for flooring (higher than painting due to cutting waste)
    
    # Calculate material costs
    cost_materials = (floor_area_m2 * (cost_flooring_m2 + additional_materials_cost_m2)) * (1 + error_margin)
    
    # Workforce costs if requested
    if pay_installation:
        cost_workforce_installation_m2 = 15  # 10-20 EUR/m2 for installation
        cost_workforce = cost_workforce_installation_m2 * floor_area_m2
    else:
        cost_workforce = 0
    
    total_cost = cost_materials + cost_workforce
    
    return total_cost


def window_replacement_calculator(num_windows, avg_width_m, avg_height_m, window_type="double_glazed_pvc", pay_installation=True):
    """
    Calculate cost for window replacement
    
    Args:
        num_windows: Number of windows to replace
        avg_width_m: Average window width in meters
        avg_height_m: Average window height in meters
        window_type: Type of windows ("single_glazed_pvc", "double_glazed_pvc", "triple_glazed_pvc", 
                    "double_glazed_aluminum", "double_glazed_wood", "premium_wood")
        pay_installation: Whether to include installation workforce costs
    
    Returns:
        Total cost for window replacement
    """
    
    # Calculate total window area
    window_area_m2 = num_windows * avg_width_m * avg_height_m
    
    # Window costs per m2 (EUR) - includes frame and glass
    window_costs = {
        "single_glazed_pvc": 200,       # 180-220 EUR/m2 - basic option
        "double_glazed_pvc": 300,       # 280-320 EUR/m2 - most common
        "triple_glazed_pvc": 400,       # 380-420 EUR/m2 - high efficiency
        "double_glazed_aluminum": 350,  # 330-370 EUR/m2 - modern look
        "double_glazed_wood": 450,      # 420-480 EUR/m2 - traditional
        "premium_wood": 600             # 550-650 EUR/m2 - luxury option
    }
    
    # Get cost per m2 for selected window type
    cost_window_m2 = window_costs.get(window_type, 300)
    
    # Additional materials and prep work
    additional_costs_per_window = 50  # Sealants, trim, finishing materials
    total_additional_costs = num_windows * additional_costs_per_window
    
    # Disposal of old windows
    disposal_cost_per_window = 30
    total_disposal_cost = num_windows * disposal_cost_per_window
    
    # Error margin for unforeseen complications
    error_margin = 0.12  # 12% for windows (potential wall repairs, sizing issues)
    
    # Calculate material costs
    cost_materials = (window_area_m2 * cost_window_m2 + total_additional_costs + total_disposal_cost) * (1 + error_margin)
    
    # Workforce costs if requested
    if pay_installation:
        # Installation cost per window (varies by complexity)
        cost_workforce_per_window = 150  # 120-180 EUR per window for installation
        cost_workforce = cost_workforce_per_window * num_windows
    else:
        cost_workforce = 0
    
    total_cost = cost_materials + cost_workforce
    
    return total_cost


def plumbing_renovation_calculator(room_type: str, size_m2: float, condition_rating: float, quality_level: str = "midend", pay_installation: bool = True) -> float:
    """
    Calculate cost for plumbing renovation/upgrade
    
    Args:
        room_type: Type of room (kitchen, bathroom)
        size_m2: Room size in square meters
        condition_rating: Condition rating 0-4
        quality_level: Quality level ("lowend", "midend", "highend")
        pay_installation: Whether to include installation workforce costs
    
    Returns:
        Total cost for plumbing renovation
    """
    
    # Base plumbing costs per room type (EUR)
    base_costs = {
        "bathroom": {
            "lowend": 800,   # Basic fixtures: toilet, sink, shower
            "midend": 1500,  # Standard fixtures: toilet, sink, bathtub/shower
            "highend": 3000  # Premium fixtures: luxury toilet, designer sink, spa shower
        },
        "kitchen": {
            "lowend": 400,   # Basic sink and faucet
            "midend": 800,   # Standard sink, faucet, dishwasher connection
            "highend": 1500   # Premium sink, faucet, advanced plumbing
        }
    }
    
    room_base = base_costs.get(room_type.lower(), {"midend": 500})
    base_cost = room_base.get(quality_level, room_base.get("midend", 500))
    
    # Adjust cost based on condition rating (0 = total replacement, 2 = outdated but usable, 4 = excellent/new)
    condition_multiplier = 1.0
    if condition_rating < 1.0:
        condition_multiplier = 1.4  # Total replacement needed (0)
    elif condition_rating < 2.0:
        condition_multiplier = 1.3  # Very poor, near total replacement (0-1)
    elif condition_rating < 2.5:
        condition_multiplier = 1.2  # Outdated but usable (2)
    elif condition_rating < 3.5:
        condition_multiplier = 1.0  # Moderate condition (2.5-3)
    else:
        condition_multiplier = 0.8  # Good to excellent (3.5-4), mostly updates
    
    # Material costs
    cost_materials = base_cost * condition_multiplier
    
    # Additional materials (pipes, fittings, sealants)
    additional_materials = size_m2 * 15  # ~10-20 EUR/m² for additional materials
    
    # Error margin
    error_margin = 0.15
    
    total_materials = (cost_materials + additional_materials) * (1 + error_margin)
    
    # Workforce costs
    if pay_installation:
        # Plumbing work hours (more complex for bathrooms)
        if room_type.lower() == "bathroom":
            work_hours = 8 + (size_m2 * 0.5)  # Base 8h + size factor
        else:
            work_hours = 4 + (size_m2 * 0.3)  # Base 4h + size factor
        
        hourly_rate = 35  # €30-40/hour for plumbing work
        cost_workforce = work_hours * hourly_rate
    else:
        cost_workforce = 0
    
    return total_materials + cost_workforce


def electrical_renovation_calculator(size_m2: float, condition_rating: float, quality_level: str = "midend", pay_installation: bool = True) -> float:
    """
    Calculate cost for electrical renovation/upgrade
    
    Args:
        size_m2: Room size in square meters
        condition_rating: Condition rating 0-4
        quality_level: Quality level ("lowend", "midend", "highend")
        pay_installation: Whether to include installation workforce costs
    
    Returns:
        Total cost for electrical renovation
    """
    
    # Base electrical costs per quality level (EUR per m²)
    base_costs_per_m2 = {
        "lowend": 30,    # Basic outlets and switches
        "midend": 50,    # Standard outlets, switches, lighting
        "highend": 80    # Premium outlets, smart switches, advanced lighting
    }
    
    base_cost_per_m2 = base_costs_per_m2.get(quality_level, 50)
    
    # Adjust based on condition rating (0 = total replacement, 2 = outdated but usable, 4 = excellent/new)
    condition_multiplier = 1.0
    if condition_rating < 1.0:
        condition_multiplier = 1.5  # Total replacement needed (0), may need rewiring
    elif condition_rating < 2.0:
        condition_multiplier = 1.4  # Very poor, near total replacement (0-1)
    elif condition_rating < 2.5:
        condition_multiplier = 1.2  # Outdated but usable (2)
    elif condition_rating < 3.5:
        condition_multiplier = 1.0  # Moderate condition (2.5-3)
    else:
        condition_multiplier = 0.8  # Good to excellent (3.5-4), mostly updates
    
    # Material costs
    cost_materials = size_m2 * base_cost_per_m2 * condition_multiplier
    
    # Additional materials (wires, junction boxes, etc.)
    additional_materials = size_m2 * 10  # ~8-12 EUR/m²
    
    # Error margin
    error_margin = 0.15
    
    total_materials = (cost_materials + additional_materials) * (1 + error_margin)
    
    # Workforce costs
    if pay_installation:
        work_hours = size_m2 * 0.3  # 0.3h per m² for electrical work
        hourly_rate = 30  # €25-35/hour for electrical work
        cost_workforce = work_hours * hourly_rate
    else:
        cost_workforce = 0
    
    return total_materials + cost_workforce


def appliances_renovation_calculator(room_type: str, condition_rating: float, quality_level: str = "midend", pay_installation: bool = True) -> float:
    """
    Calculate cost for appliances/fixtures renovation
    
    Args:
        room_type: Type of room (kitchen, bathroom, bedroom, living_room)
        condition_rating: Condition rating 0-4
        quality_level: Quality level ("lowend", "midend", "highend")
        pay_installation: Whether to include installation workforce costs
    
    Returns:
        Total cost for appliances/fixtures renovation
    """
    
    # Base appliance costs per room type (EUR)
    base_costs = {
        "kitchen": {
            "lowend": 1500,   # Basic stove, fridge, dishwasher
            "midend": 3000,   # Standard appliances: stove, fridge, dishwasher, extractor
            "highend": 6000   # Premium appliances: high-end brands
        },
        "bathroom": {
            "lowend": 400,    # Basic fixtures
            "midend": 800,    # Standard fixtures: mirrors, storage, heater
            "highend": 1500   # Premium fixtures: designer elements
        },
        "bedroom": {
            "lowend": 200,   # Basic wardrobe/closet
            "midend": 500,   # Standard built-in wardrobe
            "highend": 1200  # Premium custom wardrobe
        },
        "living_room": {
            "lowend": 300,   # Basic fixtures
            "midend": 600,   # Standard elements: storage, radiators
            "highend": 1500  # Premium elements
        }
    }
    
    room_base = base_costs.get(room_type.lower(), {"midend": 500})
    base_cost = room_base.get(quality_level, room_base.get("midend", 500))
    
    # Adjust based on condition rating (0 = total replacement, 2 = outdated but usable, 4 = excellent/new)
    condition_multiplier = 1.0
    if condition_rating < 1.0:
        condition_multiplier = 1.3  # Total replacement needed (0)
    elif condition_rating < 2.0:
        condition_multiplier = 1.2  # Very poor, near total replacement (0-1)
    elif condition_rating < 2.5:
        condition_multiplier = 1.1  # Outdated but usable (2)
    elif condition_rating < 3.5:
        condition_multiplier = 1.0  # Moderate condition (2.5-3)
    else:
        condition_multiplier = 0.9  # Good to excellent (3.5-4), mostly updates
    
    # Material costs
    cost_materials = base_cost * condition_multiplier
    
    # Error margin
    error_margin = 0.10
    
    total_materials = cost_materials * (1 + error_margin)
    
    # Workforce costs
    if pay_installation:
        # Installation hours vary by room type
        work_hours_map = {
            "kitchen": 6,      # Appliance installation
            "bathroom": 3,     # Fixture installation
            "bedroom": 4,      # Wardrobe installation
            "living_room": 2   # Basic fixture installation
        }
        work_hours = work_hours_map.get(room_type.lower(), 3)
        hourly_rate = 30  # €25-35/hour
        cost_workforce = work_hours * hourly_rate
    else:
        cost_workforce = 0
    
    return total_materials + cost_workforce


def ceiling_repair_calculator(size_m2: float, condition_rating: float, quality_level: str = "midend", pay_installation: bool = True) -> float:
    """
    Calculate cost for ceiling repair/renovation
    
    Args:
        size_m2: Room size in square meters
        condition_rating: Condition rating 0-4
        quality_level: Quality level ("lowend", "midend", "highend")
        pay_installation: Whether to include installation workforce costs
    
    Returns:
        Total cost for ceiling repair
    """
    
    # Base ceiling costs per m² (EUR)
    base_costs_per_m2 = {
        "lowend": 15,    # Basic repair and paint
        "midend": 25,    # Standard repair, plaster, paint
        "highend": 40    # Premium finish, decorative elements
    }
    
    base_cost_per_m2 = base_costs_per_m2.get(quality_level, 25)
    
    # Adjust based on condition rating (0 = total replacement, 2 = outdated but usable, 4 = excellent/new)
    condition_multiplier = 1.0
    if condition_rating < 1.0:
        condition_multiplier = 1.6  # Total replacement needed (0), may need structural work
    elif condition_rating < 2.0:
        condition_multiplier = 1.4  # Very poor, near total replacement (0-1)
    elif condition_rating < 2.5:
        condition_multiplier = 1.2  # Outdated but usable (2)
    elif condition_rating < 3.5:
        condition_multiplier = 1.0  # Moderate condition (2.5-3)
    else:
        condition_multiplier = 0.7  # Good to excellent (3.5-4), minimal work
    
    # Material costs
    cost_materials = size_m2 * base_cost_per_m2 * condition_multiplier
    
    # Error margin
    error_margin = 0.15
    
    total_materials = cost_materials * (1 + error_margin)
    
    # Workforce costs
    if pay_installation:
        work_hours = size_m2 * 0.2  # 0.2h per m² for ceiling work
        hourly_rate = 25  # €20-30/hour
        cost_workforce = work_hours * hourly_rate
    else:
        cost_workforce = 0
    
    return total_materials + cost_workforce


class PropertyRemodelingCalculator:
    """
    Comprehensive property remodeling calculator based on classification data
    """
    
    def __init__(self, classification_json_path: str):
        """
        Initialize calculator with classification data
        
        Args:
            classification_json_path: Path to deduplicated classification JSON file
        """
        self.classification_path = classification_json_path
        self.classification_data = self._load_classification_data()
        
    def _load_classification_data(self) -> Dict[str, Any]:
        """Load classification data from JSON file"""
        try:
            with open(self.classification_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise FileNotFoundError(f"Failed to load classification data: {e}")
    
    def _estimate_room_dimensions(self, size_m2: float) -> Tuple[float, float]:
        """
        Estimate length and width from total size
        Assumes roughly square rooms (can be improved with actual data)
        """
        if size_m2 <= 0:
            return 3.0, 2.5  # Default small room
        
        # Assume roughly square rooms
        side_length = sqrt(size_m2)
        # Add some variation (rooms are rarely perfect squares)
        length = side_length * 1.1
        width = size_m2 / length
        
        return round(length, 1), round(width, 1)
    
    def _determine_quality_level(self, quality_level: str = "midend") -> Dict[str, str]:
        """
        Map quality level to specific material choices
        
        Returns dict with material choices for each renovation type
        """
        quality_map = {
            "lowend": {
                "paint": "basic",
                "floor": "laminate",
                "window": "single_glazed_pvc"
            },
            "midend": {
                "paint": "standard",
                "floor": "vinyl",
                "window": "double_glazed_pvc"
            },
            "highend": {
                "paint": "premium",
                "floor": "hardwood",
                "window": "double_glazed_aluminum"
            }
        }
        return quality_map.get(quality_level, quality_map["midend"])
    
    def _get_condition_description(self, rating: float) -> str:
        """
        Get human-readable description of condition rating
        
        Based on classification scale:
        - 0 = total replacement needed
        - 2 = outdated but usable
        - 4 = excellent/new
        """
        if rating < 1.0:
            return "Total replacement needed (0)"
        elif rating < 2.0:
            return "Very poor, near total replacement (0-1)"
        elif rating < 2.5:
            return "Outdated but usable (2)"
        elif rating < 3.5:
            return "Moderate condition (2.5-3)"
        else:
            return "Good to excellent (3.5-4)"
    
    def get_condition_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all condition ratings across the property
        
        Returns:
            Dictionary with condition summaries by room type
        """
        summary = {
            "rooms": {},
            "property_average": {}
        }
        
        all_ratings = {
            "overall_condition": [],
            "flooring_condition": [],
            "ceiling_condition": [],
            "painting_condition": [],
            "windows_condition": [],
            "doors_condition": [],
            "plumbing_condition": [],
            "electrical_condition": [],
            "appliances_condition": []
        }
        
        for room_type, divisions in self.classification_data.items():
            if room_type == "views" or room_type == "house_plan":
                continue
            
            room_summary = {
                "room_count": len(divisions),
                "average_conditions": {},
                "condition_descriptions": []
            }
            
            for division in divisions:
                division_id = division.get("division_id", "unknown")
                conditions = {}
                
                for condition_key in all_ratings.keys():
                    rating = division.get(condition_key)
                    if rating is not None:
                        all_ratings[condition_key].append(rating)
                        conditions[condition_key] = {
                            "rating": rating,
                            "description": self._get_condition_description(rating)
                        }
                
                room_summary["condition_descriptions"].append({
                    "division_id": division_id,
                    "size_m2": division.get("size_m2", 0),
                    "conditions": conditions
                })
            
            # Calculate averages
            for condition_key in all_ratings.keys():
                ratings = [d.get(condition_key) for d in divisions if d.get(condition_key) is not None]
                if ratings:
                    room_summary["average_conditions"][condition_key] = {
                        "average": round(sum(ratings) / len(ratings), 2),
                        "min": round(min(ratings), 2),
                        "max": round(max(ratings), 2),
                        "description": self._get_condition_description(sum(ratings) / len(ratings))
                    }
            
            summary["rooms"][room_type] = room_summary
        
        # Property-wide averages
        for condition_key, ratings in all_ratings.items():
            if ratings:
                summary["property_average"][condition_key] = {
                    "average": round(sum(ratings) / len(ratings), 2),
                    "min": round(min(ratings), 2),
                    "max": round(max(ratings), 2),
                    "description": self._get_condition_description(sum(ratings) / len(ratings))
                }
        
        return summary
    
    def calculate_remodeling_costs(
        self,
        # Boolean flags for what to renovate
        windows: bool = False,
        flooring: bool = False,
        painting: bool = False,
        plumbing: bool = False,
        electrical: bool = False,
        appliances: bool = False,
        ceiling: bool = False,
        # Quality level (currently midend, but extensible)
        quality_level: str = "midend",
        # Whether to include workforce costs
        include_workforce: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive remodeling costs for the entire property
        
        Args:
            windows: Whether to replace/renovate windows
            flooring: Whether to replace flooring
            painting: Whether to paint walls
            plumbing: Whether to renovate plumbing
            electrical: Whether to renovate electrical
            appliances: Whether to replace appliances/fixtures
            ceiling: Whether to repair/renovate ceiling
            quality_level: Quality level ("lowend", "midend", "highend")
            include_workforce: Whether to include workforce costs
        
        Returns:
            Dictionary with detailed cost breakdown
        """
        
        quality_materials = self._determine_quality_level(quality_level)
        
        total_costs = {
            "property_total": 0.0,
            "rooms": {},
            "summary": {
                "windows": 0.0,
                "flooring": 0.0,
                "painting": 0.0,
                "plumbing": 0.0,
                "electrical": 0.0,
                "appliances": 0.0,
                "ceiling": 0.0
            }
        }
        
        # Process each room type
        for room_type, divisions in self.classification_data.items():
            if room_type == "views" or room_type == "house_plan":
                continue  # Skip views and house plans
            
            for division in divisions:
                division_id = division.get("division_id", "unknown")
                size_m2 = division.get("size_m2", 0)
                length = division.get("length_m2")
                width = division.get("width_m2")
                
                # Estimate dimensions if not provided
                if not length or not width:
                    length, width = self._estimate_room_dimensions(size_m2)
                
                room_costs = {
                    "division_id": division_id,
                    "room_type": room_type,
                    "size_m2": size_m2,
                    "costs": {},
                    "total": 0.0
                }
                
                # Windows renovation
                if windows:
                    windows_num = division.get("windows_number", 0)
                    windows_condition = division.get("windows_condition")
                    
                    if windows_num > 0 and windows_condition is not None:
                        # Average window size (1.2m x 1.5m)
                        avg_width = 1.2
                        avg_height = 1.5
                        
                        window_cost = window_replacement_calculator(
                            num_windows=windows_num,
                            avg_width_m=avg_width,
                            avg_height_m=avg_height,
                            window_type=quality_materials["window"],
                            pay_installation=include_workforce
                        )
                        room_costs["costs"]["windows"] = window_cost
                        total_costs["summary"]["windows"] += window_cost
                
                # Flooring renovation
                if flooring:
                    flooring_condition = division.get("flooring_condition")
                    
                    if flooring_condition is not None:
                        floor_cost = floor_replacement_calculator(
                            length_m2=length,
                            width_m2=width,
                            floor_type=quality_materials["floor"],
                            pay_installation=include_workforce
                        )
                        room_costs["costs"]["flooring"] = floor_cost
                        total_costs["summary"]["flooring"] += floor_cost
                
                # Painting renovation
                if painting:
                    painting_condition = division.get("painting_condition")
                    
                    if painting_condition is not None:
                        windows_num = division.get("windows_number", 0)
                        
                        paint_cost = painting_room_calculator(
                            length_m2=length,
                            width_m2=width,
                            windows=windows_num,
                            paint_quality=quality_materials["paint"],
                            num_coats=2,
                            include_ceiling=True,
                            pay_painting=include_workforce
                        )
                        room_costs["costs"]["painting"] = paint_cost
                        total_costs["summary"]["painting"] += paint_cost
                
                # Plumbing renovation
                if plumbing and room_type in ["kitchen", "bathroom"]:
                    plumbing_condition = division.get("plumbing_condition")
                    
                    if plumbing_condition is not None:
                        plumbing_cost = plumbing_renovation_calculator(
                            room_type=room_type,
                            size_m2=size_m2,
                            condition_rating=plumbing_condition,
                            quality_level=quality_level,
                            pay_installation=include_workforce
                        )
                        room_costs["costs"]["plumbing"] = plumbing_cost
                        total_costs["summary"]["plumbing"] += plumbing_cost
                
                # Electrical renovation
                if electrical:
                    electrical_condition = division.get("electrical_condition")
                    
                    if electrical_condition is not None:
                        electrical_cost = electrical_renovation_calculator(
                            size_m2=size_m2,
                            condition_rating=electrical_condition,
                            quality_level=quality_level,
                            pay_installation=include_workforce
                        )
                        room_costs["costs"]["electrical"] = electrical_cost
                        total_costs["summary"]["electrical"] += electrical_cost
                
                # Appliances renovation
                if appliances:
                    appliances_condition = division.get("appliances_condition")
                    
                    if appliances_condition is not None:
                        appliances_cost = appliances_renovation_calculator(
                            room_type=room_type,
                            condition_rating=appliances_condition,
                            quality_level=quality_level,
                            pay_installation=include_workforce
                        )
                        room_costs["costs"]["appliances"] = appliances_cost
                        total_costs["summary"]["appliances"] += appliances_cost
                
                # Ceiling renovation
                if ceiling:
                    ceiling_condition = division.get("ceiling_condition")
                    
                    if ceiling_condition is not None:
                        ceiling_cost = ceiling_repair_calculator(
                            size_m2=size_m2,
                            condition_rating=ceiling_condition,
                            quality_level=quality_level,
                            pay_installation=include_workforce
                        )
                        room_costs["costs"]["ceiling"] = ceiling_cost
                        total_costs["summary"]["ceiling"] += ceiling_cost
                
                # Calculate room total
                room_costs["total"] = sum(room_costs["costs"].values())
                
                # Add to rooms breakdown
                if room_type not in total_costs["rooms"]:
                    total_costs["rooms"][room_type] = []
                total_costs["rooms"][room_type].append(room_costs)
                
                total_costs["property_total"] += room_costs["total"]
        
        # Round all costs to 2 decimal places
        total_costs["property_total"] = round(total_costs["property_total"], 2)
        for key in total_costs["summary"]:
            total_costs["summary"][key] = round(total_costs["summary"][key], 2)
        
        for room_type in total_costs["rooms"]:
            for room in total_costs["rooms"][room_type]:
                room["total"] = round(room["total"], 2)
                for cost_key in room["costs"]:
                    room["costs"][cost_key] = round(room["costs"][cost_key], 2)
        
        return total_costs


# Example usage
if __name__ == "__main__":
    # Example calculation for listing 34458598
    calculator = PropertyRemodelingCalculator(
        "data/image_analysis/34458598/idealista_listing_34458598_classifications_dedup.json"
    )
    
    # Show condition summary first
    print("=" * 60)
    print("PROPERTY CONDITION SUMMARY")
    print("=" * 60)
    condition_summary = calculator.get_condition_summary()
    print("\nProperty Average Conditions:")
    print("-" * 60)
    for condition_key, condition_data in condition_summary["property_average"].items():
        print(f"  {condition_key.replace('_', ' ').title()}: {condition_data['average']:.2f} ({condition_data['description']})")
        print(f"    Range: {condition_data['min']:.2f} - {condition_data['max']:.2f}")
    
    print("\n" + "=" * 60)
    print("PROPERTY REMODELING COST ESTIMATE")
    print("=" * 60)
    print("\nNote: Condition ratings (0 = total replacement, 2 = outdated but usable, 4 = excellent/new)")
    print("Costs are adjusted based on condition ratings.\n")
    
    # Calculate costs with user preferences
    results = calculator.calculate_remodeling_costs(
        windows=False,
        flooring=True,
        painting=True,
        plumbing=False,
        electrical=False,
        appliances=False,
        ceiling=False,
        quality_level="midend",
        include_workforce=True
    )
    
    print(f"Total Property Cost: €{results['property_total']:,.2f}\n")
    
    print("Cost Summary by Category:")
    print("-" * 60)
    for category, cost in results["summary"].items():
        if cost > 0:
            print(f"  {category.capitalize()}: €{cost:,.2f}")
    
    print("\nDetailed Breakdown by Room:")
    print("-" * 60)
    for room_type, rooms in results["rooms"].items():
        print(f"\n{room_type.upper()}:")
        for room in rooms:
            if room["total"] > 0:
                print(f"  {room['division_id']} ({room['size_m2']}m²): €{room['total']:,.2f}")
                for cost_type, cost in room["costs"].items():
                    print(f"    - {cost_type}: €{cost:,.2f}")

