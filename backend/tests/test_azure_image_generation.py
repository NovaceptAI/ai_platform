#!/usr/bin/env python3
"""
Test script for Azure DALL-E 3 text-to-image generation.
This script demonstrates how to generate images from text prompts using Azure OpenAI's DALL-E 3.

Usage:
    python test_azure_image_generation.py

You can either:
1. Set the environment variables directly in this script (see below)
2. Or use system environment variables
"""

import os
import sys
import json
import time
from pathlib import Path

# ============================================================================
# CONFIGURATION - Set your Azure OpenAI credentials here
# ============================================================================
# Option 1: Set directly in script (uncomment and fill in your values)
AZURE_CREDENTIALS = {
    "AZURE_OPENAI_ENDPOINT": "https://scoolish-openai.openai.azure.com/",
    "AZURE_OPENAI_API_KEY": "66gxh1j4bZGbQ7RIyjOipoGM69TSsMw3EQ8fA0XD1JlgnTxn8gcCJQQJ99BCACYeBjFXJ3w3AAABACOGwOWK",
    "AZURE_OPENAI_IMAGE_DEPLOYMENT": "dall-e-3",
    "AZURE_OPENAI_IMAGE_API_VERSION": "2024-02-01",
}

# Apply credentials to environment (will override system env vars)
for key, value in AZURE_CREDENTIALS.items():
    if value:  # Only set if not empty
        os.environ[key] = value

# ============================================================================

# Add the backend directory to the path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.external.azure_image import azure_dalle_generate

# ============================================================================
# RATE LIMIT CONFIGURATION
# ============================================================================
DELAY_BETWEEN_REQUESTS = 15  # seconds (to avoid rate limits)
# Azure DALL-E 3 typical limits: 3-6 images per minute per deployment


def safe_generate_with_delay(prompt, size="1024x1024", style="vivid", quality="standard", n=1, delay=True):
    """
    Wrapper around azure_dalle_generate that handles rate limits and adds delays.
    """
    try:
        if delay:
            print(f"   [Waiting {DELAY_BETWEEN_REQUESTS}s to respect rate limits...]")
            time.sleep(DELAY_BETWEEN_REQUESTS)

        results = azure_dalle_generate(
            prompt=prompt,
            size=size,
            style=style,
            quality=quality,
            n=n
        )
        return results, None
    except Exception as e:
        if "429" in str(e) or "Too Many Requests" in str(e):
            return None, "RATE_LIMIT"
        return None, str(e)


def test_basic_generation():
    """Test basic image generation with a simple prompt."""
    print("\n" + "="*80)
    print("TEST 1: Basic Image Generation")
    print("="*80)

    prompt = "A serene mountain landscape at sunset with a crystal clear lake"
    print(f"\nPrompt: {prompt}")
    print(f"Size: 1024x1024")
    print(f"Style: vivid")
    print(f"Quality: standard")

    try:
        results = azure_dalle_generate(
            prompt=prompt,
            size="1024x1024",
            style="vivid",
            quality="standard",
            n=1
        )

        if results:
            print(f"\n✅ Success! Generated {len(results)} image(s)")
            for i, result in enumerate(results, 1):
                if result.get("url"):
                    print(f"\n  Image {i} URL: {result['url']}")
                elif result.get("b64_json"):
                    print(f"\n  Image {i}: Base64 encoded (length: {len(result['b64_json'])} chars)")
        else:
            print("\n❌ No images generated (check environment variables)")

    except Exception as e:
        if "429" in str(e) or "Too Many Requests" in str(e):
            print(f"\n⚠️  Rate Limit Error: {e}")
            print("   Azure DALL-E has rate limits. Please wait and try again.")
            print("   Typical limits: 3-6 images per minute per deployment")
        else:
            print(f"\n❌ Error: {e}")


def test_different_styles():
    """Test different art styles."""
    print("\n" + "="*80)
    print("TEST 2: Different Art Styles")
    print("="*80)

    base_prompt = "A futuristic city with flying cars"
    styles = ["vivid", "natural"]

    for style in styles:
        print(f"\n--- Testing style: {style} ---")
        print(f"Prompt: {base_prompt}")

        try:
            results = azure_dalle_generate(
                prompt=base_prompt,
                size="1024x1024",
                style=style,
                quality="standard",
                n=1
            )

            if results and results[0].get("url"):
                print(f"✅ Generated with {style} style")
                print(f"   URL: {results[0]['url']}")
            else:
                print(f"❌ Failed to generate with {style} style")

        except Exception as e:
            print(f"❌ Error with {style} style: {e}")


def test_different_sizes():
    """Test different image sizes."""
    print("\n" + "="*80)
    print("TEST 3: Different Image Sizes")
    print("="*80)
    print("\n⚠️  Note: This test will take ~45 seconds (3 sizes × 15s delay)")

    prompt = "A cute robot reading a book"
    # DALL-E 3 supports: 1024x1024, 1024x1792 (portrait), 1792x1024 (landscape)
    sizes = ["1024x1024", "1024x1792", "1792x1024"]

    for i, size in enumerate(sizes):
        print(f"\n--- Testing size: {size} ---")
        print(f"Prompt: {prompt}")

        results, error = safe_generate_with_delay(
            prompt=prompt,
            size=size,
            style="vivid",
            quality="standard",
            n=1,
            delay=(i > 0)  # Skip delay for first request
        )

        if error == "RATE_LIMIT":
            print(f"⚠️  Rate limit reached. Skipping remaining sizes.")
            print(f"   Please wait 60 seconds before running more tests.")
            break
        elif error:
            print(f"❌ Error with {size}: {error}")
        elif results and results[0].get("url"):
            print(f"✅ Generated {size} image")
            print(f"   URL: {results[0]['url']}")
        else:
            print(f"❌ Failed to generate {size} image")


def test_quality_settings():
    """Test different quality settings."""
    print("\n" + "="*80)
    print("TEST 4: Quality Settings")
    print("="*80)

    prompt = "A detailed painting of a medieval castle"
    qualities = ["standard", "hd"]

    for quality in qualities:
        print(f"\n--- Testing quality: {quality} ---")
        print(f"Prompt: {prompt}")

        try:
            results = azure_dalle_generate(
                prompt=prompt,
                size="1024x1024",
                style="vivid",
                quality=quality,
                n=1
            )

            if results and results[0].get("url"):
                print(f"✅ Generated with {quality} quality")
                print(f"   URL: {results[0]['url']}")
            else:
                print(f"❌ Failed to generate with {quality} quality")

        except Exception as e:
            print(f"❌ Error with {quality} quality: {e}")


def test_complex_prompt():
    """Test a complex, detailed prompt."""
    print("\n" + "="*80)
    print("TEST 5: Complex Detailed Prompt")
    print("="*80)

    prompt = """
    A whimsical illustration of a steampunk library floating in the clouds.
    The library has ornate brass gears, vintage bookshelves filled with glowing books,
    and large panoramic windows showing a vibrant sunset sky with hot air balloons.
    In the foreground, a young inventor with goggles is reading a map.
    Art style: digital painting with warm colors and soft lighting.
    """

    print(f"\nPrompt: {prompt.strip()}")

    try:
        results = azure_dalle_generate(
            prompt=prompt.strip(),
            size="1792x1024",  # Landscape for dramatic scene
            style="vivid",
            quality="hd",
            n=1
        )

        if results and results[0].get("url"):
            print(f"\n✅ Generated complex scene")
            print(f"   URL: {results[0]['url']}")
        else:
            print("\n❌ Failed to generate complex scene")

    except Exception as e:
        print(f"\n❌ Error: {e}")


def test_educational_content():
    """Test generating educational/learning content images."""
    print("\n" + "="*80)
    print("TEST 6: Educational Content Generation")
    print("="*80)

    educational_prompts = [
        "A simple diagram showing the water cycle with labels for evaporation, condensation, precipitation, and collection",
        "An illustration of the solar system with planets in order from the sun, labeled and sized proportionally",
        "A cross-section diagram of a plant cell showing nucleus, chloroplast, cell wall, and other organelles with labels",
    ]

    for i, prompt in enumerate(educational_prompts, 1):
        print(f"\n--- Educational Image {i} ---")
        print(f"Prompt: {prompt}")

        try:
            results = azure_dalle_generate(
                prompt=prompt,
                size="1024x1024",
                style="natural",  # Natural style often works better for educational content
                quality="standard",
                n=1
            )

            if results and results[0].get("url"):
                print(f"✅ Generated educational image")
                print(f"   URL: {results[0]['url']}")
            else:
                print(f"❌ Failed to generate educational image")

        except Exception as e:
            print(f"❌ Error: {e}")


def check_environment():
    """Check if required environment variables are set."""
    print("\n" + "="*80)
    print("ENVIRONMENT CHECK")
    print("="*80)

    required_vars = {
        "AZURE_OPENAI_ENDPOINT": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "AZURE_OPENAI_API_KEY": os.getenv("AZURE_OPENAI_API_KEY"),
    }

    optional_vars = {
        "AZURE_IMAGE_API_KEY": os.getenv("AZURE_IMAGE_API_KEY"),
        "AZURE_OPENAI_IMAGE_DEPLOYMENT": os.getenv("AZURE_OPENAI_IMAGE_DEPLOYMENT", "dall-e-3"),
        "AZURE_OPENAI_IMAGE_API_VERSION": os.getenv("AZURE_OPENAI_IMAGE_API_VERSION", "2024-02-01"),
    }

    print("\nRequired Variables:")
    all_set = True
    for var, value in required_vars.items():
        if value:
            # Show first 20 and last 4 characters for verification
            if len(value) > 24:
                masked = f"{value[:20]}...{value[-4:]}"
            else:
                masked = f"{'*' * (len(value)-4)}{value[-4:]}" if len(value) > 4 else "****"
            print(f"  ✅ {var}:")
            print(f"      Length: {len(value)} characters")
            print(f"      Value: {masked}")
        else:
            print(f"  ❌ {var}: NOT SET")
            all_set = False

    print("\nOptional Variables:")
    for var, value in optional_vars.items():
        if value:
            if "KEY" in var:
                if len(value) > 24:
                    masked = f"{value[:20]}...{value[-4:]}"
                else:
                    masked = f"{'*' * (len(value)-4)}{value[-4:]}" if len(value) > 4 else "****"
                print(f"  ✅ {var}:")
                print(f"      Length: {len(value)} characters")
                print(f"      Value: {masked}")
            else:
                print(f"  ✅ {var}: {value}")
        else:
            print(f"  ⚠️  {var}: Using default")

    print("\nFinal Configuration (what azure_image.py will use):")
    print(f"  Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT', 'NOT SET')}")
    print(f"  Deployment: {os.getenv('AZURE_OPENAI_IMAGE_DEPLOYMENT', 'dall-e-3')}")
    print(f"  API Version: {os.getenv('AZURE_OPENAI_IMAGE_API_VERSION', '2024-02-01')}")

    # Show which API key will be used (azure_image.py logic)
    api_key = os.getenv("AZURE_OPENAI_API_KEY", os.getenv("AZURE_IMAGE_API_KEY", ""))
    if api_key:
        key_source = "AZURE_OPENAI_API_KEY" if os.getenv("AZURE_OPENAI_API_KEY") else "AZURE_IMAGE_API_KEY"
        if len(api_key) > 24:
            masked = f"{api_key[:20]}...{api_key[-4:]}"
        else:
            masked = f"{'*' * (len(api_key)-4)}{api_key[-4:]}" if len(api_key) > 4 else "****"
        print(f"  API Key (from {key_source}):")
        print(f"      Length: {len(api_key)} characters")
        print(f"      Value: {masked}")
    else:
        print(f"  API Key: NOT SET")

    return all_set


def print_usage_info():
    """Print usage information about DALL-E 3 parameters."""
    print("\n" + "="*80)
    print("DALL-E 3 PARAMETER REFERENCE")
    print("="*80)

    info = """
    Size Options:
    - 1024x1024  : Square (default)
    - 1024x1792  : Portrait (vertical)
    - 1792x1024  : Landscape (horizontal)

    Style Options:
    - vivid      : Hyper-real, dramatic images (default)
    - natural    : More natural, less hyper-real images

    Quality Options:
    - standard   : Faster generation, lower cost
    - hd         : Finer details, higher quality, higher cost

    Number of Images (n):
    - Range: 1-6 images per request
    - Note: DALL-E 3 typically works best with n=1

    Prompt Tips:
    - Be specific and descriptive
    - Include art style, mood, lighting
    - Mention composition and perspective
    - DALL-E 3 is very good at understanding complex prompts
    - It can generate text in images (with varying accuracy)

    Cost Considerations:
    - Standard quality: Lower cost per image
    - HD quality: ~2x the cost of standard
    - Larger sizes (portrait/landscape): Same cost as square
    """

    print(info)


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("AZURE DALL-E 3 TEXT-TO-IMAGE GENERATION TEST SUITE")
    print("="*80)

    # Check environment
    if not check_environment():
        print("\n⚠️  Warning: Some required environment variables are not set.")
        print("   Tests may fail. Please set up your Azure OpenAI credentials.")

    # Print usage information
    print_usage_info()

    # Ask user which tests to run
    print("\n" + "="*80)
    print("SELECT TESTS TO RUN")
    print("="*80)
    print("\n⚠️  IMPORTANT: Azure DALL-E 3 Rate Limits")
    print("   - Typical limit: 3-6 images per minute per deployment")
    print("   - Tests include 15-second delays between requests")
    print("   - If you hit rate limits, wait 60 seconds before retrying")
    print("\n1. Basic Image Generation (single test, ~0s)")
    print("2. Different Art Styles (2 images, ~15s)")
    print("3. Different Image Sizes (3 images, ~30s)")
    print("4. Quality Settings (2 images, ~15s)")
    print("5. Complex Detailed Prompt (single test, ~0s)")
    print("6. Educational Content Generation (3 images, ~30s)")
    print("7. Run All Tests (⚠️  11+ images, ~2-3 minutes + may hit rate limits)")
    print("0. Exit")

    choice = input("\nEnter your choice (0-7): ").strip()

    test_functions = {
        "1": test_basic_generation,
        "2": test_different_styles,
        "3": test_different_sizes,
        "4": test_quality_settings,
        "5": test_complex_prompt,
        "6": test_educational_content,
    }

    if choice == "0":
        print("\nExiting...")
        return
    elif choice == "7":
        confirm = input("\n⚠️  This will run all tests and may use significant API credits. Continue? (yes/no): ")
        if confirm.lower() == "yes":
            for test_func in test_functions.values():
                test_func()
        else:
            print("\nTests cancelled.")
    elif choice in test_functions:
        test_functions[choice]()
    else:
        print("\n❌ Invalid choice. Please run the script again.")

    print("\n" + "="*80)
    print("TESTS COMPLETED")
    print("="*80)
    print("\nNote: Generated image URLs are temporary and will expire after some time.")
    print("Save any images you want to keep by downloading them from the URLs.")


if __name__ == "__main__":
    main()
