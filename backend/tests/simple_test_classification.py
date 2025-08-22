"""
Simple test for DivisionClassifier.request_classification method
Input an image URL and get a response
"""

import os
import sys

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from division_classifier import DivisionClassifier


def test_single_image_classification(image_url):
    """
    Test the classification of a single image
    
    Args:
        image_url (str): URL of the image to classify
    
    Returns:
        str: Classification result from OpenAI
    """
    try:
        # Initialize the classifier
        print("Initializing DivisionClassifier...")
        classifier = DivisionClassifier()
        
        # Request classification
        print(f"Requesting classification for image: {image_url}")
        result = classifier.request_classification([image_url])
        
        #print(f"\nClassification result:")
        #print(result)
        
        return result
        
    except Exception as e:
        print(f"Error during classification: {str(e)}")
        return None


if __name__ == "__main__":
    # You can change this URL to test with different images
    test_image_url = "https://img4.idealista.pt/blur/WEB_DETAIL/0/id.pro.pt.image.master/9a/c2/be/290881862.jpg"
    
    print("=== Simple Image Classification Test ===")
    print(f"Testing with image URL: {test_image_url}")
    print("=" * 50)
    
    # Run the test
    result = test_single_image_classification(test_image_url)
    
    if result:
        print("\n✅ Test completed successfully!")
        print(f"Result: {result}")
    else:
        print("\n❌ Test failed!")
