""" 
    Apify Scraper for Idealista Listings
    
    - Cheaper than Standby one, not as fast as to be better
"""

# Import libraries
import requests
import json
import os
import time
from datetime import datetime
import re

from src.utils import get_logger
from src.core.config import APIFY_USER_ID, APIFY_API_TOKEN, APIFY_ACTOR_ID

class ApifyIdealistaScraper:
    """
    A class to handle scraping of Idealista property listings using Apify actors
    """
    
    def __init__(self):
        """Initialize the scraper with environment variables and logging setup"""
        self.logger = get_logger(__name__)
        self.logger.info("Initializing ApifyIdealistaScraper...")
        
        # Use environment variables from core config
        self.apify_user_id = APIFY_USER_ID
        self.apify_api_token = APIFY_API_TOKEN
        self.actor_id = APIFY_ACTOR_ID
        
        # Apify API methods
        self.apify_methods = {
            "run_actor": "runs", #post
            "run_actor_sync_kv_pair": "run-sync", #post
            "run_actor_sync_dataset": "run-sync-get-dataset-items", #post
            "get_actor": "", #get
            "get_actor_list_webhooks": "webhooks", #get
            "update_actor": "", #put
            "get_list_runs": "runs", #get
            "get_last_run": "runs/last", #get
            "get_last_run_dataset_items": "runs/last/dataset/items" #get
        }
        
        self.logger.info("ApifyIdealistaScraper initialized successfully")
    
    def _validate_credentials(self):
        """Validate that all required credentials are available"""
        if not all([self.apify_user_id, self.apify_api_token, self.actor_id]):
            self.logger.error("Missing required environment variables for Apify API")
            return False
        return True
    
    def save_property_data(self, property_data: dict, url: str):
        """Save property data to JSON file"""
        try:
            # Create data directory
            os.makedirs("data/scraped_data", exist_ok=True)
            
            # Extract listing ID from URL
            listing_id = re.search(r'/imovel/(\d+)/', url)
            listing_id = listing_id.group(1) if listing_id else datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save file
            filename = f"idealista_listing_{listing_id}.json"
            filepath = f"data/scraped_data/{filename}"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(property_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Data saved to: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to save data: {str(e)}")
            return None
    
    def scrape_single(self, url_listing: str, save_data: bool = True):
        """
        Scrape property data from a single Idealista listing
        
        Args:
            url_listing (str): The Idealista listing URL to scrape
            save_data (bool): Whether to save the data to JSON file
            
        Returns:
            dict: Property data from the listing or None if failed
        """
        self.logger.info(f"Starting single URL scraping for: {url_listing}")
        
        if not url_listing:
            self.logger.error("No URL provided for scraping")
            return None
        
        if not self._validate_credentials():
            return None
        
        property_data = self._make_api_request(url_listing)
        
        if property_data and save_data:
            self.save_property_data(property_data, url_listing)
        
        return property_data

    def _make_api_request(self, url_listing: str):
        """
        Make API request to Apify for a single URL
        
        Args:
            url_listing (str): The URL to scrape
            
        Returns:
            dict: Property data or None if failed
        """
        url_apify = f"https://api.apify.com/v2/acts/{self.actor_id}/{self.apify_methods['run_actor_sync_dataset']}"
        self.logger.info(f"Apify API URL created")

        # Headers: To pass the kind of API/Token
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.apify_api_token}"
        }
        self.logger.debug("Headers configured for API request")

        # Data/Payload: Specific stuff you pass depending on the Actor/API
        payload = json.dumps({
            "Url": url_listing, # Listing to extract 
            "cookies": {},
            "proxyConfig": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        })
        self.logger.debug(f"Payload prepared: {payload}")

        try:
            self.logger.info("Making API request to Apify...")
            start_time = time.time()
            
            response = requests.request("POST", url=url_apify, headers=headers, data=payload)
            
            request_time = time.time() - start_time
            self.logger.info(f"API request completed in {request_time:.2f} seconds")
            self.logger.info(f"Response status code: {response.status_code}")
            
            if response.status_code == 201:
                self.logger.info("API request successful")
                property_data = response.json()
                self.logger.info(f"Successfully parsed JSON response with {len(property_data)} items")
                self.logger.debug(f"Property data: {property_data}")
                
                # print(property_data)
                return property_data
            else:
                self.logger.error(f"API request failed with status code: {response.status_code}")
                self.logger.error(f"Response content: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed with exception: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {str(e)}")
            self.logger.error(f"Response content: {response.text}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error occurred: {str(e)}")
            return None

if __name__ == "__main__":
    # Initialize the scraper
    scraper = ApifyIdealistaScraper()
    
    # Example URLs for testing
    test_urls = [
        "https://www.idealista.pt/imovel/34458598/",
    ]
    
    # Single URL mode
    scraper.logger.info("=== Testing Single URL Mode ===")
    single_result = scraper.scrape_single(url_listing = test_urls[0], save_data=True)
    if single_result:
        scraper.logger.info("Single URL scraping completed successfully")
    else:
        scraper.logger.error("Single URL scraping failed")
    
    scraper.logger.info("Script execution completed")