#!/usr/bin/env python3
"""
Test script to trigger audio processing via Celery task
"""

import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, '/home/azureuser/ai_platform/backend')

# Import the task
from app.tasks.summarizer_tasks import process_audio_video_file

def test_audio_processing():
    """Test audio processing with an existing audio file"""
    
    # Test file path
    audio_file_path = "/home/azureuser/ai_platform/test_audio.mp3"
    
    if not os.path.exists(audio_file_path):
        print(f"❌ Audio file not found: {audio_file_path}")
        return
    
    print(f"🎵 Testing audio processing with: {audio_file_path}")
    print(f"📊 File size: {os.path.getsize(audio_file_path):,} bytes")
    
    # Create a test uploaded file record (we'll use a mock ID)
    test_file_id = "test-audio-file-12345"
    
    print(f"🚀 Triggering Celery task: process_audio_video_file")
    print(f"📝 File ID: {test_file_id}")
    print(f"📂 File path: {audio_file_path}")
    
    # Trigger the Celery task
    try:
        result = process_audio_video_file.delay(test_file_id, audio_file_path)
        print(f"✅ Task submitted successfully!")
        print(f"🔗 Task ID: {result.id}")
        print(f"🕐 Task state: {result.state}")
        
        # Wait for result (with timeout)
        print("⏳ Waiting for task to complete...")
        final_result = result.get(timeout=600)  # 10 minutes timeout
        
        print("🎉 Task completed!")
        print(f"📊 Result: {final_result}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_audio_processing()
