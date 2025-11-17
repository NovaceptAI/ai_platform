import os, requests, logging
from typing import List, Dict

logger = logging.getLogger(__name__)

# Try to get endpoint from multiple sources
AZ_IMG_ENDPOINT = "https://scoolish-openai.openai.azure.com/"
AZ_IMG_DEPLOYMENT = os.getenv("AZURE_OPENAI_IMAGE_DEPLOYMENT", "dall-e-3")
AZ_IMG_VERSION = os.getenv("AZURE_OPENAI_IMAGE_API_VERSION", "2024-02-01")

# Try to get API key from multiple sources (matching the pattern used elsewhere)
AZ_API_KEY = (
    os.getenv("AZURE_OPENAI_API_KEY") or 
    os.getenv("AZURE_IMAGE_API_KEY") or 
    (os.getenv("AZURE_OPENAI_API_KEYS", "").split(",")[0].strip() if os.getenv("AZURE_OPENAI_API_KEYS") else "")
)

def azure_dalle_generate(prompt: str, size: str = "1024x1024", style: str = "vivid",
                         quality: str = "standard", n: int = 1) -> List[Dict]:
    """
    Returns a list of {"url": "..."} or {"b64_json": "..."} items from Azure DALL·E.
    """
    # Debug logging
    logger.info(f"DALL-E Config Check:")
    logger.info(f"  Endpoint: {'SET' if AZ_IMG_ENDPOINT else 'NOT SET'} ({len(AZ_IMG_ENDPOINT) if AZ_IMG_ENDPOINT else 0} chars)")
    logger.info(f"  API Key: {'SET' if AZ_API_KEY else 'NOT SET'} ({len(AZ_API_KEY) if AZ_API_KEY else 0} chars)")
    logger.info(f"  Deployment: {AZ_IMG_DEPLOYMENT}")
    logger.info(f"  API Version: {AZ_IMG_VERSION}")
    
    if not (AZ_IMG_ENDPOINT and AZ_API_KEY):
        logger.error(f"DALL-E credentials not configured! Endpoint: {bool(AZ_IMG_ENDPOINT)}, API Key: {bool(AZ_API_KEY)}")
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
    
    try:
        logger.info(f"Making DALL-E API call to: {url}")
        logger.info(f"Prompt: {prompt[:100]}...")
        r = requests.post(url, headers=headers, params=params, json=body, timeout=30)
        r.raise_for_status()
        data = r.json() or {}
        # Azure returns {"data":[{"url":...}]} or [{"b64_json":...}]
        items = data.get("data") or []
        logger.info(f"DALL-E returned {len(items)} items")
        return [{"url": it.get("url"), "b64_json": it.get("b64_json")} for it in items]
    except requests.exceptions.RequestException as e:
        logger.error(f"DALL-E API request failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
        raise