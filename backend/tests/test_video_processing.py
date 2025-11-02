#!/usr/bin/env python3
"""
Test script for video processing with MoviePy and LemonFox AI
"""

import sys
import os
import tempfile

# Add the backend directory to the Python path
sys.path.insert(0, '/home/azureuser/ai_platform/backend')

# Set up logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Import required modules
from app.services.lemonfox_service import transcribe_audio_with_timestamps

def test_video_processing(video_file_path: str):
    """Test complete video processing pipeline"""
    
    if not os.path.exists(video_file_path):
        print(f"❌ Video file not found: {video_file_path}")
        return None
    
    print(f"🎬 Testing video processing with: {video_file_path}")
    print(f"📊 File size: {os.path.getsize(video_file_path):,} bytes ({os.path.getsize(video_file_path) / 1024 / 1024:.2f} MB)")
    
    try:
        # Step 1: Extract audio using MoviePy
        print("\n🎵 Step 1: Extracting audio from video using MoviePy...")
        
        from moviepy.editor import VideoFileClip
        
        # Load video
        video = VideoFileClip(video_file_path)
        print(f"📹 Video duration: {video.duration:.2f} seconds")
        print(f"📹 Video FPS: {video.fps}")
        print(f"📹 Video size: {video.size}")
        
        # Create temporary audio file
        temp_audio_path = tempfile.mktemp(suffix='.wav')
        print(f"💾 Temporary audio file: {temp_audio_path}")
        
        # Extract audio
        audio = video.audio
        if audio is None:
            print("❌ No audio track found in video")
            video.close()
            return None
        
        # Extract audio
        print("🔊 Audio track found, extracting...")
        audio.write_audiofile(temp_audio_path, verbose=False)
        
        # Close video to free memory
        video.close()
        
        # Check extracted audio file
        if os.path.exists(temp_audio_path):
            audio_size = os.path.getsize(temp_audio_path)
            print(f"✅ Audio extracted successfully!")
            print(f"📊 Audio file size: {audio_size:,} bytes ({audio_size / 1024 / 1024:.2f} MB)")
        else:
            print("❌ Audio extraction failed")
            return None
        
        # Step 2: Transcribe audio with LemonFox
        print("\n🎯 Step 2: Transcribing audio with LemonFox AI...")
        
        result = transcribe_audio_with_timestamps(temp_audio_path)
        
        print("✅ Transcription completed!")
        print(f"📝 Segments: {len(result.get('segments', []))}")
        print(f"📄 Full text length: {len(result.get('full_text', ''))}")
        
        # Show first few segments
        segments = result.get('segments', [])
        if segments:
            print("\n📋 First 3 segments:")
            for i, segment in enumerate(segments[:3]):
                print(f"  {i+1}. [{segment['start_seconds']:.2f}s - {segment['end_seconds']:.2f}s]: {segment['text'][:100]}...")
        
        # Clean up temporary file
        try:
            os.remove(temp_audio_path)
            print(f"🗑️  Cleaned up temporary audio file")
        except:
            pass
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def find_video_files():
    """Find video files to test with"""
    
    # Common video file extensions
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv']
    
    # Search locations
    search_paths = [
        "/tmp",
        "/home/azureuser/ai_platform",
        "/home/azureuser/ai_platform/backend/tmp"
    ]
    
    video_files = []
    
    for search_path in search_paths:
        if os.path.exists(search_path):
            for root, dirs, files in os.walk(search_path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in video_extensions):
                        full_path = os.path.join(root, file)
                        video_files.append(full_path)
    
    return video_files

def main():
    """Main test function"""
    
    print("🚀 Video Processing Test with MoviePy + LemonFox AI")
    print("=" * 60)
    
    # Check if user provided video file path as command line argument
    if len(sys.argv) > 1:
        video_file_path = sys.argv[1]
        print(f"\n📁 Using provided video file: {video_file_path}")
        result = test_video_processing(video_file_path)
    else:
        # Try to find video files
        print("\n🔍 Searching for video files...")
        video_files = find_video_files()
        
        if video_files:
            print(f"✅ Found {len(video_files)} video file(s):")
            for i, video_file in enumerate(video_files[:5]):  # Show first 5
                print(f"  {i+1}. {video_file}")
            
            # Use the first video file
            video_file_path = video_files[0]
            print(f"\n🎬 Testing with: {video_file_path}")
            result = test_video_processing(video_file_path)
        else:
            print("❌ No video files found for testing")
            print("💡 Usage: python test_video_processing.py [path_to_video_file]")
            return
    
    # Print final results
    print("\n" + "=" * 60)
    print("📊 FINAL RESULTS:")
    if result:
        segments = result.get('segments', [])
        if segments:
            print("✅ Video processing test PASSED")
            print(f"📝 Total segments: {len(segments)}")
            print(f"📄 Total text length: {len(result.get('full_text', ''))}")
            
            # Show timing info
            if segments:
                first_segment = segments[0]
                last_segment = segments[-1]
                total_duration = last_segment['end_seconds'] - first_segment['start_seconds']
                print(f"⏱️  Video duration captured: {total_duration:.2f} seconds")
        else:
            print("❌ Video processing test FAILED - no segments found")
    else:
        print("❌ Video processing test FAILED")
    
    print("\n💡 This test verifies:")
    print("  1. MoviePy can extract audio from video")
    print("  2. LemonFox AI can transcribe the extracted audio")
    print("  3. SRT parsing works correctly for video-derived audio")

if __name__ == "__main__":
    main()
