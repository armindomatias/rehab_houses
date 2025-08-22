import json
from typing import List, Optional, Dict, Any


class IdealistaDataManipulator:
    """
    A class to manipulate data from Idealista JSON listing files.
    This class provides methods to extract and process various data fields
    from the JSON structure used by Idealista scrapers.
    """
    
    def __init__(self, json_file_path: str):
        """
        Initialize the manipulator with a JSON file path.
        
        Args:
            json_file_path (str): Path to the JSON file to manipulate
        """
        self.json_file_path = json_file_path
        self._data = None
        self._is_loaded = False
    
    def _load_data(self) -> None:
        """
        Load and parse the JSON data from the file.
        This method is called automatically when needed.
        
        Raises:
            FileNotFoundError: If the JSON file doesn't exist
            json.JSONDecodeError: If the file contains invalid JSON
        """
        if not self._is_loaded:
            try:
                with open(self.json_file_path, 'r', encoding='utf-8') as file:
                    self._data = json.load(file)
                self._is_loaded = True
            except FileNotFoundError:
                raise FileNotFoundError(f"JSON file not found: {self.json_file_path}")
            except json.JSONDecodeError as e:
                raise json.JSONDecodeError(f"Invalid JSON format: {e}", e.doc, e.pos)
    
    def _get_listing_data(self) -> Dict[str, Any]:
        """
        Get the actual listing data, handling the JSON structure.
        
        Returns:
            Dict[str, Any]: The listing data dictionary
            
        Raises:
            KeyError: If the data structure is unexpected
        """
        self._load_data()
        
        # Handle the JSON structure (array containing listing object)
        if isinstance(self._data, list) and len(self._data) > 0:
            return self._data[0]
        elif isinstance(self._data, dict):
            return self._data
        else:
            raise KeyError("Unexpected JSON structure: expected list or dict")
    
    def extract_gallery_urls(self) -> List[str]:
        """
        Extract all image URLs from the 'gallery' section.
        
        Returns:
            List[str]: List of image URLs from the gallery
            
        Raises:
            KeyError: If the 'gallery' key doesn't exist in the JSON
        """
        listing_data = self._get_listing_data()
        
        if 'gallery' not in listing_data:
            raise KeyError("'gallery' key not found in the JSON file")
        
        gallery = listing_data['gallery']
        
        # Extract URLs from gallery items
        urls = []
        for item in gallery:
            if isinstance(item, dict) and 'url' in item:
                urls.append(item['url'])
        
        return urls
    
    def extract_gallery_urls_safe(self) -> Optional[List[str]]:
        """
        Safe version of extract_gallery_urls that returns None instead of raising exceptions.
        
        Returns:
            Optional[List[str]]: List of image URLs from the gallery, or None if an error occurs
        """
        try:
            return self.extract_gallery_urls()
        except Exception:
            return None
    
    def get_listing_id(self) -> Optional[str]:
        """
        Get the listing ID from the JSON data.
        
        Returns:
            Optional[str]: The listing ID, or None if not found
        """
        try:
            listing_data = self._get_listing_data()
            return listing_data.get('id')
        except Exception:
            return None
    
    def get_listing_title(self) -> Optional[str]:
        """
        Get the listing title from the JSON data.
        
        Returns:
            Optional[str]: The listing title, or None if not found
        """
        try:
            listing_data = self._get_listing_data()
            return listing_data.get('title')
        except Exception:
            return None
    
    def get_listing_price(self) -> Optional[str]:
        """
        Get the listing price from the JSON data.
        
        Returns:
            Optional[str]: The listing price, or None if not found
        """
        try:
            listing_data = self._get_listing_data()
            return listing_data.get('price')
        except Exception:
            return None
    
    def get_listing_location(self) -> Optional[str]:
        """
        Get the listing location from the JSON data.
        
        Returns:
            Optional[str]: The listing location, or None if not found
        """
        try:
            listing_data = self._get_listing_data()
            return listing_data.get('location')
        except Exception:
            return None
    
    def get_all_data(self) -> Optional[Dict[str, Any]]:
        """
        Get all the listing data as a dictionary.
        
        Returns:
            Optional[Dict[str, Any]]: All listing data, or None if an error occurs
        """
        try:
            return self._get_listing_data()
        except Exception:
            return None


# Example usage and testing
if __name__ == "__main__":
    # Example file path
    file_path = "data/scraped_data/idealista_listing_34357924.json"
    
    try:
        # Create an instance of the manipulator
        manipulator = IdealistaDataManipulator(file_path)
        
        print("=== Testing IdealistaDataManipulator ===\n")
        
        # Test basic info extraction
        print("1. Basic listing information:")
        print(f"   ID: {manipulator.get_listing_id()}")
        print(f"   Title: {manipulator.get_listing_title()}")
        print(f"   Price: {manipulator.get_listing_price()}")
        print(f"   Location: {manipulator.get_listing_location()}")
        
        print()
        
        # Test gallery extraction
        print("2. Gallery extraction:")
        urls = manipulator.extract_gallery_urls()
        print(f"   ✓ Successfully extracted {len(urls)} image URLs")
        print(f"   First URL: {urls[0]}")
        print(f"   Last URL: {urls[-1]}")
        
        print()
        
        # Test safe extraction
        print("3. Safe gallery extraction:")
        urls_safe = manipulator.extract_gallery_urls_safe()
        if urls_safe:
            print(f"   ✓ Safe extraction successful: {len(urls_safe)} URLs")
        else:
            print("   ✗ Safe extraction failed")
            
    except Exception as e:
        print(f"Error: {e}")
