#!/usr/bin/env python3
"""
Test script for the IdealistaDataManipulator class.
This demonstrates how to use the class to manipulate JSON data from Idealista listings.
"""

from src.gallery_extractor import IdealistaDataManipulator


def main():
    # Test with the existing JSON file
    json_file_path = "data/scraped_data/idealista_listing_34357924.json"
    
    print("=== Testing IdealistaDataManipulator ===\n")
    
    try:
        # Create an instance of the manipulator
        manipulator = IdealistaDataManipulator(json_file_path)
        
        # Test 1: Basic listing information
        print("1. Basic listing information:")
        print(f"   ID: {manipulator.get_listing_id()}")
        print(f"   Title: {manipulator.get_listing_title()}")
        print(f"   Price: {manipulator.get_listing_price()}")
        print(f"   Location: {manipulator.get_listing_location()}")
        
        print()
        
        # Test 2: Gallery extraction (main method)
        print("2. Gallery extraction using main method:")
        try:
            urls = manipulator.extract_gallery_urls()
            print(f"   ✓ Successfully extracted {len(urls)} image URLs")
            print(f"   First URL: {urls[0]}")
            print(f"   Last URL: {urls[-1]}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        print()
        
        # Test 3: Safe gallery extraction
        print("3. Gallery extraction using safe method:")
        urls_safe = manipulator.extract_gallery_urls_safe()
        if urls_safe:
            print(f"   ✓ Safe extraction successful: {len(urls_safe)} URLs")
        else:
            print("   ✗ Safe extraction failed")
        
        print()
        
        # Test 4: Show all URLs
        print("4. All extracted image URLs:")
        try:
            urls = manipulator.extract_gallery_urls()
            for i, url in enumerate(urls, 1):
                print(f"   {i:2d}. {url}")
        except Exception as e:
            print(f"   Error: {e}")
        
        print()
        
        # Test 5: Get all data
        print("5. All listing data keys:")
        all_data = manipulator.get_all_data()
        if all_data:
            print(f"   Available keys: {list(all_data.keys())}")
            print(f"   Total keys: {len(all_data)}")
        else:
            print("   ✗ Failed to get all data")
            
    except Exception as e:
        print(f"Error creating manipulator: {e}")


if __name__ == "__main__":
    main()
