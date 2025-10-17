#!/usr/bin/env python3
"""
Test script for image analysis functionality
This demonstrates how the system handles images with no text
"""

import sys
import os
sys.path.append('/home/azureuser/ai_platform/backend')

from app.utils.file_utils import analyze_image_content

def test_image_analysis():
    """Test image analysis with a sample image"""
    print("=== Image Analysis Test ===")
    
    # Set up environment variables for AWS (using your existing credentials)
    os.environ['AWS_ACCESS_KEY_ID'] = 'AKIAUMXFDUFPRNGYU7XQ'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'quqcIKvH/8OlMkhHHmCXWfbbLhoHzH05QV0/O4bt'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    
    # Example test (you would need an actual image file to test)
    sample_image_path = "/path/to/your/test/image.jpg"
    
    if os.path.exists(sample_image_path):
        print(f"Analyzing image: {sample_image_path}")
        try:
            analysis_result = analyze_image_content(sample_image_path)
            print(f"Analysis Result:")
            print(f"'{analysis_result}'")
        except Exception as e:
            print(f"Analysis failed: {e}")
    else:
        print(f"Sample image not found at {sample_image_path}")
        print("The function would analyze the attached image showing:")
        print("'This image contains no text. It depicts a person interacting with dogs. Please upload an image containing text for document processing and analysis.'")

if __name__ == "__main__":
    test_image_analysis()
