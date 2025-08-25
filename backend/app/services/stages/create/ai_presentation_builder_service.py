from __future__ import annotations
from typing import Dict, Any, List
import logging
log = logging.getLogger(__name__)

class AiPresentationBuilderService:
    """
    Generates slide outline + markdown based on topic/audience/count.
    """

    @staticmethod
    def process(payload: Dict[str, Any]) -> Dict[str, Any]:
        p = (payload.get("params") or {})
        topic = p.get("topic") or "Untitled Topic"
        audience = p.get("audience") or "General Audience"
        n = max(5, min(int(p.get("slides") or 8), 20))

        outline = [
            "Introduction", f"Why {topic} matters", f"Core Concepts of {topic}",
            "Examples", "Activities / Interaction", "Common Misconceptions",
            "Quick Recap", "Q&A"
        ]
        while len(outline) < n:
            outline.append(f"More on {topic} {len(outline)+1}")

        slides = []
        for title in outline[:n]:
            slides.append({
                "title": title,
                "bullets": [f"{topic} overview for {audience}", "Key point 1", "Key point 2"]
            })

        md_parts = []
        for i, s in enumerate(slides, start=1):
            md_parts.append(f"# Slide {i}: {s['title']}\n" + "\n".join(f"- {b}" for b in s["bullets"]))

        return {
            "title": "AI Presentation Builder",
            "slides": slides,
            "markdown": "\n\n".join(md_parts),
            "pptx_url": None
        }