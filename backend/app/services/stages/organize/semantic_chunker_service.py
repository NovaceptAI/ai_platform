# app/services/stages/organize/semantic_chunker_service.py
import logging
from typing import List, Dict, Any
from collections import defaultdict
import re

log = logging.getLogger(__name__)

class SemanticChunkerService:
    """
    Service for extracting semantic chunks from documents.
    Instead of treating each page as a unit, this groups content by semantic coherence.
    """

    def __init__(self):
        self.min_chunk_size = 100  # minimum words per chunk
        self.max_chunk_size = 1000  # maximum words per chunk
        self.overlap_sentences = 1  # sentences to overlap between chunks

    def extract_semantic_chunks(self, pages: List[Dict[str, Any]], file_topics: List[str] = None, file_entities: Dict = None) -> List[Dict[str, Any]]:
        """
        Extract semantic chunks from document pages.

        Args:
            pages: List of page data with page_number, page_summary
            file_topics: Optional list of document-level topics
            file_entities: Optional dict of document-level entities

        Returns:
            List of semantic chunks with content, topics, entities
        """
        if not pages:
            return []

        file_topics = file_topics or []
        file_entities = file_entities or {}

        # Strategy 1: Try to detect natural section boundaries
        chunks = self._extract_by_topic_coherence(pages, file_topics)

        # If that produces too few chunks, fall back to paragraph-based chunking
        if len(chunks) < 2:
            chunks = self._extract_by_paragraph_structure(pages)

        # Enrich chunks with topics and entities
        enriched_chunks = self._enrich_chunks(chunks, file_topics, file_entities)

        log.info(f"[SemanticChunker] Extracted {len(enriched_chunks)} semantic chunks from {len(pages)} pages")
        return enriched_chunks

    def _extract_by_topic_coherence(self, pages: List[Dict[str, Any]], topics: List[str]) -> List[Dict[str, Any]]:
        """
        Group pages by topic coherence - pages that share similar topics go together.
        """
        if not topics or len(topics) < 2:
            return self._extract_by_paragraph_structure(pages)

        chunks = []
        current_chunk = {
            "pages": [],
            "content": "",
            "dominant_topics": set()
        }

        for page in pages:
            page_summary = page.get("page_summary", "")
            page_num = page.get("page_number", 0)

            # Find which topics are mentioned in this page
            page_topics = set()
            for topic in topics:
                if topic.lower() in page_summary.lower():
                    page_topics.add(topic)

            # If no topics found, extract keywords
            if not page_topics:
                page_topics = self._extract_keywords(page_summary)

            # Check if this page belongs to current chunk (shares topics)
            if not current_chunk["pages"]:
                # First page - start new chunk
                current_chunk["pages"].append(page_num)
                current_chunk["content"] = page_summary
                current_chunk["dominant_topics"] = page_topics
            elif page_topics & current_chunk["dominant_topics"]:
                # Shares topics - add to current chunk
                current_chunk["pages"].append(page_num)
                current_chunk["content"] += " " + page_summary
                current_chunk["dominant_topics"].update(page_topics)
            else:
                # Different topics - save current chunk and start new one
                if len(current_chunk["content"].split()) >= self.min_chunk_size:
                    chunks.append(current_chunk)
                else:
                    # Chunk too small, merge with next
                    current_chunk["pages"].append(page_num)
                    current_chunk["content"] += " " + page_summary
                    current_chunk["dominant_topics"].update(page_topics)
                    continue

                current_chunk = {
                    "pages": [page_num],
                    "content": page_summary,
                    "dominant_topics": page_topics
                }

        # Don't forget the last chunk
        if current_chunk["pages"]:
            chunks.append(current_chunk)

        return chunks

    def _extract_by_paragraph_structure(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract chunks based on paragraph structure and natural breaks.
        Combines all content and splits by semantic boundaries.
        """
        # Combine all page summaries
        full_content = ""
        page_map = {}  # Track which pages contribute to which part of content

        for page in pages:
            page_summary = page.get("page_summary", "")
            if page_summary:
                start_pos = len(full_content)
                full_content += page_summary + " "
                page_map[start_pos] = page.get("page_number", 0)

        if not full_content.strip():
            return []

        # Split into sentences
        sentences = self._split_into_sentences(full_content)

        if len(sentences) < 3:
            # Not enough sentences, return as single chunk
            return [{
                "pages": [p.get("page_number", 0) for p in pages],
                "content": full_content,
                "dominant_topics": set()
            }]

        # Group sentences into chunks of similar size
        chunks = []
        current_chunk = {
            "pages": [],
            "content": "",
            "sentences": [],
            "dominant_topics": set()
        }

        target_sentences_per_chunk = max(3, len(sentences) // max(2, len(sentences) // 5))

        for i, sentence in enumerate(sentences):
            current_chunk["sentences"].append(sentence)

            # Check if we should end this chunk
            should_end = False

            # Natural break indicators
            if len(current_chunk["sentences"]) >= target_sentences_per_chunk:
                should_end = True
            elif self._is_section_break(sentence):
                should_end = True

            if should_end and len(current_chunk["sentences"]) >= 2:
                chunk_content = " ".join(current_chunk["sentences"])
                chunk_pages = self._find_pages_for_content(chunk_content, pages)

                chunks.append({
                    "pages": chunk_pages,
                    "content": chunk_content,
                    "dominant_topics": set()
                })

                # Start new chunk with overlap
                if self.overlap_sentences > 0 and i < len(sentences) - 1:
                    current_chunk = {
                        "pages": [],
                        "content": "",
                        "sentences": current_chunk["sentences"][-self.overlap_sentences:],
                        "dominant_topics": set()
                    }
                else:
                    current_chunk = {
                        "pages": [],
                        "content": "",
                        "sentences": [],
                        "dominant_topics": set()
                    }

        # Handle remaining sentences
        if current_chunk["sentences"]:
            chunk_content = " ".join(current_chunk["sentences"])
            chunk_pages = self._find_pages_for_content(chunk_content, pages)
            chunks.append({
                "pages": chunk_pages,
                "content": chunk_content,
                "dominant_topics": set()
            })

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _is_section_break(self, sentence: str) -> bool:
        """Check if sentence indicates a section break."""
        break_indicators = [
            r'^chapter\s+\d+',
            r'^section\s+\d+',
            r'^part\s+\d+',
            r'^\d+\.\s+[A-Z]',  # Numbered sections like "1. Introduction"
            r'^[A-Z][A-Z\s]{5,}$',  # All caps headers
        ]

        for pattern in break_indicators:
            if re.search(pattern, sentence.strip(), re.IGNORECASE):
                return True
        return False

    def _find_pages_for_content(self, content: str, pages: List[Dict[str, Any]]) -> List[int]:
        """Find which pages contributed to this content."""
        contributing_pages = []

        # Check each page's summary for overlap with chunk content
        content_lower = content.lower()
        for page in pages:
            page_summary = page.get("page_summary", "").lower()
            if page_summary and len(page_summary) > 20:
                # Check if significant portion of page summary is in chunk
                words = page_summary.split()[:10]  # First 10 words
                match_count = sum(1 for w in words if w in content_lower)
                if match_count >= 5:  # At least 5 words match
                    contributing_pages.append(page.get("page_number", 0))

        if not contributing_pages:
            # Fallback: just use first page
            contributing_pages = [pages[0].get("page_number", 0)] if pages else [1]

        return sorted(set(contributing_pages))

    def _extract_keywords(self, text: str, top_n: int = 5) -> set:
        """Extract top keywords from text."""
        if not text:
            return set()

        # Simple keyword extraction
        words = [w.lower().strip('.,!?;:()[]"\'') for w in text.split() if len(w) > 5]
        word_freq = defaultdict(int)

        for w in words:
            if w.isalpha():
                word_freq[w] += 1

        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:top_n]
        return {w for w, _ in top_words}

    def _enrich_chunks(self, chunks: List[Dict[str, Any]], file_topics: List[str], file_entities: Dict) -> List[Dict[str, Any]]:
        """Add topic and entity information to each chunk."""
        enriched = []

        for i, chunk in enumerate(chunks):
            content = chunk.get("content", "")
            content_lower = content.lower()

            # Find topics mentioned in this chunk
            chunk_topics = list(chunk.get("dominant_topics", set()))
            if not chunk_topics:
                for topic in file_topics:
                    if topic.lower() in content_lower:
                        chunk_topics.append(topic)

            # If still no topics, extract keywords
            if not chunk_topics:
                chunk_topics = list(self._extract_keywords(content))

            # Find entities in this chunk
            chunk_entities = {}
            for entity_type, entities in file_entities.items():
                matched = []
                for entity in entities[:15]:
                    entity_text = entity if isinstance(entity, str) else str(entity)
                    if entity_text.lower() in content_lower:
                        matched.append(entity_text)
                if matched:
                    chunk_entities[entity_type] = matched

            # Create summary for the chunk (first 100 words)
            words = content.split()
            summary = " ".join(words[:100]) + ("..." if len(words) > 100 else "")

            enriched.append({
                "chunk_id": f"chunk_{i}",
                "pages": chunk.get("pages", []),
                "content": content,
                "summary": summary,
                "topics": chunk_topics,
                "entities": chunk_entities,
                "word_count": len(words)
            })

        return enriched
