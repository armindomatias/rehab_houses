"""
FINANCE CALCULATOR

GOAL => make the financing calculator of the whole investment
"""

import json
import re
import sys
import os
from typing import Dict, List, Any, Optional, Tuple

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.rehab_calculator import PropertyRemodelingCalculator
except ImportError:
    from rehab_calculator import PropertyRemodelingCalculator


class PropertyFinanceCalculator:
    """
    Comprehensive property finance calculator for investment analysis
    
    Calculates:
    - Total investment (purchase + renovation)
    - Rent estimates (by room or whole apartment)
    - Monthly and annual returns
    - ROI and cash flow analysis
    """
    
    def __init__(
        self,
        purchase_price: float,
        remodeling_costs: float,
        listing_json_path: Optional[str] = None,
        classification_json_path: Optional[str] = None
    ):
        """
        Initialize finance calculator
        
        Args:
            purchase_price: Property purchase price in EUR
            remodeling_costs: Total remodeling costs in EUR
            listing_json_path: Optional path to Idealista listing JSON for property details
            classification_json_path: Optional path to classification JSON for room count
        """
        self.purchase_price = purchase_price
        self.remodeling_costs = remodeling_costs
        self.total_investment = purchase_price + remodeling_costs
        
        self.listing_data = None
        self.classification_data = None
        
        if listing_json_path:
            self._load_listing_data(listing_json_path)
        
        if classification_json_path:
            self._load_classification_data(classification_json_path)
    
    def _load_listing_data(self, json_path: str):
        """Load Idealista listing data"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    self.listing_data = data[0]
                elif isinstance(data, dict):
                    self.listing_data = data
        except Exception as e:
            print(f"Warning: Could not load listing data: {e}")
    
    def _load_classification_data(self, json_path: str):
        """Load classification data to count rooms"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                self.classification_data = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load classification data: {e}")
    
    def _extract_price_from_string(self, price_str: str) -> Optional[float]:
        """Extract numeric price from string like '315000 €' or '850,000 €'"""
        if not price_str:
            return None
        
        # Remove currency symbols and spaces
        price_clean = re.sub(r'[€,\s]', '', str(price_str))
        
        # Extract first number
        match = re.search(r'(\d+(?:\.\d+)?)', price_clean)
        if match:
            return float(match.group(1))
        return None
    
    def _get_property_size(self) -> Optional[float]:
        """Get property size in m² from listing data"""
        if not self.listing_data:
            return None
        
        # Try to get from propertySpecs
        if 'propertySpecs' in self.listing_data:
            specs = self.listing_data['propertySpecs']
            if 'constructedArea' in specs:
                return float(specs['constructedArea'])
        
        # Try to extract from characteristics
        if 'characteristics' in self.listing_data:
            for char in self.listing_data['characteristics']:
                match = re.search(r'(\d+)\s*m²', str(char), re.IGNORECASE)
                if match:
                    return float(match.group(1))
        
        return None
    
    def _get_bedroom_count(self) -> Optional[int]:
        """Get number of bedrooms from listing or classification data"""
        # Try listing data first
        if self.listing_data:
            # From propertySpecs
            if 'propertySpecs' in self.listing_data:
                specs = self.listing_data['propertySpecs']
                if 'rooms' in specs:
                    return int(specs['rooms'])
            
            # From characteristics (T3, T4, etc.)
            if 'characteristics' in self.listing_data:
                for char in self.listing_data['characteristics']:
                    match = re.search(r'T(\d+)', str(char), re.IGNORECASE)
                    if match:
                        return int(match.group(1))
        
        # Try classification data
        if self.classification_data:
            bedroom_count = 0
            if 'bedroom' in self.classification_data:
                bedroom_count = len(self.classification_data['bedroom'])
            elif 'bedrooms' in self.classification_data:
                bedroom_count = len(self.classification_data['bedrooms'])
            
            if bedroom_count > 0:
                return bedroom_count
        
        return None
    
    def _get_bathroom_count(self) -> Optional[int]:
        """Get number of bathrooms from listing data"""
        if not self.listing_data:
            return None
        
        # From characteristics
        if 'characteristics' in self.listing_data:
            for char in self.listing_data['characteristics']:
                match = re.search(r'(\d+)\s*bathroom', str(char), re.IGNORECASE)
                if match:
                    return int(match.group(1))
        
        return None
    
    def _get_location(self) -> Optional[str]:
        """Get property location"""
        if self.listing_data and 'location' in self.listing_data:
            return self.listing_data['location']
        return None
    
    def estimate_rent_by_room(
        self,
        base_rent_per_room: float = 450,
        location_factor: float = 1.0,
        size_factor: float = 1.0,
        condition_factor: float = 1.0
    ) -> Dict[str, Any]:
        """
        Estimate rent when renting by individual rooms
        
        Args:
            base_rent_per_room: Base monthly rent per room in EUR (default 400€)
            location_factor: Multiplier for location (0.8-1.5)
            size_factor: Multiplier for room size (0.9-1.2)
            condition_factor: Multiplier for condition (0.9-1.3)
        
        Returns:
            Dictionary with rent estimates
        """
        bedroom_count = self._get_bedroom_count() or 3  # Default to 3 if unknown
        
        # Calculate rent per room
        rent_per_room = base_rent_per_room * location_factor * size_factor * condition_factor
        
        # Calculate total monthly rent
        total_monthly_rent = rent_per_room * bedroom_count
        
        # Common areas (living room, kitchen) typically add 20-30% to total
        common_areas_adjustment = 1.25
        total_monthly_rent_with_common = total_monthly_rent * common_areas_adjustment
        
        # Annual rent
        annual_rent = total_monthly_rent_with_common * 12
        
        # Account for vacancy (typically 5-10% of time)
        vacancy_rate = 0.08  # 8% vacancy
        annual_rent_after_vacancy = annual_rent * (1 - vacancy_rate)
        
        return {
            "rental_strategy": "by_room",
            "bedroom_count": bedroom_count,
            "rent_per_room_monthly": round(rent_per_room, 2),
            "total_monthly_rent": round(total_monthly_rent_with_common, 2),
            "annual_rent": round(annual_rent, 2),
            "annual_rent_after_vacancy": round(annual_rent_after_vacancy, 2),
            "vacancy_rate": vacancy_rate,
            "factors": {
                "location_factor": location_factor,
                "size_factor": size_factor,
                "condition_factor": condition_factor
            }
        }
    
    def estimate_rent_whole_apartment(
        self,
        base_rent_per_m2: float = 12,
        location_factor: float = 1.0,
        condition_factor: float = 1.0
    ) -> Dict[str, Any]:
        """
        Estimate rent when renting the whole apartment
        
        Args:
            base_rent_per_m2: Base monthly rent per m² in EUR (default 12€/m²)
            location_factor: Multiplier for location (0.8-1.5)
            condition_factor: Multiplier for condition (0.9-1.3)
        
        Returns:
            Dictionary with rent estimates
        """
        property_size = self._get_property_size()
        
        if not property_size:
            # Estimate from typical T3 (around 100-120 m²)
            bedroom_count = self._get_bedroom_count() or 3
            property_size = 90 + (bedroom_count * 10)  # Rough estimate
        
        # Calculate rent per m²
        rent_per_m2 = base_rent_per_m2 * location_factor * condition_factor
        
        # Monthly rent
        monthly_rent = property_size * rent_per_m2
        
        # Annual rent
        annual_rent = monthly_rent * 12
        
        # Account for vacancy (typically 5-10% of time)
        vacancy_rate = 0.08  # 8% vacancy
        annual_rent_after_vacancy = annual_rent * (1 - vacancy_rate)
        
        return {
            "rental_strategy": "whole_apartment",
            "property_size_m2": round(property_size, 2),
            "rent_per_m2_monthly": round(rent_per_m2, 2),
            "monthly_rent": round(monthly_rent, 2),
            "annual_rent": round(annual_rent, 2),
            "annual_rent_after_vacancy": round(annual_rent_after_vacancy, 2),
            "vacancy_rate": vacancy_rate,
            "factors": {
                "location_factor": location_factor,
                "condition_factor": condition_factor
            }
        }
    
    def calculate_financial_metrics(
        self,
        rent_estimate: Dict[str, Any],
        monthly_expenses: float = 0,
        property_tax_rate: float = 0.003,  # 0.3% of property value per year
        insurance_rate: float = 0.002,  # 0.2% of property value per year
        maintenance_rate: float = 0.01,  # 1% of property value per year
        management_fee_rate: float = 0.08  # 8% of rent for property management
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive financial metrics
        
        Args:
            rent_estimate: Rent estimate dictionary from estimate_rent_by_room or estimate_rent_whole_apartment
            monthly_expenses: Additional monthly expenses (utilities, etc.)
            property_tax_rate: Annual property tax rate (default 0.3%)
            insurance_rate: Annual insurance rate (default 0.2%)
            maintenance_rate: Annual maintenance rate (default 1%)
            management_fee_rate: Property management fee rate (default 8% of rent)
        
        Returns:
            Dictionary with financial metrics
        """
        monthly_rent = rent_estimate.get("monthly_rent") or rent_estimate.get("total_monthly_rent", 0)
        annual_rent = rent_estimate.get("annual_rent_after_vacancy", 0)
        
        # Annual expenses
        annual_property_tax = self.total_investment * property_tax_rate
        annual_insurance = self.total_investment * insurance_rate
        annual_maintenance = self.total_investment * maintenance_rate
        annual_management_fee = annual_rent * management_fee_rate
        annual_additional_expenses = monthly_expenses * 12
        
        total_annual_expenses = (
            annual_property_tax +
            annual_insurance +
            annual_maintenance +
            annual_management_fee +
            annual_additional_expenses
        )
        
        # Net income
        net_annual_income = annual_rent - total_annual_expenses
        net_monthly_income = net_annual_income / 12
        
        # ROI metrics
        roi_percentage = (net_annual_income / self.total_investment) * 100
        cash_on_cash_return = (net_annual_income / self.remodeling_costs) * 100 if self.remodeling_costs > 0 else 0
        
        # Break-even analysis
        months_to_break_even = self.total_investment / monthly_rent if monthly_rent > 0 else 0
        
        # Gross yield
        gross_yield = (annual_rent / self.total_investment) * 100
        
        # Net yield
        net_yield = (net_annual_income / self.total_investment) * 100
        
        return {
            "total_investment": round(self.total_investment, 2),
            "purchase_price": round(self.purchase_price, 2),
            "remodeling_costs": round(self.remodeling_costs, 2),
            "rent_estimate": rent_estimate,
            "income": {
                "monthly_rent": round(monthly_rent, 2),
                "annual_rent": round(annual_rent, 2)
            },
            "expenses": {
                "monthly_expenses": round(monthly_expenses, 2),
                "annual_property_tax": round(annual_property_tax, 2),
                "annual_insurance": round(annual_insurance, 2),
                "annual_maintenance": round(annual_maintenance, 2),
                "annual_management_fee": round(annual_management_fee, 2),
                "annual_additional_expenses": round(annual_additional_expenses, 2),
                "total_annual_expenses": round(total_annual_expenses, 2)
            },
            "net_income": {
                "monthly_net_income": round(net_monthly_income, 2),
                "annual_net_income": round(net_annual_income, 2)
            },
            "metrics": {
                "roi_percentage": round(roi_percentage, 2),
                "cash_on_cash_return": round(cash_on_cash_return, 2),
                "gross_yield": round(gross_yield, 2),
                "net_yield": round(net_yield, 2),
                "months_to_break_even": round(months_to_break_even, 1)
            }
        }
    
    def calculate_comprehensive_analysis(
        self,
        rental_strategy: str = "whole_apartment",  # "by_room" or "whole_apartment"
        base_rent_per_room: float = 400,
        base_rent_per_m2: float = 12,
        location_factor: float = 1.0,
        size_factor: float = 1.0,
        condition_factor: float = 1.0,
        monthly_expenses: float = 0,
        property_tax_rate: float = 0.003,
        insurance_rate: float = 0.002,
        maintenance_rate: float = 0.01,
        management_fee_rate: float = 0.08
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive financial analysis
        
        Args:
            rental_strategy: "by_room" or "whole_apartment"
            base_rent_per_room: Base monthly rent per room (for by_room strategy)
            base_rent_per_m2: Base monthly rent per m² (for whole_apartment strategy)
            location_factor: Location multiplier
            size_factor: Size multiplier (for by_room)
            condition_factor: Condition multiplier
            monthly_expenses: Additional monthly expenses
            property_tax_rate: Annual property tax rate
            insurance_rate: Annual insurance rate
            maintenance_rate: Annual maintenance rate
            management_fee_rate: Property management fee rate
        
        Returns:
            Complete financial analysis dictionary
        """
        # Estimate rent based on strategy
        if rental_strategy == "by_room":
            rent_estimate = self.estimate_rent_by_room(
                base_rent_per_room=base_rent_per_room,
                location_factor=location_factor,
                size_factor=size_factor,
                condition_factor=condition_factor
            )
        else:
            rent_estimate = self.estimate_rent_whole_apartment(
                base_rent_per_m2=base_rent_per_m2,
                location_factor=location_factor,
                condition_factor=condition_factor
            )
        
        # Calculate financial metrics
        financial_metrics = self.calculate_financial_metrics(
            rent_estimate=rent_estimate,
            monthly_expenses=monthly_expenses,
            property_tax_rate=property_tax_rate,
            insurance_rate=insurance_rate,
            maintenance_rate=maintenance_rate,
            management_fee_rate=management_fee_rate
        )
        
        # Property information
        property_info = {
            "location": self._get_location(),
            "size_m2": self._get_property_size(),
            "bedrooms": self._get_bedroom_count(),
            "bathrooms": self._get_bathroom_count()
        }
        
        return {
            "property_info": property_info,
            "investment": {
                "purchase_price": round(self.purchase_price, 2),
                "remodeling_costs": round(self.remodeling_costs, 2),
                "total_investment": round(self.total_investment, 2)
            },
            "rent_estimate": rent_estimate,
            "financial_metrics": financial_metrics
        }


# Example usage
if __name__ == "__main__":
    # Example: Calculate for listing 34458598
    # Purchase price: 315,000 EUR
    # Remodeling costs: 49,606.43 EUR (from rehab calculator)
    
    from src.rehab_calculator import PropertyRemodelingCalculator
    
    # First, get remodeling costs
    rehab_calc = PropertyRemodelingCalculator(
        "data/image_analysis/34458598/idealista_listing_34458598_classifications_dedup.json"
    )
    
    rehab_results = rehab_calc.calculate_remodeling_costs(
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
    
    remodeling_costs = rehab_results["property_total"]
    purchase_price = 315000  # From listing
    
    # Initialize finance calculator
    finance_calc = PropertyFinanceCalculator(
        purchase_price=purchase_price,
        remodeling_costs=remodeling_costs,
        listing_json_path="data/scraped_data/idealista_listing_34458598.json",
        classification_json_path="data/image_analysis/34458598/idealista_listing_34458598_classifications_dedup.json"
    )
    
    print("=" * 70)
    print("PROPERTY FINANCE CALCULATOR")
    print("=" * 70)
    
    # Calculate for both strategies
    print("\n1. RENTING BY ROOM:")
    print("-" * 70)
    by_room_analysis = finance_calc.calculate_comprehensive_analysis(
        rental_strategy="by_room",
        base_rent_per_room=400,
        location_factor=1.0,
        size_factor=1.0,
        condition_factor=1.0
    )
    
    print(f"Investment: €{by_room_analysis['investment']['total_investment']:,.2f}")
    print(f"  - Purchase: €{by_room_analysis['investment']['purchase_price']:,.2f}")
    print(f"  - Remodeling: €{by_room_analysis['investment']['remodeling_costs']:,.2f}")
    print(f"\nRent Estimate:")
    print(f"  - Per room/month: €{by_room_analysis['rent_estimate']['rent_per_room_monthly']:,.2f}")
    print(f"  - Total monthly: €{by_room_analysis['rent_estimate']['total_monthly_rent']:,.2f}")
    print(f"  - Annual (after vacancy): €{by_room_analysis['rent_estimate']['annual_rent_after_vacancy']:,.2f}")
    print(f"\nFinancial Metrics:")
    print(f"  - ROI: {by_room_analysis['financial_metrics']['metrics']['roi_percentage']:.2f}%")
    print(f"  - Net Yield: {by_room_analysis['financial_metrics']['metrics']['net_yield']:.2f}%")
    print(f"  - Monthly Net Income: €{by_room_analysis['financial_metrics']['net_income']['monthly_net_income']:,.2f}")
    print(f"  - Annual Net Income: €{by_room_analysis['financial_metrics']['net_income']['annual_net_income']:,.2f}")
    
    print("\n\n2. RENTING AS WHOLE APARTMENT:")
    print("-" * 70)
    whole_apt_analysis = finance_calc.calculate_comprehensive_analysis(
        rental_strategy="whole_apartment",
        base_rent_per_m2=12,
        location_factor=1.0,
        condition_factor=1.0
    )
    
    print(f"Investment: €{whole_apt_analysis['investment']['total_investment']:,.2f}")
    print(f"  - Purchase: €{whole_apt_analysis['investment']['purchase_price']:,.2f}")
    print(f"  - Remodeling: €{whole_apt_analysis['investment']['remodeling_costs']:,.2f}")
    print(f"\nRent Estimate:")
    print(f"  - Per m²/month: €{whole_apt_analysis['rent_estimate']['rent_per_m2_monthly']:,.2f}")
    print(f"  - Monthly: €{whole_apt_analysis['rent_estimate']['monthly_rent']:,.2f}")
    print(f"  - Annual (after vacancy): €{whole_apt_analysis['rent_estimate']['annual_rent_after_vacancy']:,.2f}")
    print(f"\nFinancial Metrics:")
    print(f"  - ROI: {whole_apt_analysis['financial_metrics']['metrics']['roi_percentage']:.2f}%")
    print(f"  - Net Yield: {whole_apt_analysis['financial_metrics']['metrics']['net_yield']:.2f}%")
    print(f"  - Monthly Net Income: €{whole_apt_analysis['financial_metrics']['net_income']['monthly_net_income']:,.2f}")
    print(f"  - Annual Net Income: €{whole_apt_analysis['financial_metrics']['net_income']['annual_net_income']:,.2f}")
