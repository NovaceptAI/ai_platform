from __future__ import annotations
from typing import Dict, Any, List
import logging, os
from app.services.external.azure_image import azure_dalle_generate
log = logging.getLogger(__name__)

class StoryToComicsConverterService:
    """
    Splits story text into panels with captions + prompts.
    Optionally generates images via Azure DALL·E when enabled.
    """

    @staticmethod
    def _segment(text: str, n: int) -> List[str]:
        sents = [s.strip() for s in text.replace("\n"," ").split(".") if s.strip()]
        if not sents:
            sents = ["A quiet day in the village", "A fox appears", "A child follows the fox"]
        step = max(1, len(sents)//n)
        chunks = [". ".join(sents[i:i+step]) for i in range(0, len(sents), step)][:n]
        return chunks

    @staticmethod
    def process(payload: Dict[str, Any]) -> Dict[str, Any]:
        p = (payload.get("params") or {})
        text = (p.get("story") or "").strip()
        style = p.get("style") or "cartoon"
        n = max(1, min(int(p.get("panels") or 6), 12))
        do_images = bool(p.get("generate_images"))

        chunks = StoryToComicsConverterService._segment(text, n)
        panels = []
        for i, chunk in enumerate(chunks, start=1):
            prompt = f"{style}, kid-friendly comic panel, {chunk[:120]}..."
            panels.append({"idx":i, "caption":chunk, "speech":[], "image_url":None, "image_prompt":prompt})

        if do_images:
            # limit to 4 panels to control cost/time
            for panel in panels[:4]:
                items = azure_dalle_generate(panel["image_prompt"], size="1024x1024", style="vivid", quality="standard", n=1)
                if items and (u := items[0].get("url")):
                    panel["image_url"] = u

        return {"title":"Story to Comics Converter","panels":panels}