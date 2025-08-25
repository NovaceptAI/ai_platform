import os, requests
from typing import List, Dict
AZ_IMG_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
AZ_IMG_DEPLOYMENT = os.getenv("AZURE_OPENAI_IMAGE_DEPLOYMENT", "dall-e-3")
AZ_IMG_VERSION = os.getenv("AZURE_OPENAI_IMAGE_API_VERSION", "2024-02-01")
AZ_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", os.getenv("AZURE_API_KEY", ""))

def azure_dalle_generate(prompt: str, size: str = "1024x1024", style: str = "vivid",
                         quality: str = "standard", n: int = 1) -> List[Dict]:
    """
    Returns a list of {"url": "..."} or {"b64_json": "..."} items from Azure DALL·E.
    """
    if not (AZ_IMG_ENDPOINT and AZ_API_KEY):
        return []
    url = f"{AZ_IMG_ENDPOINT}/openai/deployments/{AZ_IMG_DEPLOYMENT}/images/generations"
    params = {"api-version": AZ_IMG_VERSION}
    body = {
        "model": AZ_IMG_DEPLOYMENT,  # Azure ignores; deployment is authoritative
        "prompt": prompt,
        "size": size,
        "style": style,
        "quality": quality,
        "n": max(1, min(int(n or 1), 6)),
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AZ_API_KEY}",
    }
    r = requests.post(url, headers=headers, params=params, json=body, timeout=30)
    r.raise_for_status()
    data = r.json() or {}
    # Azure returns {"data":[{"url":...}]} or [{"b64_json":...}]
    items = data.get("data") or []
    return [{"url": it.get("url"), "b64_json": it.get("b64_json")} for it in items]