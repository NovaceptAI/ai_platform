from __future__ import annotations
from typing import Dict, Any
import logging
log = logging.getLogger(__name__)

class ThreeDModelBuilderService:
    """
    Turns a simple text prompt into a 3D scene spec (primitives).
    Frontend can render via Three.js (sphere/box/plane/cone).
    """

    @staticmethod
    def _add(scene: Dict[str, Any], obj: Dict[str, Any]):
        scene["objects"].append(obj)

    @staticmethod
    def process(payload: Dict[str, Any]) -> Dict[str, Any]:
        params = (payload.get("params") or {})
        prompt = (params.get("prompt") or "").lower().strip()
        scene = {"units": "meters", "background": "#0b1225", "objects": []}

        if "snowman" in prompt:
            ThreeDModelBuilderService._add(scene, {"id":"body","type":"sphere","position":[0,0.6,0],"scale":[0.6,0.6,0.6],"color":"#e5e7eb"})
            ThreeDModelBuilderService._add(scene, {"id":"head","type":"sphere","position":[0,1.2,0],"scale":[0.35,0.35,0.35],"color":"#ffffff"})
            ThreeDModelBuilderService._add(scene, {"id":"nose","type":"cone","position":[0,1.2,0.31],"scale":[0.05,0.2,0.05],"rotation":[-1.57,0,0],"color":"#f97316"})
        elif "solar" in prompt or "planet" in prompt:
            radii = [1,1.6,2.2,3,3.8,4.6,5.4,6.2]
            for i, r in enumerate(radii, start=1):
                ThreeDModelBuilderService._add(scene, {
                    "id": f"planet{i}", "type": "sphere", "position": [r,0,0],
                    "scale":[0.2,0.2,0.2], "color": f"#{20*i:02x}40{200-10*i:02x}"
                })
        else:
            ThreeDModelBuilderService._add(scene, {"id":"ground","type":"plane","position":[0,0,0],"scale":[10,10,1],"rotation":[-1.57,0,0],"color":"#111827"})
            ThreeDModelBuilderService._add(scene, {"id":"cube","type":"box","position":[0,0.5,0],"scale":[1,1,1],"color":"#8b5cf6"})
            ThreeDModelBuilderService._add(scene, {"id":"ball","type":"sphere","position":[1.6,0.3,-0.5],"scale":[0.3,0.3,0.3],"color":"#34d399"})

        return {"title":"3D Model Builder","scene":scene}