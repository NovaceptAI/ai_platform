#!/usr/bin/env python3
"""
Test script to compare Azure Computer Vision vs GPT-4 Vision for drawing recognition.

Azure Computer Vision provides:
- Object detection
- Image tagging
- Image description
- OCR (text recognition)

GPT-4 Vision provides:
- Natural language understanding of images
- Educational context generation
- More flexible interpretation
"""

import os
import base64
import requests
import openai
from dotenv import load_dotenv

load_dotenv()

# Configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# ==================== Test Image ====================
# Create a simple test drawing (or use existing one)
TEST_IMAGE_PATH = "/tmp/test_drawing.png"

def test_azure_computer_vision(image_path: str):
    """
    Test Azure Computer Vision API for drawing analysis.

    Azure CV Analyze Image API provides:
    - visualFeatures: Categories, Tags, Description, Objects, Faces, Brands, Color
    - details: Celebrities, Landmarks
    """

    endpoint = os.getenv("AZURE_VISION_ENDPOINT")
    subscription_key = os.getenv("AZURE_VISION_KEY")

    if not endpoint or not subscription_key:
        print("❌ Azure Vision credentials not found in environment")
        return None

    # API endpoint for image analysis
    analyze_url = f"{endpoint}/vision/v3.2/analyze"

    print("\n🔵 Testing Azure Computer Vision...")
    print(f"Endpoint: {endpoint}")

    # Read image
    with open(image_path, "rb") as image_file:
        image_data = image_file.read()

    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Content-Type': 'application/octet-stream'
    }

    params = {
        'visualFeatures': 'Categories,Tags,Description,Objects,Color',
        'details': '',
        'language': 'en'
    }

    try:
        response = requests.post(
            analyze_url,
            headers=headers,
            params=params,
            data=image_data,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()

        print("\n✅ Azure Computer Vision Results:")
        print(f"Description: {result.get('description', {}).get('captions', [{}])[0].get('text', 'N/A')}")
        print(f"Confidence: {result.get('description', {}).get('captions', [{}])[0].get('confidence', 0):.2%}")
        print(f"\nTags detected:")
        for tag in result.get('tags', [])[:10]:
            print(f"  - {tag['name']}: {tag['confidence']:.2%}")

        print(f"\nObjects detected:")
        for obj in result.get('objects', []):
            print(f"  - {obj['object']}: {obj['confidence']:.2%}")

        print(f"\nColor analysis:")
        colors = result.get('color', {})
        print(f"  Dominant colors: {', '.join(colors.get('dominantColors', []))}")
        print(f"  Accent color: {colors.get('accentColor', 'N/A')}")

        return result

    except Exception as e:
        print(f"❌ Azure Vision Error: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return None


def test_gpt4_vision(image_path: str):
    """
    Test GPT-4 Vision for drawing analysis with educational context.

    GPT-4V is better for:
    - Understanding conceptual drawings
    - Providing educational feedback
    - Recognizing hand-drawn diagrams
    """

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        print("❌ OpenAI API key not found in environment")
        return None

    print("\n🟢 Testing GPT-4 Vision...")

    # Encode image to base64
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",  # or "gpt-4-vision-preview"
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Analyze this drawing made by a student. Identify:
1. What objects or concepts are drawn
2. What topic this relates to (water cycle, solar system, plant parts, etc.)
3. Educational feedback for the student (2-3 sentences, age-appropriate)
4. A score from 1-10 for how well they captured the concept

Format your response as JSON:
{
  "detected_objects": ["object1", "object2"],
  "topic": "topic name",
  "feedback": "educational feedback text",
  "accuracy_score": 8
}"""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500
        )

        result_text = response['choices'][0]['message']['content']
        print("\n✅ GPT-4 Vision Results:")
        print(result_text)

        return result_text

    except Exception as e:
        print(f"❌ GPT-4 Vision Error: {str(e)}")
        return None


def create_test_drawing():
    """Create a simple test drawing using PIL."""
    from PIL import Image, ImageDraw

    # Create a simple water cycle drawing
    img = Image.new('RGB', (800, 600), color='lightblue')
    draw = ImageDraw.Draw(img)

    # Draw sun
    draw.ellipse([650, 50, 750, 150], fill='yellow', outline='orange', width=3)

    # Draw cloud
    draw.ellipse([100, 100, 200, 150], fill='white', outline='gray', width=2)
    draw.ellipse([150, 90, 250, 140], fill='white', outline='gray', width=2)

    # Draw rain
    for x in range(120, 220, 20):
        draw.line([(x, 150), (x, 200)], fill='blue', width=2)

    # Draw water body
    draw.rectangle([50, 450, 750, 550], fill='lightblue', outline='blue', width=3)

    # Draw evaporation arrows (simple lines going up)
    for x in range(150, 650, 100):
        draw.line([(x, 450), (x, 300)], fill='red', width=2)
        # Arrow head
        draw.line([(x, 300), (x-10, 310)], fill='red', width=2)
        draw.line([(x, 300), (x+10, 310)], fill='red', width=2)

    img.save(TEST_IMAGE_PATH)
    print(f"✅ Created test drawing: {TEST_IMAGE_PATH}")
    return TEST_IMAGE_PATH


def compare_services():
    """Compare both services and provide recommendation."""

    print("=" * 80)
    print("🧪 Azure Computer Vision vs GPT-4 Vision Comparison")
    print("=" * 80)

    # Create test image
    image_path = create_test_drawing()

    # Test both services
    azure_result = test_azure_computer_vision(image_path)
    gpt4_result = test_gpt4_vision(image_path)

    print("\n" + "=" * 80)
    print("📊 RECOMMENDATION")
    print("=" * 80)

    print("""
    🎯 HYBRID APPROACH (Best Solution):

    1. PRIMARY: GPT-4 Vision
       ✅ Better for educational context
       ✅ Understands conceptual drawings
       ✅ Provides age-appropriate feedback
       ✅ Can identify topics and concepts
       ✅ More flexible interpretation

    2. SECONDARY: Azure Computer Vision
       ✅ Faster response time
       ✅ Better for object detection
       ✅ Good for color analysis
       ✅ Can validate GPT-4 results
       ✅ Lower cost per request

    💡 RECOMMENDED WORKFLOW:

    Stage 1 MVP:
    - Use GPT-4 Vision only for simplicity
    - Handles recognition + feedback in one call

    Stage 2 Production:
    - Azure CV for quick object detection (< 1s)
    - GPT-4V for detailed educational feedback (2-3s)
    - Azure CV can pre-filter/validate before GPT-4

    📈 Cost Comparison:
    - Azure CV: ~$1 per 1000 images
    - GPT-4V: ~$0.03 per image (with image tokens)

    For educational use with ~1000 drawings/day:
    - Azure CV only: $1/day = $30/month
    - GPT-4V only: $30/day = $900/month
    - Hybrid: $1 + $15/day = $480/month (Azure filters 50%)
    """)


if __name__ == "__main__":
    compare_services()
