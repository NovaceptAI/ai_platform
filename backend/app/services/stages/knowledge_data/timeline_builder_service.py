"""
Timeline Builder AI Service

Handles AI-powered timeline generation from text, documents, and data.
Extracts events, dates, relationships, and creates structured timelines.
"""

import os
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.services.ai_service_base import AIServiceBase

logger = logging.getLogger(__name__)


class TimelineBuilderService(AIServiceBase):
    """Service for creating timelines from text, documents, and data."""

    def __init__(self):
        super().__init__()
        self.service_name = "TimelineBuilder"
        self.model_name = "gpt-4"

    def get_service_info(self) -> Dict[str, Any]:
        """Return service metadata."""
        return {
            'service_name': 'TimelineBuilder',
            'description': 'Extract timelines and historical events from text and documents',
            'capabilities': [
                'text_extraction',
                'document_analysis',
                'event_detection',
                'date_extraction',
                'relationship_mapping',
                'timeline_visualization'
            ],
            'supported_formats': ['text', 'pdf', 'docx', 'txt'],
            'categories': ['history', 'science', 'personal', 'project', 'military', 'political']
        }

    def extract_timeline_from_text(
        self,
        input_text: str,
        category: Optional[str] = None,
        time_period: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract timeline events from text using GPT-4.

        Args:
            input_text: Text to analyze
            category: Optional category hint (history, science, personal, project)
            time_period: Optional time period hint

        Returns:
            Dictionary with extracted events and metadata
        """
        try:
            logger.info("[TimelineBuilder] Extracting timeline from text")

            # Build system prompt
            system_prompt = """You are a historical and timeline analysis expert. Extract the most significant events from the text and create a structured timeline.

CRITICAL INSTRUCTIONS:
1. Extract the 15-20 MOST IMPORTANT events only (not every single event mentioned)
2. Focus on major turning points, significant dates, and key milestones
3. Be concise in descriptions (1-2 sentences max per event)
4. You MUST respond with ONLY a valid JSON object - no explanations, no markdown, no text before or after
5. Ensure the JSON is complete and properly closed

For each event, identify:
- Title (concise, 5-10 words max)
- Date (ISO format: YYYY-MM-DD, YYYY-MM, or YYYY)
- Date precision (exact, year, month, decade, century, approximate)
- Description (1-2 sentences, keep it short)
- Significance (why this event matters, 1 sentence)
- Category (political, cultural, scientific, economic, military, or personal)
- Location (if mentioned)
- People involved (key figures only)

JSON STRUCTURE (copy this exactly):
{
    "title": "Timeline Title",
    "description": "Brief timeline description",
    "time_period": "Date range",
    "events": [
        {
            "title": "Event Title",
            "date": "YYYY",
            "date_precision": "year",
            "description": "Brief description",
            "significance": "Why it matters",
            "category": "political",
            "location": "Location",
            "people_involved": [],
            "related_event_ids": [],
            "sources": []
        }
    ],
    "date_range_start": "YYYY",
    "date_range_end": "YYYY",
    "key_themes": [],
    "key_figures": [],
    "confidence_score": 8
}

Return ONLY valid JSON. No other text."""

            user_prompt = f"Text to analyze:\n\n{input_text}"

            if category:
                user_prompt += f"\n\nCategory hint: {category}"
            if time_period:
                user_prompt += f"\nTime period hint: {time_period}"

            # Call GPT-4 using the base class method
            # Increased token limit to handle large timelines
            response_text = self._make_openai_call(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=8000  # Increased from 4000 to handle larger responses
            )

            logger.debug(f"[TimelineBuilder] Raw response length: {len(response_text)} chars")

            result = self._parse_json_response(response_text)

            # Check if parsing failed
            if 'error' in result and 'raw_response' in result:
                logger.error(f"[TimelineBuilder] Failed to parse AI response. Response preview: {response_text[:500]}...")
                return {
                    'success': False,
                    'error': 'Failed to parse AI response. The text may not contain clear timeline information. Please try again with more structured historical content.'
                }

            # Validate required fields
            required_fields = ['title', 'events']
            if not self._validate_response(result, required_fields):
                logger.error(f"[TimelineBuilder] Response missing required fields")
                return {
                    'success': False,
                    'error': 'Could not extract a valid timeline structure. Please ensure the text contains clear events with dates.'
                }

            # Ensure events is a list
            if not isinstance(result.get('events'), list):
                logger.error(f"[TimelineBuilder] Events field is not a list")
                return {
                    'success': False,
                    'error': 'Invalid timeline structure received.'
                }

            # Add unique IDs to events
            for i, event in enumerate(result.get('events', [])):
                event['id'] = f"event_{i}"

            logger.info(f"[TimelineBuilder] Extracted {len(result.get('events', []))} events")

            return {
                'success': True,
                'timeline_data': result,
                'total_events': len(result.get('events', [])),
                'model_used': 'gpt-4'
            }

        except Exception as e:
            logger.error(f"[TimelineBuilder] Error extracting timeline: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def extract_timeline_from_document(
        self,
        document_path: str,
        category: Optional[str] = None,
        time_period: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract timeline from document (PDF, TXT, DOCX).

        Args:
            document_path: Path to document file
            category: Optional category hint
            time_period: Optional time period hint

        Returns:
            Dictionary with extracted events and metadata
        """
        try:
            logger.info(f"[TimelineBuilder] Extracting timeline from document: {document_path}")

            # Extract text from document
            document_text = self.extract_text_from_document(document_path)

            if not document_text:
                return {
                    'success': False,
                    'error': 'Failed to extract text from document'
                }

            # Use text extraction
            return self.extract_timeline_from_text(document_text, category, time_period)

        except Exception as e:
            logger.error(f"[TimelineBuilder] Error extracting timeline from document: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def extract_text_from_document(self, document_path: str) -> Optional[str]:
        """
        Extract text from various document formats.

        Args:
            document_path: Path to document

        Returns:
            Extracted text or None
        """
        try:
            if document_path.endswith('.txt'):
                with open(document_path, 'r', encoding='utf-8') as f:
                    return f.read()

            elif document_path.endswith('.pdf'):
                import PyPDF2
                text = []
                with open(document_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page in pdf_reader.pages:
                        text.append(page.extract_text())
                return '\n'.join(text)

            elif document_path.endswith('.docx'):
                from docx import Document
                doc = Document(document_path)
                return '\n'.join([para.text for para in doc.paragraphs])

            else:
                logger.warning(f"[TimelineBuilder] Unsupported document format: {document_path}")
                return None

        except Exception as e:
            logger.error(f"[TimelineBuilder] Error extracting text from document: {str(e)}")
            return None

    def enhance_timeline_with_research(self, timeline_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance timeline with additional research and context.

        Args:
            timeline_data: Original timeline data

        Returns:
            Enhanced timeline data
        """
        try:
            logger.info("[TimelineBuilder] Enhancing timeline with research")

            system_prompt = """You are a historical research assistant. Given a timeline of events, provide additional context, connections, and insights.

For the provided timeline:
1. Add historical context to events
2. Identify causal relationships between events
3. Suggest additional related events that might be missing
4. Provide interesting facts or connections
5. Validate and improve date accuracy

IMPORTANT: You MUST respond with ONLY a valid JSON object in the exact same structure as the input, with enhanced data. No other text before or after the JSON."""

            response_text = self._make_openai_call(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(timeline_data, indent=2)}
                ],
                temperature=0.7,
                max_tokens=4000
            )

            enhanced_data = self._parse_json_response(response_text)

            # Check if parsing failed
            if 'error' in enhanced_data and 'raw_response' in enhanced_data:
                logger.warning(f"[TimelineBuilder] Failed to parse enhancement response, using original data")
                return {
                    'success': True,
                    'timeline_data': timeline_data
                }

            logger.info("[TimelineBuilder] Timeline enhanced successfully")

            return {
                'success': True,
                'timeline_data': enhanced_data
            }

        except Exception as e:
            logger.error(f"[TimelineBuilder] Error enhancing timeline: {str(e)}")
            return {
                'success': False,
                'timeline_data': timeline_data,
                'error': str(e)
            }

    def analyze_timeline_relationships(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze and establish relationships between events.

        Args:
            events: List of timeline events

        Returns:
            Events with updated relationship data
        """
        try:
            logger.info("[TimelineBuilder] Analyzing event relationships")

            # Sort events by date
            sorted_events = sorted(events, key=lambda x: x.get('date', ''))

            # Use GPT to identify relationships
            system_prompt = """Analyze the following timeline events and identify causal relationships, influences, and connections between them.

For each event, list the IDs of related events (events that directly led to, influenced, or were consequences of this event).

IMPORTANT: You MUST respond with ONLY a valid JSON object, no other text. Use this exact structure:
{
    "events": [
        {
            "id": "event_0",
            "title": "Event Title",
            "date": "YYYY-MM-DD",
            "related_event_ids": ["event_1", "event_2"]
        }
    ]
}

Return ONLY the JSON object with all events and their updated related_event_ids fields."""

            response_text = self._make_openai_call(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(sorted_events, indent=2)}
                ],
                temperature=0.7,
                max_tokens=3000
            )

            result = self._parse_json_response(response_text)

            # Handle both array and object responses
            if isinstance(result, list):
                return result
            elif isinstance(result, dict):
                return result.get('events', sorted_events)
            else:
                return sorted_events

        except Exception as e:
            logger.error(f"[TimelineBuilder] Error analyzing relationships: {str(e)}")
            return events

    def generate_timeline_visualization_config(
        self,
        timeline_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate optimal visualization configuration based on timeline data.

        Args:
            timeline_data: Timeline data

        Returns:
            Visualization configuration
        """
        try:
            total_events = len(timeline_data.get('events', []))
            time_span = timeline_data.get('date_range_end', '') and timeline_data.get('date_range_start', '')

            # Determine best visualization type
            visualization_type = 'linear'

            if total_events > 50:
                visualization_type = 'condensed'
            elif timeline_data.get('category') == 'personal':
                visualization_type = 'vertical'

            # Choose color scheme based on category
            color_schemes = {
                'history': 'historical',
                'science': 'scientific',
                'personal': 'warm',
                'project': 'professional',
                'military': 'military'
            }

            color_scheme = color_schemes.get(
                timeline_data.get('category', ''),
                'default'
            )

            return {
                'visualization_type': visualization_type,
                'color_scheme': color_scheme,
                'display_options': {
                    'show_relationships': total_events <= 30,
                    'group_by_category': total_events > 20,
                    'show_images': True,
                    'compact_mode': total_events > 40
                }
            }

        except Exception as e:
            logger.error(f"[TimelineBuilder] Error generating visualization config: {str(e)}")
            return {
                'visualization_type': 'linear',
                'color_scheme': 'default',
                'display_options': {}
            }

    def validate_timeline_data(self, timeline_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize timeline data.

        Args:
            timeline_data: Raw timeline data

        Returns:
            Validated timeline data with validation report
        """
        try:
            issues = []
            warnings = []

            # Check required fields
            if not timeline_data.get('title'):
                issues.append('Missing timeline title')
                timeline_data['title'] = 'Untitled Timeline'

            if not timeline_data.get('events'):
                issues.append('No events found')
                timeline_data['events'] = []

            # Validate each event
            for i, event in enumerate(timeline_data.get('events', [])):
                if not event.get('title'):
                    warnings.append(f"Event {i} missing title")
                    event['title'] = f"Event {i+1}"

                if not event.get('date'):
                    warnings.append(f"Event {i} missing date")
                    event['date'] = 'Unknown'
                    event['date_precision'] = 'approximate'

                if not event.get('description'):
                    warnings.append(f"Event {i} missing description")
                    event['description'] = 'No description available'

            # Calculate metadata
            valid_dates = [e['date'] for e in timeline_data['events'] if e.get('date') and e['date'] != 'Unknown']
            if valid_dates:
                timeline_data['date_range_start'] = min(valid_dates)
                timeline_data['date_range_end'] = max(valid_dates)

            logger.info(f"[TimelineBuilder] Validation complete: {len(issues)} issues, {len(warnings)} warnings")

            return {
                'success': True,
                'timeline_data': timeline_data,
                'validation': {
                    'issues': issues,
                    'warnings': warnings,
                    'is_valid': len(issues) == 0
                }
            }

        except Exception as e:
            logger.error(f"[TimelineBuilder] Error validating timeline: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
