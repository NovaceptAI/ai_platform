#!/usr/bin/env python3
"""
Test script for image processing with AWS Textract
"""

import sys
import os
sys.path.append('/home/azureuser/ai_platform/backend')

from app.utils.file_utils import extract_text_from_image, detect_file_type

def test_image_processing(image_path):
    """Test image processing with a real image file"""
    print(f"Testing image processing for: {image_path}")
    
    # Check if file exists
    if not os.path.exists(image_path):
        print(f"❌ File not found: {image_path}")
        return
    
    # Detect file type
    try:
        file_type = detect_file_type(image_path)
        print(f"✓ Detected file type: {file_type}")
    except Exception as e:
        print(f"❌ File type detection failed: {e}")
        return
    
    # Extract text using AWS Textract
    try:
        # Make a copy since the function deletes the file
        import shutil
        temp_path = f"/tmp/test_image_{os.path.basename(image_path)}"
        shutil.copy2(image_path, temp_path)
        
        text_chunks = extract_text_from_image(temp_path)
        print(f"✓ Text extraction successful!")
        print(f"✓ Number of chunks: {len(text_chunks)}")
        
        for i, chunk in enumerate(text_chunks, 1):
            print(f"\n--- Chunk {i} ---")
            print(chunk[:200] + "..." if len(chunk) > 200 else chunk)
            
    except Exception as e:
        print(f"❌ Text extraction failed: {e}")

if __name__ == "__main__":
    # Set up environment variables for AWS
    os.environ['AWS_ACCESS_KEY_ID'] = 'AKIAUMXFDUFPRNGYU7XQ'
    os.environ['AWS_SECRET_ACCESS_KEY'] = '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'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    
    print("=== Image Processing Test ===")
    
    # You can test with any image file
    test_files = [
        "/path/to/your/test/image.jpg",
        "/path/to/your/test/document.png"
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            test_image_processing(test_file)
        else:
            print(f"Skipping {test_file} (file not found)")
    
    print("\n=== Test Complete ===")
