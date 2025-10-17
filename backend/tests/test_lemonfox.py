#!/usr/bin/env python3
"""
Standalone test script for LemonFox AI transcription service
This script tests the LemonFox API independently without the full Flask app
"""

import requests
import json
import time
import os
from typing import List, Dict, Any

# LemonFox AI Configuration
LEMONFOX_API_KEY = "rk61hEoE7P1WYvymUqCsIicLySY4KUYj"
LEMONFOX_BASE_URL = "https://api.lemonfox.ai"

def test_lemonfox_transcription(audio_file_path: str) -> Dict[str, Any]:
    """
    Test LemonFox AI transcription with a local audio file
    """
    print(f"🎵 Testing LemonFox AI transcription with file: {audio_file_path}")
    
    # Check if file exists
    if not os.path.exists(audio_file_path):
        print(f"❌ Error: Audio file not found at {audio_file_path}")
        return {"error": "File not found"}
    
    # Get file size
    file_size = os.path.getsize(audio_file_path)
    print(f"📊 File size: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")
    
    try:
        # Step 1: Upload file to LemonFox
        print("\n📤 Step 1: Uploading file to LemonFox AI...")
        
        upload_headers = {
            "Authorization": f"Bearer {LEMONFOX_API_KEY}",
        }
        
        with open(audio_file_path, 'rb') as audio_file:
            files = {
                'file': (os.path.basename(audio_file_path), audio_file, 'audio/mpeg')
            }
            
            upload_response = requests.post(
                f"{LEMONFOX_BASE_URL}/v1/audio/transcriptions",
                headers=upload_headers,
                files=files,
                data={
                    'model': 'whisper-1',
                    'response_format': 'srt',
                    'language': 'en'
                },
                timeout=300  # 5 minutes timeout
            )
        
        print(f"📡 Upload Response Status: {upload_response.status_code}")
        print(f"📡 Upload Response Headers: {dict(upload_response.headers)}")
        
        if upload_response.status_code == 200:
            srt_content = upload_response.text
            print(f"✅ Transcription successful!")
            print(f"📝 SRT Content length: {len(srt_content)} characters")
            
            # Show first 500 characters of SRT content for debugging
            print(f"\n📄 First 500 characters of SRT content:")
            print("=" * 50)
            print(repr(srt_content[:500]))
            print("=" * 50)
            
            # Parse SRT content
            segments = parse_srt_content(srt_content)
            print(f"🎯 Parsed {len(segments)} segments from SRT")
            
            # Show first few segments
            if segments:
                print("\n📋 First 3 segments:")
                for i, segment in enumerate(segments[:3]):
                    print(f"  {i+1}. [{segment['start_time']:.2f}s - {segment['end_time']:.2f}s]: {segment['text'][:100]}...")
            
            return {
                "success": True,
                "srt_content": srt_content,
                "segments": segments,
                "segment_count": len(segments)
            }
        else:
            error_text = upload_response.text
            print(f"❌ Upload failed: {upload_response.status_code}")
            print(f"❌ Error response: {error_text}")
            
            return {
                "success": False,
                "error": f"HTTP {upload_response.status_code}: {error_text}",
                "status_code": upload_response.status_code
            }
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out after 5 minutes")
        return {"success": False, "error": "Request timeout"}
    except requests.exceptions.RequestException as e:
        print(f"🌐 Network error: {e}")
        return {"success": False, "error": f"Network error: {e}"}
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        return {"success": False, "error": f"Unexpected error: {e}"}

def parse_srt_content(srt_content: str) -> List[Dict[str, Any]]:
    """
    Parse SRT subtitle content into segments with timestamps
    """
    segments = []
    
    if not srt_content.strip():
        print("⚠️  Warning: Empty SRT content")
        return segments
    
    # Handle quoted content and escaped newlines from LemonFox API
    cleaned_content = srt_content.strip()
    
    # Remove quotes if the content is wrapped in quotes
    if cleaned_content.startswith('"') and cleaned_content.endswith('"'):
        cleaned_content = cleaned_content[1:-1]
        print("🔧 Removed surrounding quotes from SRT content")
    
    # Replace escaped newlines with actual newlines
    if '\\n' in cleaned_content:
        cleaned_content = cleaned_content.replace('\\n', '\n')
        print("🔧 Converted escaped newlines to actual newlines")
    
    print(f"📄 Cleaned SRT content (first 300 chars):")
    print("=" * 30)
    print(repr(cleaned_content[:300]))
    print("=" * 30)
    
    # Split by double newlines to get individual subtitle blocks
    blocks = cleaned_content.strip().split('\n\n')
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            try:
                # Parse sequence number
                sequence = int(lines[0])
                
                # Parse timestamp line (format: 00:00:00,000 --> 00:00:05,000)
                timestamp_line = lines[1]
                start_str, end_str = timestamp_line.split(' --> ')
                
                # Convert timestamps to seconds
                start_time = parse_timestamp(start_str)
                end_time = parse_timestamp(end_str)
                
                # Get text content (may span multiple lines)
                text = '\n'.join(lines[2:])
                
                segments.append({
                    'sequence': sequence,
                    'start_time': start_time,
                    'end_time': end_time,
                    'text': text.strip()
                })
                
            except (ValueError, IndexError) as e:
                print(f"⚠️  Warning: Could not parse SRT block: {block[:100]}... Error: {e}")
                continue
    
    return segments

def parse_timestamp(timestamp_str: str) -> float:
    """
    Convert SRT timestamp string to seconds
    Format: 00:00:00,000
    """
    time_part, milliseconds = timestamp_str.split(',')
    hours, minutes, seconds = map(int, time_part.split(':'))
    
    total_seconds = hours * 3600 + minutes * 60 + seconds + int(milliseconds) / 1000
    return total_seconds

def test_with_sample_audio():
    """
    Test with different audio file locations
    """
    # Possible test audio file locations
    test_files = [
        "/tmp/test_audio.mp3",
        "/home/azureuser/ai_platform/test_audio.mp3",
        "/home/azureuser/ai_platform/backend/tmp/test_audio.mp3"
    ]
    
    print("🔍 Looking for test audio files...")
    for file_path in test_files:
        if os.path.exists(file_path):
            print(f"✅ Found test file: {file_path}")
            return test_lemonfox_transcription(file_path)
    
    # Check if there are any audio files in tmp directories
    tmp_dirs = ["/tmp", "/home/azureuser/ai_platform/backend/tmp"]
    for tmp_dir in tmp_dirs:
        if os.path.exists(tmp_dir):
            for file in os.listdir(tmp_dir):
                if file.endswith(('.mp3', '.wav', '.m4a', '.mp4')):
                    file_path = os.path.join(tmp_dir, file)
                    print(f"✅ Found audio file: {file_path}")
                    return test_lemonfox_transcription(file_path)
    
    print("❌ No test audio files found. Please provide a path to an audio file.")
    return None

def create_test_audio():
    """
    Create a simple test audio file using text-to-speech
    """
    try:
        import pyttsx3
        
        print("🎤 Creating test audio file with text-to-speech...")
        
        # Initialize text-to-speech engine
        engine = pyttsx3.init()
        
        # Set properties
        engine.setProperty('rate', 150)  # Speed of speech
        
        # Test text
        test_text = "Hello, this is a test audio file for LemonFox AI transcription. The quick brown fox jumps over the lazy dog. Testing one two three."
        
        # Save to file
        output_path = "/tmp/test_audio.wav"
        engine.save_to_file(test_text, output_path)
        engine.runAndWait()
        
        if os.path.exists(output_path):
            print(f"✅ Created test audio file: {output_path}")
            return output_path
        else:
            print("❌ Failed to create test audio file")
            return None
            
    except ImportError:
        print("⚠️  pyttsx3 not available. Cannot create test audio.")
        return None
    except Exception as e:
        print(f"❌ Error creating test audio: {e}")
        return None

def main():
    """
    Main test function
    """
    print("🚀 LemonFox AI Transcription Test")
    print("=" * 50)
    
    # Test API key
    print(f"🔑 API Key: {LEMONFOX_API_KEY[:10]}...{LEMONFOX_API_KEY[-10:]}")
    print(f"🌐 Base URL: {LEMONFOX_BASE_URL}")
    
    # Check if user provided audio file path as command line argument
    import sys
    if len(sys.argv) > 1:
        audio_file_path = sys.argv[1]
        print(f"\n📁 Using provided audio file: {audio_file_path}")
        result = test_lemonfox_transcription(audio_file_path)
    else:
        # Try to find existing audio files
        result = test_with_sample_audio()
        
        if result is None:
            # Try to create test audio
            test_audio_path = create_test_audio()
            if test_audio_path:
                result = test_lemonfox_transcription(test_audio_path)
    
    # Print final results
    print("\n" + "=" * 50)
    print("📊 FINAL RESULTS:")
    if result:
        if result.get("success"):
            print("✅ LemonFox AI transcription test PASSED")
            print(f"📝 Total segments: {result.get('segment_count', 0)}")
        else:
            print("❌ LemonFox AI transcription test FAILED")
            print(f"💥 Error: {result.get('error', 'Unknown error')}")
    else:
        print("❌ No test could be performed - no audio file available")
    
    print("\n💡 Usage: python test_lemonfox.py [path_to_audio_file]")
    print("💡 Supported formats: .mp3, .wav, .m4a, .mp4")

if __name__ == "__main__":
    main()
