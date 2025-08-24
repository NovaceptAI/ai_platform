from __future__ import annotations
from typing import Dict, Any
import logging

log = logging.getLogger(__name__)


class LearnByDrawingService:
    """
    Service layer for Learn by Drawing.
    Implements pure functions that the Celery task can call.
    Replace 'process' with real logic when ready.
    """

    @staticmethod
    def process(input_payload: Dict[str, Any]) -> Dict[str, Any]:
        log.info("Learn by Drawing service processing start")
        dummy = {
            "summary": f"Learn by Drawing placeholder result for input={input_payload!r}",
            "chunks": [],
            "meta": {"version": 1},
        }
        log.info("Learn by Drawing service processing done")
        return dummy