import requests

def transcribe_audio():
    url = "https://api.lemonfox.ai/v1/audio/transcriptions"
    headers = {
        "Authorization": "Bearer cIVYjRhCUlHt36U6oRs20qYt3IpKrZxJ"
    }
    data = {
        "language": "tamil",
        "response_format": "srt"
    }
    files = {"file": open("C:/Users/novneet.patnaik/Downloads/transcribe_input_audios/Mahindra_Video_Tamil.mp3", "rb")}
    response = requests.post(url, headers=headers, files=files, data=data)
    return response.json()