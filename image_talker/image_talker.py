import requests
import os
from sadtalker import SadTalker  # Assuming SadTalker is a module you have for generating speaking animations

# ElevenLabs API Configuration
ELEVENLABS_API_KEY = "YOUR_ELEVENLABS_API_KEY"  # Replace with your actual ElevenLabs API key
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech"

# Function to convert text to speech using ElevenLabs API
def text_to_speech(text, voice_id, model_id, output_format):
    headers = {
        "Authorization": f"Bearer {ELEVENLABS_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "voice_id": voice_id,
        "model_id": model_id,
        "output_format": output_format
    }
    response = requests.post(ELEVENLABS_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        audio_content = response.content
        with open("output_audio.mp3", "wb") as audio_file:
            audio_file.write(audio_content)
        return "output_audio.mp3"
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")

# Function to make an image speak using SadTalker
def make_image_speak(image_path, audio_path):
    sadtalker = SadTalker()
    sadtalker.generate_speaking_animation(image_path, audio_path, output_path="output_video.mp4")
    return "output_video.mp4"

# Main function
def main():
    image_path = "path_to_image.jpg"  # Replace with the path to your image
    text = "The first move is what sets everything in motion."
    voice_id = "JBFqnCBsd6RMkjVDRZzb"
    model_id = "eleven_multilingual_v2"
    output_format = "mp3_44100_128"

    # Convert text to speech
    audio_path = text_to_speech(text, voice_id, model_id, output_format)
    print(f"Audio saved to {audio_path}")

    # Make the image speak
    video_path = make_image_speak(image_path, audio_path)
    print(f"Video saved to {video_path}")

if __name__ == "__main__":
    main()