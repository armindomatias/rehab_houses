"""
REHAB CALCULATOR

GOAL => make the calculators per house/apartment of remodelation costs
"""

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


