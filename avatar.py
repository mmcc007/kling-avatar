#!/usr/bin/env python3
"""
Kling AI Avatar via fal.ai

Takes a portrait image + audio file and generates a talking head video
using the Kling AI Avatar v2 model on fal.ai.

Usage:
    python3 avatar.py <image_path> <audio_path> [output.mp4]

Requirements:
    pip install fal-client requests

Auth:
    export FAL_KEY="your_fal_api_key"

Pricing:
    ~$0.056/second of output video (e.g. 30s clip ≈ $1.70, 4.5min ≈ $15)

Tip:
    Trim your audio first with ffmpeg if you only want a short clip:
    ffmpeg -ss 0 -t 30 -i input.mp3 clip.mp3
"""

import fal_client
import requests
import sys
import os

FAL_KEY = os.environ.get("FAL_KEY", "")
AVATAR_ENDPOINT = "fal-ai/kling-video/ai-avatar/v2/standard"


def upload_file(path: str) -> str:
    """Upload a local file to fal.ai storage and return its public URL."""
    print(f"  Uploading {os.path.basename(path)} to fal.ai storage...")
    url = fal_client.upload_file(path)
    print(f"  URL: {url}")
    return url


def generate_avatar(image_path: str, audio_path: str, output_path: str):
    if not FAL_KEY:
        print("Error: set FAL_KEY environment variable")
        sys.exit(1)

    os.environ["FAL_KEY"] = FAL_KEY

    # Upload local files to fal storage (or pass through if already URLs)
    image_url = image_path if image_path.startswith("http") else upload_file(image_path)
    audio_url = audio_path if audio_path.startswith("http") else upload_file(audio_path)

    print(f"\nGenerating avatar video...")
    print(f"  Image: {image_url}")
    print(f"  Audio: {audio_url}")
    print(f"  Model: {AVATAR_ENDPOINT}")
    print(f"  (This takes a few minutes — billing is per second of output)\n")

    def on_queue_update(update):
        if isinstance(update, fal_client.InProgress):
            for log in update.logs:
                print(f"  {log['message']}")

    result = fal_client.subscribe(
        AVATAR_ENDPOINT,
        arguments={
            "image_url": image_url,
            "audio_url": audio_url,
            "prompt": ".",
        },
        with_logs=True,
        on_queue_update=on_queue_update,
    )

    video_url = result["video"]["url"]
    duration = result.get("duration", "?")
    print(f"\nDone! Duration: {duration}s")
    print(f"Video URL: {video_url}")

    print(f"Downloading to {output_path}...")
    resp = requests.get(video_url, timeout=300)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(resp.content)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 avatar.py <image_path> <audio_path> [output.mp4]")
        print("")
        print("Examples:")
        print("  python3 avatar.py pele.png speech.mp3 pele_avatar.mp4")
        print("  python3 avatar.py pele.png speech.mp3  (saves to output.mp4)")
        sys.exit(1)

    image = sys.argv[1]
    audio = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) > 3 else "output.mp4"

    generate_avatar(image, audio, output)
