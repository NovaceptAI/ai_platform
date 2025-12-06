"""
Azure OpenAI Transcription Service with Speaker Diarization
Uses gpt-4o-transcribe-diarize model for audio/video transcription with speaker separation
"""
import os
import logging
import json
import tempfile
import requests
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Azure OpenAI Configuration for Transcription
AZURE_TRANSCRIBE_API_KEY = os.getenv('AZURE_TRANSCRIBE_API_KEY', 'DuJ9DCCigEizWPFT1GjFh5KyArgDIWqIX5y8ZX4pfGHGSIlCe0DyJQQJ99BHACHYHv6XJ3w3AAABACOGFd6f')
AZURE_TRANSCRIBE_ENDPOINT = os.getenv('AZURE_TRANSCRIBE_ENDPOINT', 'https://scoolish-openai4.openai.azure.com')
AZURE_TRANSCRIBE_MODEL = os.getenv('AZURE_TRANSCRIBE_MODEL', 'gpt-4o-transcribe-diarize')
AZURE_API_VERSION = os.getenv('AZURE_TRANSCRIBE_API_VERSION', '2025-03-01-preview')

def transcribe_audio_with_diarization(audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
    """
    Transcribe audio file using Azure OpenAI with speaker diarization.
    
    Args:
        audio_path: Path to the audio file (WAV, MP3, M4A, etc.)
        language: Optional language code (e.g., 'en', 'es', 'fr')
    
    Returns:
        Dictionary containing:
            - segments: List of transcribed segments with timestamps and speaker info
            - full_text: Complete transcription text
            - speakers: List of detected speakers
            - language: Detected or specified language
    """
    logger.info(f"[AzureTranscribe] Starting transcription with diarization: {audio_path}")
    
    try:
        # Validate file exists and get size
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        logger.info(f"[AzureTranscribe] File size: {file_size_mb:.2f}MB")
        
        # Azure OpenAI endpoint for audio transcription
        url = f"{AZURE_TRANSCRIBE_ENDPOINT}/openai/deployments/{AZURE_TRANSCRIBE_MODEL}/audio/transcriptions"
        
        headers = {
            "Authorization": f"Bearer {AZURE_TRANSCRIBE_API_KEY}"
        }
        
        # Prepare the request
        params = {
            "api-version": AZURE_API_VERSION
        }
        
        # Build form data - chunking_strategy required for diarization
        data = {
            "model": AZURE_TRANSCRIBE_MODEL,
            "chunking_strategy": "auto"  # Required for diarization models
        }
        
        if language:
            data["language"] = language
            logger.info(f"[AzureTranscribe] Using language: {language}")
        
        # Open and send the audio file
        with open(audio_path, 'rb') as audio_file:
            files = {
                'file': (os.path.basename(audio_path), audio_file, 'audio/wav')
            }
            
            logger.info(f"[AzureTranscribe] Sending request to Azure OpenAI...")
            response = requests.post(
                url,
                headers=headers,
                params=params,
                data=data,
                files=files,
                timeout=600  # 10 minute timeout for large files
            )
        
        logger.info(f"[AzureTranscribe] Response status: {response.status_code}")
        
        if response.status_code != 200:
            error_msg = f"Azure transcription failed [{response.status_code}]: {response.text}"
            logger.error(f"[AzureTranscribe] {error_msg}")
            raise Exception(error_msg)
        
        # Parse response
        result = response.json()
        logger.info(f"[AzureTranscribe] Received transcription response")
        
        # Extract segments with speaker diarization
        segments = parse_azure_transcription_response(result)
        
        # Generate full text
        full_text = " ".join([seg['text'] for seg in segments])
        
        # Extract unique speakers
        speakers = sorted(list(set(seg.get('speaker', 'Speaker 1') for seg in segments)))
        
        transcription_result = {
            'segments': segments,
            'full_text': full_text,
            'speakers': speakers,
            'language': result.get('language', language or 'en'),
            'duration': result.get('duration', 0),
            'model': AZURE_TRANSCRIBE_MODEL
        }
        
        logger.info(f"[AzureTranscribe] Transcription complete: {len(segments)} segments, {len(speakers)} speakers")
        logger.info(f"[AzureTranscribe] Speakers detected: {', '.join(speakers)}")
        
        return transcription_result
        
    except Exception as e:
        logger.error(f"[AzureTranscribe] Transcription failed: {str(e)}")
        raise


def parse_azure_transcription_response(response_data: Dict) -> List[Dict]:
    """
    Parse Azure OpenAI transcription response and extract segments with speaker info.
    
    Args:
        response_data: JSON response from Azure OpenAI API
    
    Returns:
        List of segment dictionaries with text, timestamps, and speaker information
    """
    segments = []
    
    # Azure response structure for gpt-4o-transcribe (json format)
    # Simple JSON response: {"text": "full transcription text"}
    # OR with diarization:
    # {
    #   "text": "full transcription...",
    #   "segments": [
    #     {
    #       "start": 0.0,
    #       "end": 5.5,
    #       "text": "Hello, this is speaker one.",
    #       "speaker": "Speaker 1"
    #     },
    #     ...
    #   ]
    # }
    
    logger.info(f"[AzureTranscribe] Parsing response: {list(response_data.keys())}")
    
    raw_segments = response_data.get('segments', [])
    
    if not raw_segments:
        # Fallback: create single segment from full text
        # This happens when API returns simple format: {"text": "..."}
        logger.warning("[AzureTranscribe] No segments in response, using full text as single segment")
        full_text = response_data.get('text', '')
        
        if full_text:
            # Estimate duration based on text length (rough approximation)
            # Average speaking rate: ~150 words per minute = 2.5 words per second
            word_count = len(full_text.split())
            estimated_duration = word_count / 2.5
            
            segments.append({
                'sequence': 1,
                'start_seconds': 0.0,
                'end_seconds': estimated_duration,
                'start': format_timestamp(0.0),
                'end': format_timestamp(estimated_duration),
                'duration': estimated_duration,
                'text': full_text.strip(),
                'speaker': 'Speaker 1',
                'confidence': 0.8  # Lower confidence since we don't have detailed info
            })
        else:
            logger.error("[AzureTranscribe] No text or segments in response!")
        
        return segments
    
    # Process each segment
    for idx, segment in enumerate(raw_segments, start=1):
        start_time = segment.get('start', 0.0)
        end_time = segment.get('end', 0.0)
        text = segment.get('text', '').strip()
        
        # Speaker information (if available from diarization)
        speaker = segment.get('speaker', f'Speaker {estimate_speaker_from_context(idx, segments)}')
        
        # Confidence/probability metrics (may not be present in json format)
        avg_logprob = segment.get('avg_logprob', -0.5)
        no_speech_prob = segment.get('no_speech_prob', 0.0)
        confidence = calculate_confidence(avg_logprob, no_speech_prob)
        
        segment_data = {
            'sequence': idx,
            'start_seconds': start_time,
            'end_seconds': end_time,
            'start': format_timestamp(start_time),
            'end': format_timestamp(end_time),
            'duration': end_time - start_time,
            'text': text,
            'speaker': speaker,
            'confidence': confidence,
            'language': response_data.get('language', 'en')
        }
        
        segments.append(segment_data)
    
    logger.info(f"[AzureTranscribe] Parsed {len(segments)} segments")
    return segments


def estimate_speaker_from_context(segment_idx: int, previous_segments: List[Dict]) -> int:
    """
    Estimate speaker number if diarization info is not available.
    Uses simple heuristics based on pauses and turn-taking patterns.
    """
    # Simple alternating speaker heuristic
    # In real scenarios, the model should provide speaker labels
    if not previous_segments:
        return 1
    
    # Check last segment's speaker and estimate based on pause duration
    last_segment = previous_segments[-1]
    last_speaker_num = int(last_segment.get('speaker', 'Speaker 1').replace('Speaker ', ''))
    
    # If there's a significant pause (>2 seconds), might be different speaker
    # This is a fallback heuristic; the model should provide actual speaker info
    return last_speaker_num


def calculate_confidence(avg_logprob: float, no_speech_prob: float) -> float:
    """
    Calculate confidence score from Azure model probabilities.
    
    Args:
        avg_logprob: Average log probability of tokens
        no_speech_prob: Probability that segment contains no speech
    
    Returns:
        Confidence score between 0 and 1
    """
    # Convert log probability to confidence (typical range: -1.0 to 0.0)
    # Lower (more negative) means less confident
    logprob_confidence = max(0.0, min(1.0, 1.0 + avg_logprob))
    
    # Speech probability (inverse of no_speech_prob)
    speech_confidence = 1.0 - no_speech_prob
    
    # Combined confidence
    confidence = (logprob_confidence + speech_confidence) / 2.0
    
    return round(confidence, 3)


def format_timestamp(seconds: float) -> str:
    """
    Format seconds into SRT timestamp format (HH:MM:SS,mmm).
    
    Args:
        seconds: Time in seconds
    
    Returns:
        Formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def transcribe_audio_with_timestamps(audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
    """
    Main transcription function that maintains compatibility with existing code.
    This is the function that file_utils.py calls.
    
    Args:
        audio_path: Path to audio file
        language: Optional language code
    
    Returns:
        Transcription result dictionary compatible with existing code
    """
    return transcribe_audio_with_diarization(audio_path, language)


def export_to_srt(segments: List[Dict], output_path: Optional[str] = None) -> str:
    """
    Export transcription segments to SRT subtitle format.
    
    Args:
        segments: List of transcription segments
        output_path: Optional path to save SRT file
    
    Returns:
        SRT content as string
    """
    srt_lines = []
    
    for segment in segments:
        sequence = segment['sequence']
        start = segment['start']
        end = segment['end']
        speaker = segment.get('speaker', '')
        text = segment['text']
        
        # Add speaker label to text if available
        if speaker and speaker != 'Speaker 1':
            text = f"[{speaker}] {text}"
        
        srt_lines.append(f"{sequence}")
        srt_lines.append(f"{start} --> {end}")
        srt_lines.append(text)
        srt_lines.append("")  # Blank line between segments
    
    srt_content = "\n".join(srt_lines)
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        logger.info(f"[AzureTranscribe] Exported SRT to: {output_path}")
    
    return srt_content


def get_speaker_statistics(segments: List[Dict]) -> Dict[str, Any]:
    """
    Calculate speaking time statistics for each speaker.
    
    Args:
        segments: List of transcription segments
    
    Returns:
        Dictionary with speaker statistics
    """
    speaker_stats = {}
    
    for segment in segments:
        speaker = segment.get('speaker', 'Unknown')
        duration = segment.get('duration', 0)
        
        if speaker not in speaker_stats:
            speaker_stats[speaker] = {
                'total_duration': 0,
                'segment_count': 0,
                'word_count': 0
            }
        
        speaker_stats[speaker]['total_duration'] += duration
        speaker_stats[speaker]['segment_count'] += 1
        speaker_stats[speaker]['word_count'] += len(segment['text'].split())
    
    # Calculate percentages
    total_duration = sum(stats['total_duration'] for stats in speaker_stats.values())
    
    for speaker, stats in speaker_stats.items():
        stats['percentage'] = (stats['total_duration'] / total_duration * 100) if total_duration > 0 else 0
        stats['percentage'] = round(stats['percentage'], 1)
    
    logger.info(f"[AzureTranscribe] Speaker statistics calculated for {len(speaker_stats)} speakers")
    
    return speaker_stats
