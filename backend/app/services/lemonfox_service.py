import requests

def transcribe_audio(temp_audio_path):
    url = "https://api.lemonfox.ai/v1/audio/transcriptions"
    headers = {
        "Authorization": "Bearer cIVYjRhCUlHt36U6oRs20qYt3IpKrZxJ"
    }
    data = {
        "language": "english",
        "response_format": "srt"
    }
    with open(temp_audio_path, "rb") as audio_file:
        files = {"file": audio_file}
        response = requests.post(url, headers=headers, files=files, data=data)
    
    return response.json()      