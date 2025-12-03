import os
import json
import logging
from app.services.lemonfox_service import transcribe_audio
import openai

from app.utils.file_utils import (
    detect_file_type,
    extract_text_from_document,
    extract_text_from_audio,
    extract_text_from_video
)

from app.services.openai_key_manager import key_manager

logger = logging.getLogger(__name__)

# We’ll set api_key/base per-instance (or per-call) via rotation:
OPENAI_API_TYPE = "azure"
OPENAI_API_VERSION = "2023-03-15-preview"  # keep your current version

class Summarizer:
    def __init__(self, openai_engine="gpt-4.1"):
        self.openai_engine = openai_engine
        # grab credentials for this batch instance
        self._use_new_credentials()

    def _use_new_credentials(self):
        api_key, api_base, idx = key_manager.get_next()
        openai.api_type = OPENAI_API_TYPE
        openai.api_version = OPENAI_API_VERSION
        openai.api_key = api_key
        openai.api_base = api_base
        logger.info(f"[Summarizer] Using Azure OpenAI credential slot #{idx} ({openai.api_base})")

    def _summarize_file(self, file_path):
        try:
            file_type = detect_file_type(file_path)
            if file_type == "document":
                return self._summarize_document(file_path)
            elif file_type == "audio":
                return self._summarize_audio(file_path)
            elif file_type == "video":
                return self._summarize_video(file_path)
            else:
                raise ValueError("Unsupported file format")
        except Exception as e:
            logger.error(f"Error summarizing file: {e}")
            raise

    def _summarize_document(self, file_path):
        chunks = extract_text_from_document(file_path)  # returns chunks
        summaries, tags, entities = [], [], []

        for chunk in chunks:
            summaries.append(self._summarize_text(chunk))
            tags.append(self._tag_segment(chunk))
            entities.append(self._extract_entities(chunk))

        toc = self._generate_toc(chunks)
        return {
            "toc": toc,
            "segments": chunks,
            "tags": tags,
            "entities": entities,
            "summary": summaries
        }

    def _summarize_audio(self, file_path):
        transcribed_text = extract_text_from_audio(file_path)
        segments = self._segment_text(transcribed_text)
        toc = self._generate_toc(segments)
        tags = self._tag_segments(segments)
        entities = self._extract_named_entities(segments)
        summaries = [self._summarize_text(segment) for segment in segments]
        return {"toc": toc, "segments": segments, "tags": tags, "entities": entities, "summary": summaries}

    def _summarize_video(self, file_path):
        transcribed_text = extract_text_from_video(file_path)
        segments = self._segment_text(transcribed_text)
        toc = self._generate_toc(segments)
        tags = self._tag_segments(segments)
        entities = self._extract_named_entities(segments)
        summaries = [self._summarize_text(segment) for segment in segments]
        return {"toc": toc, "segments": segments, "tags": tags, "entities": entities, "summary": summaries}

    def _summarize_text(self, text):
        if not text or not text.strip():
            return ""

        # Clean and sanitize text to avoid content filter issues
        cleaned_text = self._clean_text_for_summary(text)
        
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                prompt = self._get_safe_summary_prompt(cleaned_text)
                
                resp = openai.ChatCompletion.create(
                    engine=self.openai_engine,
                    messages=[
                        {"role": "system", "content": "You are an academic document analysis assistant that provides objective, factual summaries."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=300,
                    temperature=0.3,  # Lower temperature for more consistent, safer output
                    timeout=30
                )
                return resp["choices"][0]["message"]["content"].strip()

            except openai.error.InvalidRequestError as e:
                # Handle content filter specifically
                if "content_filter" in str(e).lower() or "content management policy" in str(e).lower():
                    logger.warning(f"Content filter triggered on attempt {attempt + 1}. Error: {e}")
                    
                    if attempt < max_attempts - 1:
                        # Try with even more sanitized content
                        cleaned_text = self._apply_aggressive_content_cleaning(cleaned_text)
                        logger.info(f"Applying aggressive content cleaning for retry {attempt + 2}")
                        continue
                    else:
                        # Final attempt failed - return a safe fallback
                        logger.error(f"All content filter attempts failed. Returning fallback summary.")
                        return self._generate_fallback_summary(text)
                else:
                    # Other invalid request errors
                    raise e

            except openai.error.RateLimitError as e:
                # Rotate credentials and re-raise for Celery retry
                logger.warning(f"Rate limit encountered, rotating credentials and retrying via Celery: {e}")
                self._use_new_credentials()
                raise

            except openai.error.OpenAIError as e:
                logger.error(f"OpenAI API error on attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    # Rotate credentials and try again
                    self._use_new_credentials()
                    continue
                raise e
                
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    continue
                raise RuntimeError(f"Unexpected summarization error after {max_attempts} attempts: {str(e)}")

    def _clean_text_for_summary(self, text):
        """
        Clean and sanitize text to avoid Azure OpenAI content filter issues.
        """
        import re
        
        # Remove potentially problematic content patterns
        # Remove URLs and email addresses
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '[URL]', text)
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        
        # Remove phone numbers
        text = re.sub(r'[\+]?[1-9]?[0-9]{3}[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}', '[PHONE]', text)
        
        # Remove potential personal identifiers (SSNs, credit card patterns)
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[ID]', text)
        text = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD]', text)
        
        # Truncate very long text to avoid hitting limits
        if len(text) > 3000:
            text = text[:3000] + "...(truncated for processing)"
        
        return text.strip()

    def _get_safe_summary_prompt(self, text):
        """
        Create a safe prompt that's less likely to trigger content filters.
        """
        # Use a more neutral, academic tone
        prompt = (
            "Please analyze and summarize the following document content. "
            "Provide a factual, objective summary focusing on the main topics, "
            "key information, and important concepts discussed.\n\n"
            f"Content:\n{text}"
        )
        
        return prompt

    def _apply_aggressive_content_cleaning(self, text):
        """
        Apply more aggressive content cleaning for problematic text.
        """
        import re
        
        # Keep only alphanumeric characters, basic punctuation, and whitespace
        text = re.sub(r'[^\w\s\.\,\!\?\-\:\;\(\)]', ' ', text)
        
        # Remove excessive whitespace and newlines
        text = re.sub(r'\s+', ' ', text)
        
        # Further truncate
        if len(text) > 2000:
            text = text[:2000] + "...(content truncated for safety)"
        
        return text.strip()

    def _generate_fallback_summary(self, text):
        """
        Generate a simple fallback summary when AI summarization fails.
        """
        # Basic text analysis
        words = text.split()
        sentences = text.split('.')
        
        word_count = len(words)
        sentence_count = len([s for s in sentences if s.strip()])
        
        # Extract first few words of each paragraph
        paragraphs = text.split('\n\n')
        key_phrases = []
        for para in paragraphs[:3]:
            if para.strip():
                words_in_para = para.strip().split()[:10]
                key_phrases.append(' '.join(words_in_para))
        
        fallback = f"Document Summary (automated): This content contains approximately {word_count} words across {sentence_count} sentences. "
        
        if key_phrases:
            fallback += f"Key sections include: {'; '.join(key_phrases)}..."
        
        fallback += " [Note: Full AI summarization was not available for this content]"
        
        return fallback

    def _segment_text(self, text):
        return text.split('\n\n')

    def _generate_toc(self, segments):
        return [f"Section {i+1}: {segment[:30]}..." for i, segment in enumerate(segments)]

    def _tag_segments(self, segments):
        tags = []
        for segment in segments:
            tags.append(self._tag_segment(segment))
        return tags

    def _tag_segment(self, segment):
        resp = openai.ChatCompletion.create(
            engine=self.openai_engine,
            messages=[
                {"role": "system", "content": "You are a keyword extraction assistant."},
                {"role": "user", "content": f"Assign tags to the following text:\n\n{segment}"}
            ],
            max_tokens=50
        )
        return resp["choices"][0]["message"]["content"].strip()

    def _extract_named_entities(self, segments):
        return [self._extract_entities(s) for s in segments]

    def _extract_entities(self, segment):
        prompt = (
            "Extract named entities (e.g., people, organizations, locations) from the following text. "
            "Format the output as a list of entities in JSON format:\n\n"
            f"Text:\n{segment}"
        )
        resp = openai.ChatCompletion.create(
            engine=self.openai_engine,
            messages=[
                {"role": "system", "content": "You are a named entity recognition assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200
        )
        try:
            return json.loads(resp["choices"][0]["message"]["content"].strip())
        except json.JSONDecodeError:
            return []

    def generate_overall_summary(self, page_summaries, total_pages):
        """
        Generate an overall document summary from page summaries.
        Intelligently samples pages based on document length to stay under token limits.

        Args:
            page_summaries: List of (page_number, summary_text) tuples
            total_pages: Total number of pages in document

        Returns:
            str: Overall summary of the document
        """
        if not page_summaries:
            return "No summary available."

        # Determine sampling strategy based on document size
        if total_pages <= 10:
            # Small doc: use all summaries
            selected_summaries = page_summaries
        elif total_pages <= 50:
            # Medium doc: every 3rd page
            selected_summaries = [s for i, s in enumerate(page_summaries) if i % 3 == 0]
        elif total_pages <= 100:
            # Large doc: every 10th page
            selected_summaries = [s for i, s in enumerate(page_summaries) if i % 10 == 0]
        else:
            # Very large doc: every 20th page
            selected_summaries = [s for i, s in enumerate(page_summaries) if i % 20 == 0]

        # Build condensed input
        condensed_input = "\n\n".join([
            f"Page {page_num}: {summary[:500]}"  # Limit each summary to 500 chars
            for page_num, summary in selected_summaries
        ])

        # Truncate if still too long (keep under ~3000 tokens = ~12000 chars)
        if len(condensed_input) > 12000:
            condensed_input = condensed_input[:12000] + "..."

        prompt = f"""Based on the following page summaries from a {total_pages}-page document, provide a comprehensive overall summary that captures the main themes, key points, and conclusions.

Page Summaries:
{condensed_input}

Provide a well-structured overall summary (200-400 words) that gives readers a clear understanding of the entire document."""

        try:
            resp = openai.ChatCompletion.create(
                engine=self.openai_engine,
                messages=[
                    {"role": "system", "content": "You are an expert document summarization assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=600,
                temperature=0.5,
                timeout=45
            )
            return resp["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"Error generating overall summary: {e}")
            return f"Unable to generate overall summary. Document contains {total_pages} pages."