#!/usr/bin/env python3
"""
Test script for Azure OpenAI Transcription Service with Speaker Diarization
Tests the new azure_transcribe_service.py implementation
"""
import os
import sys
import logging
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add the app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.azure_transcribe_service import (
    transcribe_audio_with_diarization,
    get_speaker_statistics,
    export_to_srt
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_transcription_service():
    """Test the Azure transcription service"""
    
    logger.info("=" * 80)
    logger.info("Azure Transcription Service Test")
    logger.info("=" * 80)
    
    # Check environment variables
    api_key = os.getenv('AZURE_TRANSCRIBE_API_KEY')
    endpoint = os.getenv('AZURE_TRANSCRIBE_ENDPOINT')
    
    if not api_key:
        logger.error("❌ AZURE_TRANSCRIBE_API_KEY not set in environment")
        return False
    
    if not endpoint:
        logger.error("❌ AZURE_TRANSCRIBE_ENDPOINT not set in environment")
        return False
    
    logger.info(f"✓ API Key configured: {api_key[:20]}...")
    logger.info(f"✓ Endpoint configured: {endpoint}")
    
    # Test with a sample audio file (if provided)
    if len(sys.argv) > 1:
        audio_path = sys.argv[1]
        
        if not os.path.exists(audio_path):
            logger.error(f"❌ Audio file not found: {audio_path}")
            return False
        
        logger.info(f"\n📁 Testing with audio file: {audio_path}")
        logger.info(f"📊 File size: {os.path.getsize(audio_path) / 1024 / 1024:.2f} MB")
        
        try:
            # Perform transcription
            logger.info("\n🎙️  Starting transcription with speaker diarization...")
            result = transcribe_audio_with_diarization(audio_path)
            
            # Display results
            logger.info("\n" + "=" * 80)
            logger.info("TRANSCRIPTION RESULTS")
            logger.info("=" * 80)
            
            logger.info(f"\n✓ Model: {result.get('model', 'N/A')}")
            logger.info(f"✓ Language: {result.get('language', 'N/A')}")
            logger.info(f"✓ Duration: {result.get('duration', 0):.2f} seconds")
            logger.info(f"✓ Total segments: {len(result['segments'])}")
            logger.info(f"✓ Speakers detected: {len(result['speakers'])}")
            
            # Speaker information
            if result['speakers']:
                logger.info(f"\n👥 Speakers: {', '.join(result['speakers'])}")
                
                # Get speaker statistics
                stats = get_speaker_statistics(result['segments'])
                logger.info("\n📊 Speaker Statistics:")
                for speaker, speaker_stats in stats.items():
                    logger.info(f"\n  {speaker}:")
                    logger.info(f"    - Speaking time: {speaker_stats['total_duration']:.1f}s ({speaker_stats['percentage']:.1f}%)")
                    logger.info(f"    - Segments: {speaker_stats['segment_count']}")
                    logger.info(f"    - Words: {speaker_stats['word_count']}")
            
            # Show sample segments
            logger.info("\n📝 Sample Transcription (first 5 segments):")
            for i, segment in enumerate(result['segments'][:5], 1):
                speaker = segment.get('speaker', 'Unknown')
                text = segment['text']
                start = segment['start']
                end = segment['end']
                logger.info(f"\n  {i}. [{start} --> {end}]")
                logger.info(f"     {speaker}: {text}")
            
            if len(result['segments']) > 5:
                logger.info(f"\n  ... and {len(result['segments']) - 5} more segments")
            
            # Export to SRT
            srt_output = audio_path.replace('.wav', '_transcription.srt').replace('.mp3', '_transcription.srt')
            export_to_srt(result['segments'], srt_output)
            logger.info(f"\n💾 SRT file exported to: {srt_output}")
            
            # Show full text preview
            logger.info("\n📄 Full Transcription Text (first 500 chars):")
            logger.info("-" * 80)
            logger.info(result['full_text'][:500])
            if len(result['full_text']) > 500:
                logger.info(f"... ({len(result['full_text'])} total characters)")
            logger.info("-" * 80)
            
            logger.info("\n✅ Test completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"\n❌ Transcription failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    else:
        logger.info("\n⚠️  No audio file provided for testing")
        logger.info("Usage: python test_azure_transcribe.py <path_to_audio_file>")
        logger.info("\n✓ Configuration check passed!")
        logger.info("✓ Service is ready to use")
        return True

if __name__ == "__main__":
    success = test_transcription_service()
    sys.exit(0 if success else 1)
