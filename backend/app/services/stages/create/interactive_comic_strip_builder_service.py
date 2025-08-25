from __future__ import annotations
from typing import Dict, Any
import logging
log = logging.getLogger(__name__)

class InteractiveComicStripBuilderService:
    """
    Initializes a comic project template for DnD editing on frontend.
    """

    @staticmethod
    def process(payload: Dict[str, Any]) -> Dict[str, Any]:
        template = ((payload.get("params") or {}).get("template") or "3-panel")
        count = 3 if "3" in template else 4 if "4" in template else 6
        project = {"panels":[{"idx":i,"image_url":None,"caption":"","speech":[]} for i in range(1, count+1)]}
        return {"title":"Interactive Comic Strip Builder","project":project}