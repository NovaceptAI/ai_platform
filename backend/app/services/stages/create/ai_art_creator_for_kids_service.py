from __future__ import annotations
from typing import Dict, Any, List
import logging
from app.services.external.azure_image import azure_dalle_generate
log = logging.getLogger(__name__)

class AiArtCreatorForKidsService:
    STYLES = {
        "crayon":"childlike crayon drawing, bold colors, simple shapes",
        "watercolor":"soft watercolor painting, pastel, gentle wash",
        "comic":"clean lines, comic style for kids, bright colors"
    }

    @staticmethod
    def process(payload: Dict[str, Any]) -> Dict[str, Any]:
        p = (payload.get("params") or {})
        prompt = p.get("prompt") or "A happy scene"
        style_phrase = AiArtCreatorForKidsService.STYLES.get(p.get("style","crayon"), AiArtCreatorForKidsService.STYLES["crayon"])
        count = max(1, min(int(p.get("count") or 4), 6))

        final_prompt = f"{style_phrase}; {prompt}"
        items = azure_dalle_generate(final_prompt, size="1024x1024", style="vivid", quality="standard", n=count)

        images = []
        # Prefer URL if present; otherwise propagate b64_json (frontend can handle)
        for i, it in enumerate(items, start=1):
            images.append({"idx": i, "prompt": final_prompt, "image_url": it.get("url"), "b64_json": it.get("b64_json")})

        # If Azure not configured, still return prompts
        if not images:
            images = [{"idx": i+1, "prompt": final_prompt, "image_url": None} for i in range(count)]

        return {"title":"AI Art Creator for Kids","images": images}