#!/usr/bin/env python3
"""
Direct test of LemonFox service functions
"""

import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, '/home/azureuser/ai_platform/backend')

# Set up logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Import the service
from app.services.lemonfox_service import transcribe_audio_with_timestamps

def test_lemonfox_service():
    """Test LemonFox service functions directly"""
    
    # Test file path
    audio_file_path = "/home/azureuser/ai_platform/test_audio.mp3"
    
    if not os.path.exists(audio_file_path):
        print(f"❌ Audio file not found: {audio_file_path}")
        return
    
    print(f"🎵 Testing LemonFox service with: {audio_file_path}")
    print(f"📊 File size: {os.path.getsize(audio_file_path):,} bytes")
    
    try:
        print("🚀 Calling transcribe_audio_with_timestamps...")
        result = transcribe_audio_with_timestamps(audio_file_path)
        
        print("✅ Transcription completed!")
        print(f"📝 Segments: {len(result.get('segments', []))}")
        print(f"📄 Full text length: {len(result.get('full_text', ''))}")
        
        # Show first few segments
        segments = result.get('segments', [])
        if segments:
            print("\n📋 First 3 segments:")
            for i, segment in enumerate(segments[:3]):
                print(f"  {i+1}. [{segment['start_seconds']:.2f}s - {segment['end_seconds']:.2f}s]: {segment['text'][:100]}...")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = test_lemonfox_service()
    if result:
        print(f"\n🎉 SUCCESS: Got {len(result.get('segments', []))} segments from LemonFox!")
