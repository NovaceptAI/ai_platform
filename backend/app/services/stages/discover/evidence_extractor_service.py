# app/services/stages/discover/evidence_extractor_service.py
import os, json, logging, re
from typing import List, Dict, Any, Tuple
import openai
from app.services.openai_key_manager import key_manager

log = logging.getLogger(__name__)

OPENAI_API_TYPE = "azure"
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")
DEFAULT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")

class EvidenceExtractorService:
    """
    Extracts evidence, quotes, and supporting statements from text.
    Useful for academic research, fact-checking, and argument analysis.
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
        log.info(f"[EvidenceExtractor] Using Azure OpenAI slot #{idx} ({api_base})")

    def _chat(self, messages, temperature=0.2, max_tokens=800, timeout=40) -> str:
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
            log.error(f"[EvidenceExtractor] OpenAI API error: {e}")
            # Retry with fresh credentials
            self._use_new_credentials()
            raise

    def extract_evidence_from_page(self, page_text: str) -> List[Dict[str, Any]]:
        """
        Extract evidence from a single page of text.
        Returns list of evidence items with type, content, confidence, etc.
        """
        if not page_text or len(page_text.strip()) < 50:
            return []

        prompt = f"""Analyze the following text and extract evidence, quotes, facts, and supporting statements that could be used in research or argumentation.

For each piece of evidence, provide:
1. The exact quote or statement
2. Type of evidence (quote, statistic, fact, expert_opinion, case_study, research_finding, etc.)
3. Confidence level (high/medium/low)
4. Context or explanation
5. Any supporting details (author, source, date if mentioned)

Text to analyze:
{page_text}

Return a JSON array of evidence items. Example format:
[
  {{
    "content": "exact quote or statement",
    "type": "quote|statistic|fact|expert_opinion|case_study|research_finding|anecdote|definition",
    "confidence": "high|medium|low",
    "context": "brief explanation of relevance",
    "supporting_info": {{
      "author": "if mentioned",
      "source": "if mentioned", 
      "date": "if mentioned",
      "page": "if mentioned"
    }},
    "themes": ["theme1", "theme2"]
  }}
]

Only include substantial evidence - skip trivial statements."""

        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = self._chat(messages)
            evidence_items = self._parse_evidence_response(response)
            log.info(f"[EvidenceExtractor] Extracted {len(evidence_items)} evidence items from page")
            return evidence_items
        except Exception as e:
            log.error(f"[EvidenceExtractor] Failed to extract evidence: {e}")
            return []

    def _parse_evidence_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse the JSON response from the evidence extraction."""
        try:
            # Clean up the response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            evidence_items = json.loads(response)
            
            # Validate and clean up each evidence item
            cleaned_items = []
            for item in evidence_items:
                if isinstance(item, dict) and item.get("content"):
                    cleaned_item = {
                        "content": str(item.get("content", "")).strip(),
                        "type": str(item.get("type", "fact")).lower(),
                        "confidence": str(item.get("confidence", "medium")).lower(),
                        "context": str(item.get("context", "")).strip(),
                        "supporting_info": item.get("supporting_info", {}),
                        "themes": item.get("themes", [])
                    }
                    
                    # Ensure confidence is valid
                    if cleaned_item["confidence"] not in ["high", "medium", "low"]:
                        cleaned_item["confidence"] = "medium"
                    
                    # Ensure type is valid
                    valid_types = ["quote", "statistic", "fact", "expert_opinion", "case_study", 
                                  "research_finding", "anecdote", "definition", "other"]
                    if cleaned_item["type"] not in valid_types:
                        cleaned_item["type"] = "fact"
                    
                    cleaned_items.append(cleaned_item)
            
            return cleaned_items
            
        except json.JSONDecodeError as e:
            log.error(f"[EvidenceExtractor] JSON parse error: {e}, response: {response[:200]}...")
            return []
        except Exception as e:
            log.error(f"[EvidenceExtractor] Error parsing evidence response: {e}")
            return []

    def aggregate_evidence_by_file(self, per_page_evidence: List[Tuple[int, List[Dict]]]) -> Dict[str, Any]:
        """
        Aggregate evidence from all pages into a file-level summary.
        """
        all_evidence = []
        evidence_by_type = {}
        evidence_by_confidence = {"high": [], "medium": [], "low": []}
        themes = {}
        
        total_pages_with_evidence = 0
        
        for page_num, page_evidence in per_page_evidence:
            if page_evidence:
                total_pages_with_evidence += 1
                
            for evidence in page_evidence:
                # Add page number to evidence
                evidence["page_number"] = page_num
                all_evidence.append(evidence)
                
                # Group by type
                ev_type = evidence.get("type", "other")
                if ev_type not in evidence_by_type:
                    evidence_by_type[ev_type] = []
                evidence_by_type[ev_type].append(evidence)
                
                # Group by confidence
                confidence = evidence.get("confidence", "medium")
                evidence_by_confidence[confidence].append(evidence)
                
                # Count themes
                for theme in evidence.get("themes", []):
                    themes[theme] = themes.get(theme, 0) + 1
        
        # Sort themes by frequency
        top_themes = sorted(themes.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Summary statistics
        stats = {
            "total_evidence_items": len(all_evidence),
            "pages_with_evidence": total_pages_with_evidence,
            "total_pages": len(per_page_evidence),
            "evidence_density": len(all_evidence) / max(len(per_page_evidence), 1),
            "types_distribution": {k: len(v) for k, v in evidence_by_type.items()},
            "confidence_distribution": {k: len(v) for k, v in evidence_by_confidence.items()},
            "top_themes": top_themes
        }
        
        return {
            "all_evidence": all_evidence,
            "evidence_by_type": evidence_by_type,
            "evidence_by_confidence": evidence_by_confidence,
            "stats": stats,
            "summary": self._generate_evidence_summary(all_evidence, stats)
        }
    
    def _generate_evidence_summary(self, all_evidence: List[Dict], stats: Dict) -> str:
        """Generate a natural language summary of the evidence."""
        total = stats["total_evidence_items"]
        if total == 0:
            return "No significant evidence items were found in this document."
        
        type_dist = stats["types_distribution"]
        conf_dist = stats["confidence_distribution"]
        top_themes = stats["top_themes"]
        
        # Build summary
        summary_parts = []
        summary_parts.append(f"Found {total} evidence items across {stats['pages_with_evidence']} pages.")
        
        # Most common types
        if type_dist:
            top_type = max(type_dist.items(), key=lambda x: x[1])
            summary_parts.append(f"Most common evidence type: {top_type[0]} ({top_type[1]} items).")
        
        # Confidence distribution
        high_conf = conf_dist.get("high", 0)
        if high_conf > 0:
            summary_parts.append(f"{high_conf} high-confidence evidence items identified.")
        
        # Top themes
        if top_themes:
            theme_names = [theme[0] for theme in top_themes[:3]]
            summary_parts.append(f"Key themes: {', '.join(theme_names)}.")
        
        return " ".join(summary_parts)
