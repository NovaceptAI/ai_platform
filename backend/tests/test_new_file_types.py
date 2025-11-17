#!/usr/bin/env python3
"""
Test script for new file type processing (images, PowerPoint, Excel)
"""

import sys
import os
sys.path.append('/home/azureuser/ai_platform/backend')

from app.utils.file_utils import detect_file_type, extract_text_by_pages

def test_file_type_detection():
    """Test file type detection for new formats"""
    print("Testing file type detection...")
    
    test_cases = [
        ('test.jpg', 'image'),
        ('test.png', 'image'),
        ('test.pptx', 'presentation'),
        ('test.xlsx', 'spreadsheet'),
        ('test.xls', 'spreadsheet'),
        ('test.pdf', 'document'),
        ('test.mp3', 'audio'),
        ('test.mp4', 'video')
    ]
    
    for filename, expected_type in test_cases:
        try:
            detected_type = detect_file_type(filename)
            status = "✓" if detected_type == expected_type else "✗"
            print(f"{status} {filename} -> {detected_type} (expected: {expected_type})")
        except Exception as e:
            print(f"✗ {filename} -> ERROR: {e}")

def test_import_dependencies():
    """Test if all new dependencies can be imported"""
    print("\nTesting dependency imports...")
    
    try:
        import boto3
        print("✓ boto3 imported successfully")
    except ImportError as e:
        print(f"✗ boto3 import failed: {e}")
    
    try:
        from pptx import Presentation
        print("✓ python-pptx imported successfully")
    except ImportError as e:
        print(f"✗ python-pptx import failed: {e}")
    
    try:
        import openpyxl
        print("✓ openpyxl imported successfully")
    except ImportError as e:
        print(f"✗ openpyxl import failed: {e}")
    
    try:
        from PIL import Image
        print("✓ Pillow imported successfully")
    except ImportError as e:
        print(f"✗ Pillow import failed: {e}")

def test_aws_credentials():
    """Test AWS credentials for Textract"""
    print("\nTesting AWS credentials...")
    
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = os.getenv('AWS_DEFAULT_REGION')
    
    if aws_access_key:
        print(f"✓ AWS_ACCESS_KEY_ID found: {aws_access_key[:10]}...")
    else:
        print("✗ AWS_ACCESS_KEY_ID not found in environment")
    
    if aws_secret_key:
        print(f"✓ AWS_SECRET_ACCESS_KEY found: {aws_secret_key[:10]}...")
    else:
        print("✗ AWS_SECRET_ACCESS_KEY not found in environment")
    
    if aws_region:
        print(f"✓ AWS_DEFAULT_REGION found: {aws_region}")
    else:
        print("✗ AWS_DEFAULT_REGION not found in environment")

if __name__ == "__main__":
    print("=== Testing New File Type Processing ===")
    test_file_type_detection()
    test_import_dependencies()
    test_aws_credentials()
    print("\n=== Test Complete ===")
