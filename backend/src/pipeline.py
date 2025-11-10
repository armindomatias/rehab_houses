"""
PROPERTY ANALYSIS PIPELINE

GOAL => Orchestrate all services from scraping to finance calculation
"""

import os
import re
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from src.apify_idealista_scraper import ApifyIdealistaScraper
from src.idealista_data_manipulator import IdealistaDataManipulator
from src.division_classifier import DivisionClassifier
from src.deduplication import Deduplication
from src.rehab_calculator import PropertyRemodelingCalculator
from src.finance_calculator import PropertyFinanceCalculator


class PropertyAnalysisPipeline:
    """
    Orchestrates the complete property analysis pipeline:
    1. Scrape property data
    2. Extract gallery URLs
    3. Classify images
    4. Deduplicate classifications
    5. Calculate remodeling costs
    6. Calculate financial metrics
    """
    
    def __init__(self):
        """Initialize all services"""
        self.logger = self._setup_logging()
        self.logger.info("Initializing PropertyAnalysisPipeline...")
        
        # Initialize services
        self.scraper = ApifyIdealistaScraper()
        self.classifier = DivisionClassifier()
        self.deduplication = Deduplication()
        
        self.logger.info("PropertyAnalysisPipeline initialized successfully")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler()]
        )
        return logging.getLogger(__name__)
    
    def _extract_listing_id_from_url(self, url: str) -> Optional[str]:
        """Extract listing ID from Idealista URL"""
        match = re.search(r'/imovel/(\d+)/', url)
        if match:
            return match.group(1)
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
        """Step 1: Scrape property data from Idealista"""
        self.logger.info("=" * 60)
        self.logger.info("STEP 1: Scraping property data")
        self.logger.info("=" * 60)
        
        listing_data = self.scraper.scrape_single(link, save_data=save_intermediate)
        if not listing_data:
            raise ValueError("Failed to scrape property data")
        
        # Extract listing ID
        listing_id = self._extract_listing_id_from_data(listing_data)
        if not listing_id:
            listing_id = self._extract_listing_id_from_url(link)
        if not listing_id:
            raise ValueError("Could not extract listing ID from URL or data")
        
        pipeline_state['listing_id'] = listing_id
        pipeline_state['listing_data'] = listing_data
        pipeline_state['listing_json_path'] = f"data/scraped_data/idealista_listing_{listing_id}.json"
        
        self.logger.info(f"Successfully scraped listing {listing_id}")
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
    
    async def _classify_images(
        self,
        pipeline_state: Dict[str, Any],
        save_intermediate: bool,
        classification_concurrency: int
    ) -> Dict[str, Any]:
        """Step 3: Classify images using vision models"""
        self.logger.info("=" * 60)
        self.logger.info("STEP 3: Classifying images")
        self.logger.info("=" * 60)
        
        listing_id = pipeline_state['listing_id']
        gallery_items = pipeline_state['gallery_items']
        base_name = f"idealista_listing_{listing_id}"
        jsonl_name = f"{base_name}_classifications.jsonl"
        aggregated_name = f"{base_name}_classifications_aggregated.json"
        
        aggregated = await self.classifier.classify_images_concurrently(
            gallery_items=gallery_items,
            listing_id=listing_id,
            output_jsonl_filename=jsonl_name if save_intermediate else None,
            output_aggregated_filename=aggregated_name if save_intermediate else None,
            max_concurrency=classification_concurrency,
        )
        
        if not aggregated:
            raise ValueError("Image classification failed or returned no results")
        
        pipeline_state['classification_aggregated_path'] = (
            f"data/image_analysis/{listing_id}/{aggregated_name}"
        )
        self.logger.info(f"Classified images into {len(aggregated)} room types")
        return pipeline_state
    
    def _deduplicate_classifications(
        self,
        pipeline_state: Dict[str, Any],
        deduplication_threshold: int
    ) -> Dict[str, Any]:
        """Step 4: Deduplicate and aggregate classifications"""
        self.logger.info("=" * 60)
        self.logger.info("STEP 4: Deduplicating classifications")
        self.logger.info("=" * 60)
        
        listing_id = pipeline_state['listing_id']
        base_name = f"idealista_listing_{listing_id}"
        
        dedup_path = self.deduplication.deduplicate_aggregated_results(
            aggregated_input_path=pipeline_state['classification_aggregated_path'],
            listing_json_path=pipeline_state['listing_json_path'],
            listing_id=listing_id,
            output_filename=f"{base_name}_classifications_dedup.json",
            distance_threshold=deduplication_threshold,
        )
        
        pipeline_state['classification_dedup_path'] = dedup_path
        self.logger.info(f"Deduplication complete: {dedup_path}")
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
        
        dedup_path = pipeline_state['classification_dedup_path']
        rehab_calc = PropertyRemodelingCalculator(dedup_path)
        
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
        dedup_path = pipeline_state['classification_dedup_path']
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
            classification_json_path=dedup_path,
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
    
    def _compile_result(
        self,
        pipeline_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compile final result from pipeline state"""
        finance_analysis = pipeline_state['finance_analysis']
        rehab_costs = pipeline_state['rehab_costs']
        listing_id = pipeline_state['listing_id']
        dedup_path = pipeline_state['classification_dedup_path']
        
        # Load deduplicated classification data to get images per division
        divisions_with_images = {}
        try:
            with open(dedup_path, 'r', encoding='utf-8') as f:
                dedup_data = json.load(f)
            
            # Create a map of division_id to images
            # Skip views, house plans, and common areas
            for room_type, divisions in dedup_data.items():
                if room_type in ["views", "house_plan", "common_areas"]:
                    continue
                for division in divisions:
                    division_id = division.get('division_id', 'unknown')
                    divisions_with_images[division_id] = {
                        'images': division.get('images', []),
                        'room_type': division.get('room_type', room_type),
                        'size_m2': division.get('size_m2', 0),
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
            self.logger.warning(f"Could not load division images: {e}")
        
        # Merge images with rehab costs per division
        divisions_with_costs = {}
        for room_type, rooms in rehab_costs.get('rooms', {}).items():
            for room in rooms:
                division_id = room.get('division_id', 'unknown')
                division_info = divisions_with_images.get(division_id, {})
                
                divisions_with_costs[division_id] = {
                    'division_id': division_id,
                    'room_type': room.get('room_type', room_type),
                    'size_m2': room.get('size_m2', division_info.get('size_m2', 0)),
                    'images': division_info.get('images', []),
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
                'classification_dedup_path': pipeline_state['classification_dedup_path'],
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
                - classification_concurrency: int (default: 5) - Max concurrent classifications
                - deduplication_threshold: int (default: 15) - Image similarity threshold
                - rehab_options: dict - Options for rehab calculator
                - finance_options: dict - Options for finance calculator
        
        Returns:
            Dictionary with complete analysis results
        """
        if options is None:
            options = {}
        
        # Default options
        save_intermediate = options.get('save_intermediate', True)
        classification_concurrency = options.get('classification_concurrency', 5)
        deduplication_threshold = options.get('deduplication_threshold', 15)
        rehab_options = options.get('rehab_options', {})
        finance_options = options.get('finance_options', {})
        
        pipeline_state = {
            'link': link,
            'listing_id': None,
            'listing_data': None,
            'listing_json_path': None,
            'gallery_items': None,
            'classification_aggregated_path': None,
            'classification_dedup_path': None,
            'rehab_costs': None,
            'finance_analysis': None,
            'errors': []
        }
        
        try:
            # Step 1: Scrape property data
            pipeline_state = self._scrape_property_data(link, save_intermediate, pipeline_state)
            
            # Step 2: Extract gallery URLs
            pipeline_state = self._extract_gallery_urls(pipeline_state)
            
            # Step 3: Classify images
            pipeline_state = await self._classify_images(
                pipeline_state, save_intermediate, classification_concurrency
            )
            
            # Step 4: Deduplicate classifications
            pipeline_state = self._deduplicate_classifications(
                pipeline_state, deduplication_threshold
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
        'classification_concurrency': 5,
        'deduplication_threshold': 15,
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

