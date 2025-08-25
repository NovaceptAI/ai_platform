from __future__ import annotations
from typing import Dict, Any, List, Tuple
import logging, math
log = logging.getLogger(__name__)

class LearnByDrawingService:
    """
    Naive shape recognition on point paths (circle/square-ish).
    Frontend sends downsampled paths: [{points:[[x,y], ...]}, ...]
    """

    @staticmethod
    def _detect_shape(points: List[List[float]]) -> Tuple[str, float]:
        xs, ys = zip(*points)
        cx, cy = (sum(xs)/len(xs), sum(ys)/len(ys))
        dists = [math.hypot(x-cx, y-cy) for x,y in points]
        mean = sum(dists)/len(dists)
        var = sum((d-mean)**2 for d in dists)/len(dists)
        # low variance -> circle-ish
        if var < (0.1 * mean):
            return ("circle", 0.8)
        # aspect ratio test -> rectangle-ish
        w, h = (max(xs)-min(xs), max(ys)-min(ys))
        ar = w/h if h else 999
        if 0.6 <= ar <= 1.4 and var >= (0.1*mean):
            return ("square-ish", 0.6)
        return ("unknown", 0.3)

    @staticmethod
    def process(payload: Dict[str, Any]) -> Dict[str, Any]:
        paths = ((payload.get("params") or {}).get("paths") or [])
        detected = []
        for p in paths:
            pts = p.get("points") or []
            if len(pts) < 12: continue
            shape, conf = LearnByDrawingService._detect_shape(pts)
            if shape != "unknown": detected.append({"shape":shape,"confidence":round(conf,2)})

        feedback = ["Great circle! Try adding a square next."] if any(d["shape"]=="circle" for d in detected) else ["Try a circle—keep the distance from center even."]
        quiz = [{"q":"How many sides does a square have?","a":["3","4","5"],"correct":1}]
        return {"title":"Learn by Drawing","detected":detected,"feedback":feedback,"quiz":quiz}