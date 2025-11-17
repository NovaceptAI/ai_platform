# app/services/stages/discover/readability_service.py
import os
import json
import logging
import re
from typing import Dict, List, Any
import openai
from app.services.openai_key_manager import key_manager

log = logging.getLogger(__name__)

OPENAI_API_TYPE = "azure"
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")
DEFAULT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")

class ReadabilityService:
    """
    Analyzes text for readability, clarity, complexity, and writing style.
    Provides metrics, audience assessment, and improvement recommendations.
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
        log.info(f"[ReadabilityService] Using Azure OpenAI slot #{idx} ({api_base})")

    def _chat(self, messages, temperature=0.3, max_tokens=1500, timeout=45) -> str:
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
            log.error(f"[ReadabilityService] OpenAI API error: {e}")
            self._use_new_credentials()
            raise

    def analyze_page_readability(self, page_text: str) -> Dict[str, Any]:
        """
        Analyze readability metrics for a single page.
        Returns metrics, issues, and complexity assessment.
        """
        if not page_text or len(page_text.strip()) < 50:
            return {
                "word_count": 0,
                "sentence_count": 0,
                "avg_sentence_length": 0,
                "complex_words": 0,
                "issues": [],
                "readability_level": "insufficient_text"
            }

        # Calculate basic metrics
        metrics = self._calculate_basic_metrics(page_text)

        # Use AI to analyze style and issues
        prompt = f"""Analyze the following text for readability and style. Provide a JSON response with:

1. readability_level: one of "very_easy", "easy", "moderate", "difficult", "very_difficult"
2. tone: e.g., "formal", "informal", "academic", "conversational", "technical"
3. issues: array of readability issues found (max 5 most important)
   Each issue: {{"type": "issue_type", "severity": "high|medium|low", "description": "what's wrong", "suggestion": "how to improve"}}
4. strengths: array of positive aspects (max 3)
5. target_audience: best suited for which audience level

Text to analyze:
{page_text[:2000]}

IMPORTANT: Return ONLY valid JSON. No explanatory text before or after.

Example format:
{{
  "readability_level": "moderate",
  "tone": "formal",
  "issues": [
    {{
      "type": "long_sentences",
      "severity": "medium",
      "description": "Several sentences exceed 30 words",
      "suggestion": "Break long sentences into shorter ones"
    }}
  ],
  "strengths": ["Clear structure", "Good use of transitions"],
  "target_audience": "college_educated"
}}"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self._chat(messages)
            ai_analysis = self._parse_json_response(response)

            # Merge basic metrics with AI analysis
            return {
                **metrics,
                **ai_analysis
            }
        except Exception as e:
            log.error(f"[ReadabilityService] Failed to analyze page: {e}")
            return {
                **metrics,
                "readability_level": "unknown",
                "tone": "unknown",
                "issues": [],
                "strengths": [],
                "target_audience": "unknown"
            }

    def _calculate_basic_metrics(self, text: str) -> Dict[str, Any]:
        """Calculate basic text metrics (word count, sentence count, etc.)"""
        # Count words
        words = re.findall(r'\b\w+\b', text)
        word_count = len(words)

        # Count sentences (approximate)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        sentence_count = len(sentences)

        # Average sentence length
        avg_sentence_length = word_count / max(sentence_count, 1)

        # Count complex words (words with 3+ syllables, rough estimate)
        complex_words = len([w for w in words if self._estimate_syllables(w) >= 3])
        complex_word_percentage = (complex_words / max(word_count, 1)) * 100

        # Count paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        paragraph_count = len(paragraphs)

        return {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "paragraph_count": paragraph_count,
            "avg_sentence_length": round(avg_sentence_length, 1),
            "complex_words": complex_words,
            "complex_word_percentage": round(complex_word_percentage, 1),
            "avg_word_length": round(sum(len(w) for w in words) / max(word_count, 1), 1)
        }

    def _estimate_syllables(self, word: str) -> int:
        """Rough syllable count estimation"""
        word = word.lower()
        vowels = 'aeiou'
        syllable_count = 0
        previous_was_vowel = False

        for char in word:
            is_vowel = char in vowels
            if is_vowel and not previous_was_vowel:
                syllable_count += 1
            previous_was_vowel = is_vowel

        # Adjust for silent 'e'
        if word.endswith('e'):
            syllable_count -= 1

        return max(1, syllable_count)

    def aggregate_readability_by_file(self, per_page_analysis: List[tuple]) -> Dict[str, Any]:
        """
        Aggregate readability analysis from all pages into document-level metrics.
        per_page_analysis: [(page_number, analysis_dict)]
        """
        if not per_page_analysis:
            return {
                "doc_metrics": {},
                "per_page_analysis": [],
                "style_analysis": {},
                "readability_scores": {},
                "issues": [],
                "recommendations": [],
                "summary": "No analysis data available."
            }

        # Aggregate metrics
        total_words = sum(a[1].get("word_count", 0) for a in per_page_analysis)
        total_sentences = sum(a[1].get("sentence_count", 0) for a in per_page_analysis)
        total_paragraphs = sum(a[1].get("paragraph_count", 0) for a in per_page_analysis)
        total_complex_words = sum(a[1].get("complex_words", 0) for a in per_page_analysis)

        doc_metrics = {
            "total_words": total_words,
            "total_sentences": total_sentences,
            "total_paragraphs": total_paragraphs,
            "avg_words_per_sentence": round(total_words / max(total_sentences, 1), 1),
            "complex_word_percentage": round((total_complex_words / max(total_words, 1)) * 100, 1),
            "pages_analyzed": len(per_page_analysis)
        }

        # Collect all issues
        all_issues = []
        for page_num, analysis in per_page_analysis:
            for issue in analysis.get("issues", []):
                issue_copy = issue.copy()
                issue_copy["page"] = page_num
                all_issues.append(issue_copy)

        # Count readability levels
        readability_levels = {}
        tones = {}
        for _, analysis in per_page_analysis:
            level = analysis.get("readability_level", "unknown")
            readability_levels[level] = readability_levels.get(level, 0) + 1

            tone = analysis.get("tone", "unknown")
            tones[tone] = tones.get(tone, 0) + 1

        # Determine dominant tone and readability level
        dominant_tone = max(tones.items(), key=lambda x: x[1])[0] if tones else "unknown"
        dominant_readability = max(readability_levels.items(), key=lambda x: x[1])[0] if readability_levels else "unknown"

        style_analysis = {
            "dominant_tone": dominant_tone,
            "dominant_readability_level": dominant_readability,
            "tone_distribution": tones,
            "readability_distribution": readability_levels
        }

        # Generate recommendations based on issues
        recommendations = self._generate_recommendations(all_issues, doc_metrics)

        # Generate summary
        summary = self._generate_summary(doc_metrics, style_analysis, all_issues)

        return {
            "doc_metrics": doc_metrics,
            "per_page_analysis": [{"page": p[0], "analysis": p[1]} for p in per_page_analysis],
            "style_analysis": style_analysis,
            "readability_scores": self._calculate_readability_scores(doc_metrics),
            "issues": all_issues[:20],  # Top 20 issues
            "recommendations": recommendations,
            "summary": summary
        }

    def _calculate_readability_scores(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate standard readability scores"""
        avg_words_per_sentence = metrics.get("avg_words_per_sentence", 0)
        complex_word_pct = metrics.get("complex_word_percentage", 0)

        # Flesch Reading Ease (simplified approximation)
        # Score = 206.835 - 1.015(total words/total sentences) - 84.6(total syllables/total words)
        # Higher score = easier to read
        flesch_ease = 206.835 - (1.015 * avg_words_per_sentence) - (84.6 * (complex_word_pct / 100))
        flesch_ease = max(0, min(100, flesch_ease))

        # Flesch-Kincaid Grade Level (simplified)
        # Grade = 0.39(total words/total sentences) + 11.8(total syllables/total words) - 15.59
        fk_grade = (0.39 * avg_words_per_sentence) + (11.8 * (complex_word_pct / 100)) - 15.59
        fk_grade = max(1, min(18, fk_grade))

        return {
            "flesch_reading_ease": round(flesch_ease, 1),
            "flesch_kincaid_grade": round(fk_grade, 1),
            "interpretation": self._interpret_flesch_score(flesch_ease)
        }

    def _interpret_flesch_score(self, score: float) -> str:
        """Interpret Flesch Reading Ease score"""
        if score >= 90:
            return "Very Easy (5th grade level)"
        elif score >= 80:
            return "Easy (6th grade level)"
        elif score >= 70:
            return "Fairly Easy (7th grade level)"
        elif score >= 60:
            return "Standard (8th-9th grade level)"
        elif score >= 50:
            return "Fairly Difficult (10th-12th grade level)"
        elif score >= 30:
            return "Difficult (College level)"
        else:
            return "Very Difficult (College graduate level)"

    def _generate_recommendations(self, issues: List[Dict], metrics: Dict) -> List[str]:
        """Generate actionable recommendations based on issues"""
        recommendations = []

        # Count issue types
        issue_types = {}
        for issue in issues:
            itype = issue.get("type", "unknown")
            issue_types[itype] = issue_types.get(itype, 0) + 1

        # Generate recommendations based on common issues
        if issue_types.get("long_sentences", 0) > 3:
            recommendations.append("Break down long sentences into shorter, clearer statements")

        if issue_types.get("passive_voice", 0) > 3:
            recommendations.append("Use active voice more frequently to make writing more direct")

        if issue_types.get("complex_vocabulary", 0) > 3:
            recommendations.append("Simplify vocabulary where possible for better clarity")

        if metrics.get("avg_words_per_sentence", 0) > 25:
            recommendations.append("Reduce average sentence length (currently above 25 words)")

        if metrics.get("complex_word_percentage", 0) > 20:
            recommendations.append("Reduce use of complex words (currently over 20% of text)")

        return recommendations[:5]  # Top 5 recommendations

    def _generate_summary(self, metrics: Dict, style: Dict, issues: List[Dict]) -> str:
        """Generate a natural language summary"""
        total_words = metrics.get("total_words", 0)
        avg_words = metrics.get("avg_words_per_sentence", 0)
        tone = style.get("dominant_tone", "unknown")
        readability = style.get("dominant_readability_level", "unknown")
        issue_count = len(issues)

        summary_parts = []
        summary_parts.append(f"Document contains {total_words} words with an average of {avg_words} words per sentence.")
        summary_parts.append(f"The writing style is predominantly {tone} with {readability.replace('_', ' ')} readability.")

        if issue_count > 0:
            summary_parts.append(f"Found {issue_count} readability issues that could be improved.")
        else:
            summary_parts.append("No major readability issues detected.")

        return " ".join(summary_parts)

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from AI response"""
        try:
            response = response.strip()

            # Remove markdown code blocks
            if response.startswith("```json"):
                response = response[7:]
            elif response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            # Extract JSON object
            start_idx = response.find('{')
            end_idx = response.rfind('}')

            if start_idx == -1 or end_idx == -1:
                log.warning(f"[ReadabilityService] No valid JSON object found")
                return {}

            json_str = response[start_idx:end_idx + 1]
            return json.loads(json_str)

        except json.JSONDecodeError as e:
            log.error(f"[ReadabilityService] JSON parse error: {e}, response: {response[:500]}")
            return {}
        except Exception as e:
            log.error(f"[ReadabilityService] Error parsing response: {e}")
            return {}
