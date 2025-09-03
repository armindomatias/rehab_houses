""" 
    Apify Scraper for Idealista Listings
    
    - Cheaper than Standby one, not as fast as to be better
"""

# Import libraries
import requests
import json
from dotenv import load_dotenv
import os
import logging
import time
from datetime import datetime
import re

class ApifyIdealistaScraper:
    """
    A class to handle scraping of Idealista property listings using Apify actors
    """
    
    def __init__(self):
        """Initialize the scraper with environment variables and logging setup"""
        self.logger = self._setup_logging()
        self.logger.info("Initializing ApifyIdealistaScraper...")
        
        # Load environment variables
        self._load_environment_variables()
        
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
    
    def _setup_logging(self):
        """Setup logging configuration with both file and console handlers"""
        # Create logs directory if it doesn't exist
        #os.makedirs('logs', exist_ok=True)
        
        # Create a timestamp for the log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        #log_filename = f'logs/apify_idealista_scraper_{timestamp}.log'
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                #logging.FileHandler(log_filename),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    def _load_environment_variables(self):
        """Load and validate environment variables"""
        self.logger.info("Loading environment variables...")
        load_dotenv()
        
        self.apify_user_id = os.getenv("APIFY_USER_ID")
        self.apify_api_token = os.getenv("APIFY_API_TOKEN")
        self.actor_id = os.getenv("APIFY_ACTOR_ID")
        
        # Log environment variable status
        if self.apify_user_id:
            self.logger.info("APIFY_USER_ID loaded successfully")
        else:
            self.logger.warning("APIFY_USER_ID not found in environment variables")

        if self.apify_api_token:
            self.logger.info("APIFY_API_TOKEN loaded successfully")
        else:
            self.logger.error("APIFY_API_TOKEN not found in environment variables")

        if self.actor_id:
            self.logger.info(f"APIFY_ACTOR_ID loaded successfully: {self.actor_id}")
        else:
            self.logger.error("APIFY_ACTOR_ID not found in environment variables")
    
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
    
    def scrape_batch(self, url_listings: list, save_data: bool = True):
        """
        Scrape property data from multiple Idealista listings
        
        Args:
            url_listings (list): List of Idealista listing URLs to scrape
            save_data (bool): Whether to save the data to JSON files
            
        Returns:
            list: List of property data from the listings
        """
        self.logger.info(f"Starting batch scraping for {len(url_listings)} URLs")
        
        if not url_listings:
            self.logger.error("No URLs provided for batch scraping")
            return []
        
        if not self._validate_credentials():
            return []
        
        results = []
        
        for i, url in enumerate(url_listings, 1):
            self.logger.info(f"Processing URL {i}/{len(url_listings)}: {url}")
            try:
                result = self._make_api_request(url)
                if result:
                    results.append(result)
                    self.logger.info(f"Successfully scraped URL {i}/{len(url_listings)}")
                    
                    if save_data:
                        self.save_property_data(result, url)
                else:
                    self.logger.error(f"Failed to scrape URL {i}/{len(url_listings)}")
            except Exception as e:
                self.logger.error(f"Exception occurred while scraping URL {i}/{len(url_listings)}: {str(e)}")
                continue
        
        self.logger.info(f"Batch scraping completed. Successfully scraped {len(results)}/{len(url_listings)} URLs")
        return results
    
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
        "https://www.idealista.pt/imovel/34219509/",
    ]
    
    # Single URL mode
    scraper.logger.info("=== Testing Single URL Mode ===")
    single_result = scraper.scrape_single(url_listing = test_urls[0], save_data=True)
    if single_result:
        scraper.logger.info("Single URL scraping completed successfully")
    else:
        scraper.logger.error("Single URL scraping failed")
    
    scraper.logger.info("Script execution completed")