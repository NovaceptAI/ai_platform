# app/services/stages/discover/comparison_service.py
import os, json, logging, re
from typing import List, Dict, Any, Tuple
import openai
from app.services.openai_key_manager import key_manager

log = logging.getLogger(__name__)

OPENAI_API_TYPE = "azure"
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")
DEFAULT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")

class ComparisonService:
    """
    Compares multiple documents or text segments to identify:
    - Similarities and differences
    - Contrasting viewpoints
    - Common themes
    - Unique insights per source
    """
    
    def __init__(self, openai_engine: str = DEFAULT_DEPLOYMENT):
        self.openai_engine = openai_engine
        self._use_new_credentials()

    def _use_new_credentials(self):
        api_key, api_base, idx = key_manager.get_next()
        openai.api_type = OPENAI_API_TYPE
        openai.api_version = OPENAI_API_VERSION
        openai.api_key = api_key
        openai.api_base = api_base
        log.info(f"[Comparison] Using Azure OpenAI slot #{idx} ({api_base})")

    def _chat(self, messages, temperature=0.3, max_tokens=1000, timeout=60) -> str:
        try:
            r = openai.ChatCompletion.create(
                engine=self.openai_engine,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout
            )
            return (r.choices[0].message.content or "").strip()
        except Exception as e:
            log.error(f"[Comparison] OpenAI API error: {e}")
            # Retry with fresh credentials
            self._use_new_credentials()
            raise

    def compare_documents(self, file_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compare multiple documents based on their summaries and key content.
        
        Args:
            file_summaries: List of dicts with keys: file_id, title, summary, key_points, etc.
        
        Returns:
            Dict with comparison results
        """
        if len(file_summaries) < 2:
            return {
                "error": "Need at least 2 documents to compare",
                "file_count": len(file_summaries)
            }

        # Prepare content for comparison
        doc_texts = []
        for i, doc in enumerate(file_summaries):
            doc_text = f"Document {i+1} ({doc.get('title', 'Untitled')}):\n"
            doc_text += f"Summary: {doc.get('summary', 'No summary available')}\n"
            if doc.get('key_points'):
                doc_text += f"Key Points: {', '.join(doc.get('key_points', []))}\n"
            doc_texts.append(doc_text)

        prompt = f"""Compare the following {len(file_summaries)} documents and analyze their similarities, differences, and relationships.

{chr(10).join(doc_texts)}

Provide a comprehensive comparison analysis in JSON format with:

1. **similarities**: Common themes, shared concepts, overlapping ideas
2. **differences**: Contrasting viewpoints, unique perspectives, different approaches
3. **themes**: Major themes across all documents with their presence in each doc
4. **relationships**: How documents relate to each other (complementary, contradictory, etc.)
5. **unique_insights**: What each document contributes uniquely
6. **synthesis**: Overall insights from comparing all documents
7. **recommendations**: Suggested reading order or how to use these documents together

Example format:
{{
  "similarities": [
    {{
      "theme": "theme name",
      "description": "what's similar",
      "documents": ["doc1", "doc2"]
    }}
  ],
  "differences": [
    {{
      "aspect": "what differs",
      "variations": [
        {{"document": "doc1", "perspective": "their view"}},
        {{"document": "doc2", "perspective": "their view"}}
      ]
    }}
  ],
  "themes": [
    {{
      "theme": "major theme",
      "presence": {{"doc1": "high|medium|low", "doc2": "high|medium|low"}},
      "description": "theme description"
    }}
  ],
  "relationships": [
    {{
      "type": "complementary|contradictory|builds_upon|alternative_view",
      "documents": ["doc1", "doc2"],
      "explanation": "how they relate"
    }}
  ],
  "unique_insights": [
    {{
      "document": "doc1",
      "insights": ["unique insight 1", "unique insight 2"]
    }}
  ],
  "synthesis": "overall analysis from comparing all documents",
  "recommendations": {{
    "reading_order": ["doc1", "doc2"],
    "usage": "how to best use these documents together"
  }}
}}"""

        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = self._chat(messages)
            comparison_result = self._parse_comparison_response(response)
            
            # Add metadata
            comparison_result["file_count"] = len(file_summaries)
            comparison_result["file_ids"] = [doc.get("file_id") for doc in file_summaries]
            comparison_result["document_titles"] = [doc.get("title", "Untitled") for doc in file_summaries]
            
            log.info(f"[Comparison] Completed comparison of {len(file_summaries)} documents")
            return comparison_result
            
        except Exception as e:
            log.error(f"[Comparison] Failed to compare documents: {e}")
            return {
                "error": str(e),
                "file_count": len(file_summaries)
            }

    def _parse_comparison_response(self, response: str) -> Dict[str, Any]:
        """Parse the JSON response from document comparison."""
        try:
            # Clean up the response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            comparison_data = json.loads(response)
            
            # Validate required keys
            required_keys = ["similarities", "differences", "themes", "synthesis"]
            for key in required_keys:
                if key not in comparison_data:
                    comparison_data[key] = []
            
            return comparison_data
            
        except json.JSONDecodeError as e:
            log.error(f"[Comparison] JSON parse error: {e}, response: {response[:200]}...")
            return {
                "similarities": [],
                "differences": [],
                "themes": [],
                "synthesis": "Failed to parse comparison results",
                "error": "Parse error"
            }
        except Exception as e:
            log.error(f"[Comparison] Error parsing comparison response: {e}")
            return {
                "similarities": [],
                "differences": [],
                "themes": [],
                "synthesis": "Error occurred during comparison",
                "error": str(e)
            }

    def compare_text_segments(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compare text segments within a document or across documents.
        
        Args:
            segments: List of text segments with metadata
        
        Returns:
            Comparison analysis of the segments
        """
        if len(segments) < 2:
            return {
                "error": "Need at least 2 segments to compare",
                "segment_count": len(segments)
            }

        # Prepare segments for comparison
        segment_texts = []
        for i, segment in enumerate(segments):
            seg_text = f"Segment {i+1}: {segment.get('text', '')}"
            if segment.get('source'):
                seg_text += f" (Source: {segment.get('source')})"
            segment_texts.append(seg_text)

        prompt = f"""Compare the following {len(segments)} text segments and identify patterns, similarities, and differences.

{chr(10).join(segment_texts)}

Analyze and return JSON with:
- **patterns**: Recurring themes or patterns across segments
- **similarity_groups**: Groups of similar segments
- **contrasts**: How segments differ from each other
- **progression**: Any logical progression or development across segments
- **key_insights**: Main insights from the comparison

Focus on content, style, and thematic elements."""

        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = self._chat(messages)
            result = self._parse_comparison_response(response)
            result["segment_count"] = len(segments)
            return result
        except Exception as e:
            log.error(f"[Comparison] Failed to compare segments: {e}")
            return {
                "error": str(e),
                "segment_count": len(segments)
            }
