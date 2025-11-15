# app/services/stages/collaborate/mind_map_ai_service.py
import os
import json
import logging
from typing import Dict, List, Any
import openai
from app.services.openai_key_manager import key_manager

log = logging.getLogger(__name__)

OPENAI_API_TYPE = "azure"
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")
DEFAULT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")

class MindMapAIService:
    """AI assistance for collaborative mind mapping."""

    def __init__(self, openai_engine: str = DEFAULT_DEPLOYMENT):
        self.openai_engine = openai_engine
        self._use_new_credentials()

    def _use_new_credentials(self):
        api_key, api_base, idx = key_manager.get_next()
        openai.api_type = OPENAI_API_TYPE
        openai.api_version = OPENAI_API_VERSION
        openai.api_key = api_key
        openai.api_base = api_base
        log.info(f"[MindMapAI] Using Azure OpenAI slot #{idx}")

    def _chat(self, messages, temperature=0.7, max_tokens=800, timeout=40) -> str:
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
            log.error(f"[MindMapAI] OpenAI API error: {e}")
            self._use_new_credentials()
            raise

    def expand_node(self, node_content: str, context: Dict[str, Any]) -> List[str]:
        """Suggest child nodes/subtopics for a given node."""
        prompt = f"""You are helping expand a mind map. Given a node with the content:
"{node_content}"

Context: The mind map is about {context.get('mind_map_title', 'various topics')}.

Suggest 3-5 related subtopics or child ideas that would make sense to branch from this node.
Return as a JSON array of strings:
["subtopic1", "subtopic2", "subtopic3"]

Keep suggestions concise and relevant."""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self._chat(messages, temperature=0.8)
            suggestions = self._parse_json_array(response)
            return suggestions[:5]
        except Exception as e:
            log.error(f"[MindMapAI] Expand node error: {e}")
            return []

    def suggest_connections(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Suggest hidden relationships between nodes."""
        if len(nodes) < 2:
            return []

        nodes_summary = "\n".join([f"- {i+1}. {n.get('content', n.get('title', ''))}" for i, n in enumerate(nodes)])

        prompt = f"""Given these mind map nodes:
{nodes_summary}

Identify 2-3 meaningful connections/relationships between these nodes that might not be obvious.
Return as JSON array:
[
  {{"source_index": 1, "target_index": 3, "reason": "Both relate to...", "label": "causes"}}
]

Only suggest strong, logical connections."""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self._chat(messages, temperature=0.6)
            connections = self._parse_json_response(response)
            return connections if isinstance(connections, list) else []
        except Exception as e:
            log.error(f"[MindMapAI] Suggest connections error: {e}")
            return []

    def generate_summary(self, nodes: List[Dict[str, Any]], branch_name: str = None) -> str:
        """Generate a summary paragraph from a branch of nodes."""
        nodes_content = "\n".join([f"- {n.get('content', n.get('title', ''))}" for n in nodes])

        prompt = f"""Summarize the following mind map branch{' about ' + branch_name if branch_name else ''} into a coherent paragraph:

{nodes_content}

Write a clear, concise summary (2-3 sentences)."""

        try:
            messages = [{"role": "user", "content": prompt}]
            return self._chat(messages, temperature=0.5, max_tokens=300)
        except Exception as e:
            log.error(f"[MindMapAI] Generate summary error: {e}")
            return "Unable to generate summary."

    def extract_concepts_from_document(self, document_text: str, max_concepts: int = 10) -> List[Dict[str, str]]:
        """Extract key concepts from a document to create initial mind map nodes."""
        prompt = f"""Extract the {max_concepts} most important concepts/topics from this text:

{document_text[:3000]}

Return as JSON array:
[
  {{"concept": "concept name", "description": "brief description"}}
]

Focus on main ideas and key topics."""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self._chat(messages, temperature=0.5, max_tokens=600)
            concepts = self._parse_json_response(response)
            return concepts if isinstance(concepts, list) else []
        except Exception as e:
            log.error(f"[MindMapAI] Extract concepts error: {e}")
            return []

    def _parse_json_array(self, response: str) -> List[str]:
        """Parse JSON array from response."""
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            elif response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            start_idx = response.find('[')
            end_idx = response.rfind(']')
            if start_idx == -1 or end_idx == -1:
                return []

            json_str = response[start_idx:end_idx + 1]
            return json.loads(json_str)
        except Exception as e:
            log.error(f"[MindMapAI] JSON array parse error: {e}")
            return []

    def _parse_json_response(self, response: str) -> Any:
        """Parse JSON object or array from response."""
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            elif response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            # Try to find JSON structure
            for start_char, end_char in [('[', ']'), ('{', '}')]:
                start_idx = response.find(start_char)
                end_idx = response.rfind(end_char)
                if start_idx != -1 and end_idx != -1:
                    json_str = response[start_idx:end_idx + 1]
                    return json.loads(json_str)

            return {}
        except Exception as e:
            log.error(f"[MindMapAI] JSON parse error: {e}")
            return {}
