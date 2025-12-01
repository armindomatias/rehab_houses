"""
PROPERTY ANALYSIS PIPELINE

GOAL => Orchestrate all services from scraping to finance calculation
"""

import os
import re
import json
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from src.idealista_scraper.apify_idealista_scraper import ApifyIdealistaScraper
from src.idealista_scraper.idealista_data_manipulator import IdealistaDataManipulator
from src.division_grouper.image_grouping_pipeline import ImageGroupingPipeline
from src.division_classifier.division_classifier import DivisionClassifier
from src.calculators.rehab_calculator import PropertyRemodelingCalculator
from src.calculators.finance_calculator import PropertyFinanceCalculator
from src.utils import get_logger


class PropertyAnalysisPipeline:
    """
    Orchestrates the complete property analysis pipeline:
    1. Scrape property data
    2. Extract gallery URLs
    3. Group images by division (signature-based)
    4. Classify images
    5. Calculate remodeling costs
    6. Calculate financial metrics
    """
    
    def __init__(self):
        """Initialize all services"""
        self.logger = get_logger(__name__)
        self.logger.info("Initializing PropertyAnalysisPipeline...")
        
        # Initialize services
        self.scraper = ApifyIdealistaScraper()
        # ImageGroupingPipeline will be initialized with parameters in _group_images
        self.image_grouping_pipeline = None
        self.classifier = DivisionClassifier()
        
        self.logger.info("PropertyAnalysisPipeline initialized successfully")
    
    def _extract_listing_id_from_url(self, url: str) -> Optional[str]:
        """Extract listing ID from Idealista URL"""
        match = re.search(r'/imovel/(\d+)/', url)
        if match:
            return match.group(1)
        return None
    
    def _check_local_listing_data(self, listing_id: str) -> Optional[Dict[str, Any]]:
        """
        Check if listing data exists locally and load it.
        
        Args:
            listing_id: The listing ID to check
        
        Returns:
            Listing data dict if found, None otherwise
        """
        json_path = f"data/scraped_data/idealista_listing_{listing_id}.json"
        
        if os.path.exists(json_path):
            try:
                self.logger.info(f"Found local listing data at: {json_path}")
                with open(json_path, 'r', encoding='utf-8') as f:
                    listing_data = json.load(f)
                self.logger.info("Successfully loaded local listing data")
                return listing_data
            except (FileNotFoundError, json.JSONDecodeError) as e:
                self.logger.warning(f"Failed to load local listing data: {e}")
                return None
        
        return None
    
    def _extract_listing_id_from_data(self, listing_data: Dict[str, Any]) -> Optional[str]:
        """Extract listing ID from scraped data"""
        if isinstance(listing_data, list) and len(listing_data) > 0:
            return listing_data[0].get('id')
        elif isinstance(listing_data, dict):
            return listing_data.get('id')
        return None
    
    def _scrape_property_data(
        self,
        link: str,
        save_intermediate: bool,
        pipeline_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Step 1: Load or scrape property data from Idealista"""
        self.logger.info("=" * 60)
        self.logger.info("STEP 1: Loading/Scraping property data")
        self.logger.info("=" * 60)
        
        # First, try to extract listing ID from URL to check local database
        listing_id = self._extract_listing_id_from_url(link)
        
        # Check local database first
        listing_data = None
        if listing_id:
            listing_data = self._check_local_listing_data(listing_id)
            if listing_data:
                self.logger.info(f"Using local listing data for ID: {listing_id}")
        
        # If not found locally, scrape
        if not listing_data:
            self.logger.info(f"Listing not found locally, scraping URL: {link}")
            listing_data = self.scraper.scrape_single(link, save_data=save_intermediate)
            
            if not listing_data:
                error_msg = (
                    "Failed to scrape property data. Possible reasons:\n"
                    "  - Invalid or inaccessible URL\n"
                    "  - Missing or invalid Apify API credentials\n"
                    "  - API request failed (check Apify actor status)\n"
                    "  - Network connectivity issues"
                )
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Extract listing ID from scraped data if we didn't have it from URL
            if not listing_id:
                listing_id = self._extract_listing_id_from_data(listing_data)
            
            # Log what we got
            if isinstance(listing_data, list):
                self.logger.info(f"Received list with {len(listing_data)} items")
            elif isinstance(listing_data, dict):
                self.logger.info("Received dict with listing data")
            else:
                self.logger.warning(f"Received unexpected data type: {type(listing_data)}")
        
        # Ensure we have a listing ID
        if not listing_id:
            listing_id = self._extract_listing_id_from_data(listing_data)
        
        if not listing_id:
            error_msg = (
                "Could not extract listing ID from URL or data. "
                f"URL: {link}, Data type: {type(listing_data)}"
            )
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        pipeline_state['listing_id'] = listing_id
        pipeline_state['listing_data'] = listing_data
        pipeline_state['listing_json_path'] = f"data/scraped_data/idealista_listing_{listing_id}.json"
        
        self.logger.info(f"Successfully loaded/scraped listing {listing_id}")
        return pipeline_state
    
    def _extract_gallery_urls(
        self,
        pipeline_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Step 2: Extract gallery URLs from scraped data"""
        self.logger.info("=" * 60)
        self.logger.info("STEP 2: Extracting gallery URLs")
        self.logger.info("=" * 60)
        
        manipulator = IdealistaDataManipulator(pipeline_state['listing_json_path'])
        gallery_items = manipulator.extract_gallery_urls()
        
        if not gallery_items:
            raise ValueError("No gallery images found")
        
        pipeline_state['gallery_items'] = gallery_items
        self.logger.info(f"Extracted {len(gallery_items)} gallery images")
        return pipeline_state
    
    async def _group_images(
        self,
        pipeline_state: Dict[str, Any],
        grouping_concurrency: int,
        signature_similarity_threshold: float
    ) -> Dict[str, Any]:
        """Step 3: Group images by division using room signatures"""
        self.logger.info("=" * 60)
        self.logger.info("STEP 3: Grouping images by division")
        self.logger.info("=" * 60)
        
        listing_id = pipeline_state['listing_id']
        gallery_items = pipeline_state['gallery_items']
        listing_data = pipeline_state['listing_data']
        
        # Initialize pipeline with concurrency and threshold parameters
        self.image_grouping_pipeline = ImageGroupingPipeline(
            max_concurrency=grouping_concurrency,
            signature_similarity_threshold=signature_similarity_threshold
        )
        
        grouped = await self.image_grouping_pipeline.process(
            gallery_items=gallery_items,
            listing_data=listing_data,
            listing_id=listing_id
        )
        
        if not grouped:
            self.logger.warning("Image grouping returned no results, continuing with ungrouped images")
        
        pipeline_state['image_grouping'] = grouped
        self.logger.info(f"Grouped images into {sum(len(v) for v in grouped.values())} divisions")
        return pipeline_state
    
    async def _classify_images(
        self,
        pipeline_state: Dict[str, Any],
        save_intermediate: bool,
        classification_concurrency: int
    ) -> Dict[str, Any]:
        """Step 4: Classify divisions (groups of images) using vision models"""
        self.logger.info("=" * 60)
        self.logger.info("STEP 4: Classifying divisions")
        self.logger.info("=" * 60)
        
        listing_id = pipeline_state['listing_id']
        image_grouping = pipeline_state.get('image_grouping', {})
        
        if not image_grouping:
            raise ValueError("No image grouping data available. Run image grouping step first.")
        
        base_name = f"idealista_listing_{listing_id}"
        jsonl_name = f"{base_name}_classifications.jsonl"
        aggregated_name = f"{base_name}_classifications_aggregated.json"
        
        # Classify divisions (groups of images) instead of individual images
        aggregated = await self.classifier.classify_divisions_concurrently(
            image_grouping=image_grouping,
            listing_id=listing_id,
            output_jsonl_filename=jsonl_name if save_intermediate else None,
            output_aggregated_filename=aggregated_name if save_intermediate else None,
            max_concurrency=classification_concurrency,
        )
        
        if not aggregated:
            raise ValueError("Division classification failed or returned no results")
        
        classification_path = (
            f"data/image_analysis/{listing_id}/{aggregated_name}"
        )
        pipeline_state['classification_path'] = classification_path
        pipeline_state['classification_aggregated_path'] = classification_path  # Keep for backward compatibility
        self.logger.info(f"Classified {sum(len(v) for v in aggregated.values())} divisions into {len(aggregated)} room types")
        return pipeline_state
    
    def _calculate_remodeling_costs(
        self,
        pipeline_state: Dict[str, Any],
        rehab_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Step 5: Calculate remodeling costs"""
        self.logger.info("=" * 60)
        self.logger.info("STEP 5: Calculating remodeling costs")
        self.logger.info("=" * 60)
        
        classification_path = pipeline_state['classification_path']
        rehab_calc = PropertyRemodelingCalculator(classification_path)
        
        # Default rehab options
        default_rehab_options = {
            'windows': False,
            'flooring': True,
            'painting': True,
            'plumbing': False,
            'electrical': False,
            'appliances': False,
            'ceiling': False,
            'quality_level': 'midend',
            'include_workforce': True,
        }
        default_rehab_options.update(rehab_options)
        
        rehab_costs = rehab_calc.calculate_remodeling_costs(**default_rehab_options)
        pipeline_state['rehab_costs'] = rehab_costs
        
        self.logger.info(f"Total remodeling cost: €{rehab_costs['property_total']:,.2f}")
        return pipeline_state
    
    def _calculate_financial_metrics(
        self,
        pipeline_state: Dict[str, Any],
        finance_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Step 6: Calculate financial metrics"""
        self.logger.info("=" * 60)
        self.logger.info("STEP 6: Calculating financial metrics")
        self.logger.info("=" * 60)
        
        listing_data = pipeline_state['listing_data']
        classification_path = pipeline_state['classification_path']
        rehab_costs = pipeline_state['rehab_costs']
        
        # Extract purchase price from listing data
        purchase_price = None
        if isinstance(listing_data, list) and len(listing_data) > 0:
            price_str = listing_data[0].get('price', '')
        elif isinstance(listing_data, dict):
            price_str = listing_data.get('price', '')
        else:
            price_str = ''
        
        # Try to extract numeric price
        if price_str:
            price_match = re.search(r'(\d+(?:[.,]\d+)?)', str(price_str).replace(',', ''))
            if price_match:
                purchase_price = float(price_match.group(1))
        
        if not purchase_price:
            # Default to a reasonable value or raise error
            self.logger.warning("Could not extract purchase price, using default")
            purchase_price = 300000  # Default fallback
        
        finance_calc = PropertyFinanceCalculator(
            purchase_price=purchase_price,
            remodeling_costs=rehab_costs['property_total'],
            listing_json_path=pipeline_state['listing_json_path'],
            classification_json_path=classification_path,
        )
        
        # Default finance options
        default_finance_options = {
            'rental_strategy': 'whole_apartment',
            'base_rent_per_room': 400,
            'base_rent_per_m2': 12,
            'location_factor': 1.0,
            'size_factor': 1.0,
            'condition_factor': 1.0,
            'monthly_expenses': 0,
            'property_tax_rate': 0.003,
            'insurance_rate': 0.002,
            'maintenance_rate': 0.01,
            'management_fee_rate': 0.08,
        }
        default_finance_options.update(finance_options)
        
        finance_analysis = finance_calc.calculate_comprehensive_analysis(**default_finance_options)
        pipeline_state['finance_analysis'] = finance_analysis
        
        self.logger.info(f"ROI: {finance_analysis['financial_metrics']['metrics']['roi_percentage']:.2f}%")
        self.logger.info(f"Net Yield: {finance_analysis['financial_metrics']['metrics']['net_yield']:.2f}%")
        return pipeline_state
    
    def _extract_size_m2(self, classification: Dict[str, Any]) -> float:
        """
        Extract size in m² from classification data.
        Tries multiple fields: size_m2, length_m * width_m, or size_m2_range.
        """
        # Direct size_m2 field
        if 'size_m2' in classification and classification['size_m2']:
            return float(classification['size_m2'])
        
        # Calculate from length and width
        length = classification.get('length_m')
        width = classification.get('width_m')
        if length and width:
            try:
                return float(length) * float(width)
            except (ValueError, TypeError):
                pass
        
        # Parse from size_m2_range (e.g., "5-7" -> 6)
        size_range = classification.get('size_m2_range', '')
        if size_range:
            match = re.search(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)', str(size_range))
            if match:
                try:
                    min_size = float(match.group(1))
                    max_size = float(match.group(2))
                    return (min_size + max_size) / 2  # Average
                except (ValueError, TypeError):
                    pass
        
        return 0.0
    
    def _compile_result(
        self,
        pipeline_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compile final result from pipeline state"""
        finance_analysis = pipeline_state['finance_analysis']
        rehab_costs = pipeline_state['rehab_costs']
        listing_id = pipeline_state['listing_id']
        classification_path = pipeline_state['classification_path']
        
        # Load classification data - now it contains divisions with their images already grouped
        divisions_with_classification = {}
        try:
            with open(classification_path, 'r', encoding='utf-8') as f:
                classification_data = json.load(f)
            
            # Classification data is now organized by room_type -> list of divisions
            # Each division already has: division_id, room_type, images, and classification metadata
            for room_type, divisions in classification_data.items():
                if room_type in ["views", "house_plan", "common_areas", "unknown"]:
                    continue
                for division in divisions:
                    division_id = division.get('division_id', 'unknown')
                    divisions_with_classification[division_id] = {
                        'division_id': division_id,
                        'room_type': division.get('room_type', room_type),
                        'images': division.get('images', []),  # Already grouped images from image_grouping
                        'size_m2': self._extract_size_m2(division),
                        'detailed_notes': division.get('detailed_notes', ''),
                        'conditions': {
                            'overall_condition': division.get('overall_condition'),
                            'flooring_condition': division.get('flooring_condition'),
                            'painting_condition': division.get('painting_condition'),
                            'windows_condition': division.get('windows_condition'),
                            'plumbing_condition': division.get('plumbing_condition'),
                            'electrical_condition': division.get('electrical_condition'),
                            'appliances_condition': division.get('appliances_condition'),
                            'ceiling_condition': division.get('ceiling_condition'),
                        }
                    }
        except Exception as e:
            self.logger.warning(f"Could not load classification data: {e}")
            divisions_with_classification = {}
        
        # Merge classification data with rehab costs per division
        divisions_with_costs = {}
        for room_type, rooms in rehab_costs.get('rooms', {}).items():
            for room in rooms:
                division_id = room.get('division_id', 'unknown')
                division_info = divisions_with_classification.get(division_id, {})
                
                divisions_with_costs[division_id] = {
                    'division_id': division_id,
                    'room_type': room.get('room_type', room_type),
                    'size_m2': room.get('size_m2', division_info.get('size_m2', 0)),
                    'images': division_info.get('images', []),  # Grouped images from image_grouping
                    'costs': room.get('costs', {}),
                    'total_cost': room.get('total', 0),
                    'detailed_notes': division_info.get('detailed_notes', ''),
                    'conditions': division_info.get('conditions', {}),
                }
        
        return {
            'success': True,
            'listing_id': listing_id,
            'property_info': finance_analysis.get('property_info', {}),
            'investment': finance_analysis.get('investment', {}),
            'rehab_costs': {
                'property_total': rehab_costs.get('property_total', 0),
                'summary': rehab_costs.get('summary', {}),
                'divisions': list(divisions_with_costs.values()),
            },
            'rent_estimate': finance_analysis.get('rent_estimate', {}),
            'financial_metrics': finance_analysis.get('financial_metrics', {}),
            'pipeline_state': {
                'listing_json_path': pipeline_state['listing_json_path'],
                'classification_path': pipeline_state['classification_path'],
            }
        }
    
    async def run(
        self,
        link: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run the complete analysis pipeline
        
        Args:
            link: Idealista property listing URL
            options: Configuration options for the pipeline:
                - save_intermediate: bool (default: True) - Save intermediate results
                - grouping_concurrency: int (default: 3) - Max concurrent grouping requests
                - signature_similarity_threshold: float (default: 0.5) - Signature similarity threshold
                - classification_concurrency: int (default: 5) - Max concurrent classifications
                - rehab_options: dict - Options for rehab calculator
                - finance_options: dict - Options for finance calculator
        
        Returns:
            Dictionary with complete analysis results
        """
        if options is None:
            options = {}
        
        # Default options
        save_intermediate = options.get('save_intermediate', True)
        grouping_concurrency = options.get('grouping_concurrency', 3)
        signature_similarity_threshold = options.get('signature_similarity_threshold', 0.5)
        classification_concurrency = options.get('classification_concurrency', 5)
        rehab_options = options.get('rehab_options', {})
        finance_options = options.get('finance_options', {})
        
        pipeline_state = {
            'link': link,
            'listing_id': None,
            'listing_data': None,
            'listing_json_path': None,
            'gallery_items': None,
            'image_grouping': None,
            'classification_path': None,
            'classification_aggregated_path': None,  # Keep for backward compatibility
            'rehab_costs': None,
            'finance_analysis': None,
            'errors': []
        }
        
        try:
            # Step 1: Scrape property data
            pipeline_state = self._scrape_property_data(link, save_intermediate, pipeline_state)
            
            # Step 2: Extract gallery URLs
            pipeline_state = self._extract_gallery_urls(pipeline_state)
            
            # Step 3: Group images by division
            pipeline_state = await self._group_images(
                pipeline_state, grouping_concurrency, signature_similarity_threshold
            )
            
            # Step 4: Classify images
            pipeline_state = await self._classify_images(
                pipeline_state, save_intermediate, classification_concurrency
            )
            
            # Step 5: Calculate remodeling costs
            pipeline_state = self._calculate_remodeling_costs(pipeline_state, rehab_options)
            
            # Step 6: Calculate financial metrics
            pipeline_state = self._calculate_financial_metrics(pipeline_state, finance_options)
            
            # Compile final result
            self.logger.info("=" * 60)
            self.logger.info("PIPELINE COMPLETE")
            self.logger.info("=" * 60)
            
            return self._compile_result(pipeline_state)
            
        except Exception as e:
            self.logger.error(f"Pipeline error: {str(e)}", exc_info=True)
            pipeline_state['errors'].append(str(e))
            
            return {
                'success': False,
                'error': str(e),
                'pipeline_state': pipeline_state,
            }
    
    async def analyze(
        self,
        link: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Public API method - runs the complete analysis pipeline
        
        This is an alias for run() to maintain backward compatibility
        """
        return await self.run(link, options)


# Example usage
if __name__ == "__main__":
    pipeline = PropertyAnalysisPipeline()
    
    test_url = "https://www.idealista.pt/imovel/34458598/"
    
    options = {
        'save_intermediate': True,
        'grouping_concurrency': 3,
        'signature_similarity_threshold': 0.5,
        'classification_concurrency': 5,
        'rehab_options': {
            'flooring': True,
            'painting': True,
            'quality_level': 'midend',
        },
        'finance_options': {
            'rental_strategy': 'whole_apartment',
            'base_rent_per_m2': 12,
        }
    }
    
    result = asyncio.run(pipeline.run(test_url, options))
    
    if result['success']:
        print("\n" + "=" * 70)
        print("ANALYSIS RESULTS")
        print("=" * 70)
        print(f"Listing ID: {result['listing_id']}")
        print(f"\nInvestment: €{result['investment']['total_investment']:,.2f}")
        print(f"  - Purchase: €{result['investment']['purchase_price']:,.2f}")
        print(f"  - Remodeling: €{result['investment']['remodeling_costs']:,.2f}")
        print(f"\nRemodeling Costs: €{result['rehab_costs']['property_total']:,.2f}")
        print(f"\nROI: {result['financial_metrics']['metrics']['roi_percentage']:.2f}%")
        print(f"Net Yield: {result['financial_metrics']['metrics']['net_yield']:.2f}%")
        print(f"Monthly Net Income: €{result['financial_metrics']['net_income']['monthly_net_income']:,.2f}")
    else:
        print(f"Pipeline failed: {result.get('error')}")

