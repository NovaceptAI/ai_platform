import os
import openai
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Helper to parse CSV env vars cleanly
def split_env_list(varname):
    raw = os.getenv(varname, "")
    return [item.strip() for item in raw.split(",") if item.strip()]

# Load keys and bases
AZURE_OPENAI_API_KEYS = split_env_list("AZURE_OPENAI_API_KEYS")
AZURE_OPENAI_API_BASES = split_env_list("AZURE_OPENAI_API_BASES")

DEPLOYMENT_NAME = "gpt-4.1"  # must match your Azure deployment
API_VERSION = "2023-03-15-preview"

for idx, (key, base) in enumerate(zip(AZURE_OPENAI_API_KEYS, AZURE_OPENAI_API_BASES), start=1):
    print(f"\n--- Testing key #{idx} ---")
    try:
        openai.api_type = "azure"
        openai.api_key = key
        openai.api_base = base
        openai.api_version = API_VERSION

        resp = openai.ChatCompletion.create(
            engine=DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "You are a test."},
                {"role": "user", "content": "Say 'Hello'."}
            ],
            max_tokens=5
        )

        print(f"[OK] Key #{idx} valid. Response: {resp['choices'][0]['message']['content']}")
    except Exception as e:
        print(f"[FAIL] Key #{idx} failed: {e}")