import requests

def translate_audio_with_azure_whisper(audio_path: str) -> str:
    """
    Translates non-English speech in an audio file to English using Azure OpenAI Whisper.

    Args:
        audio_path (str): Path to the audio file to translate.

    Returns:
        str: Translated text.
    """
    endpoint = "https://scool-mb23vwrz-swedencentral.cognitiveservices.azure.com/openai/deployments/whisper/audio/translations?api-version=2024-06-01"
    api_key = "CHStGQVfxNnxPtSmcuCdUM7uSWsmn3MIFvmeXIxQcuSfTmSqxKdMJQQJ99BEACfhMk5XJ3w3AAAAACOGF72B"

    headers = {
        "api-key": api_key,
    }

    data = {
        "response_format": "text",  # Can also be: "json", "srt", or "verbose_json"
    }

    with open(audio_path, "rb") as audio_file:
        files = {
            "file": (audio_path, audio_file, "audio/mpeg")
        }

        response = requests.post(endpoint, headers=headers, files=files, data=data)

    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"Translation failed [{response.status_code}]: {response.text}")