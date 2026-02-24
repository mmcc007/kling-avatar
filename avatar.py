#!/usr/bin/env python3
"""
Talking head video pipeline:
  text  →  ElevenLabs TTS (cloned voice)  →  MP3
  image + MP3  →  fal.ai Kling Avatar v2  →  MP4

Usage:
    # Text-to-speech + avatar (full pipeline)
    python3 avatar.py --image pele.png --text "Hello, I am Pelé." --voice-id <id> --output pele.mp4

    # Use existing audio file (skip TTS)
    python3 avatar.py --image pele.png --audio speech.mp3 --output pele.mp4

    # With animation prompt
    python3 avatar.py --image pele.png --audio speech.mp3 --prompt "Speak with energy and passion" --output pele.mp4

Requirements:
    pip install fal-client elevenlabs requests

Env vars:
    FAL_KEY          - fal.ai API key
    ELEVENLABS_KEY   - ElevenLabs API key (only needed for TTS)
"""

import fal_client
import requests
import sys
import os
import argparse
import tempfile
from elevenlabs import ElevenLabs


def upload_to_fal(path: str) -> str:
    """Upload a local file to fal.ai storage and return its public URL."""
    print(f"  Uploading {os.path.basename(path)}...")
    url = fal_client.upload_file(path)
    print(f"  → {url}")
    return url


def text_to_speech(text: str, voice_id: str, output_path: str):
    """Generate speech audio from text using ElevenLabs."""
    api_key = os.environ.get("ELEVENLABS_KEY", "")
    if not api_key:
        print("Error: set ELEVENLABS_KEY environment variable")
        sys.exit(1)

    print(f"\n[TTS] Generating speech with ElevenLabs...")
    print(f"  Voice ID: {voice_id}")
    print(f"  Text: {text[:80]}{'...' if len(text) > 80 else ''}")

    client = ElevenLabs(api_key=api_key)
    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    with open(output_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)

    print(f"  Saved: {output_path}")


def generate_avatar(image_path: str, audio_path: str, output_path: str, prompt: str = "."):
    """Generate a talking head video using fal.ai Kling Avatar v2."""
    if not os.environ.get("FAL_KEY"):
        print("Error: set FAL_KEY environment variable")
        sys.exit(1)

    print(f"\n[Avatar] Generating talking head video...")

    image_url = image_path if image_path.startswith("http") else upload_to_fal(image_path)
    audio_url = audio_path if audio_path.startswith("http") else upload_to_fal(audio_path)

    print(f"  Prompt: {prompt}")
    print(f"  Model: fal-ai/kling-video/ai-avatar/v2/standard")
    print(f"  (Billing: ~$0.056/sec of output — this may take a few minutes)\n")

    def on_queue_update(update):
        if isinstance(update, fal_client.InProgress):
            for log in update.logs:
                print(f"  {log['message']}")

    result = fal_client.subscribe(
        "fal-ai/kling-video/ai-avatar/v2/standard",
        arguments={
            "image_url": image_url,
            "audio_url": audio_url,
            "prompt": prompt,
        },
        with_logs=True,
        on_queue_update=on_queue_update,
    )

    video_url = result["video"]["url"]
    duration = result.get("duration", "?")
    cost_estimate = round(float(duration) * 0.0562, 2) if duration != "?" else "?"
    print(f"\n  Duration: {duration}s  |  Estimated cost: ~${cost_estimate}")
    print(f"  Video URL: {video_url}")

    print(f"\n[Download] Saving to {output_path}...")
    resp = requests.get(video_url, timeout=300)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(resp.content)
    print(f"  Done: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate a talking head video from image + text or audio")
    parser.add_argument("--image", required=True, help="Portrait image path or URL (JPG/PNG)")
    parser.add_argument("--audio", help="Audio file path or URL (MP3/WAV) — skip TTS if provided")
    parser.add_argument("--text", help="Text to speak (requires --voice-id and ELEVENLABS_KEY)")
    default_voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "")
    parser.add_argument("--voice-id", default=default_voice_id, help="ElevenLabs voice ID for TTS (default: $ELEVENLABS_VOICE_ID)")
    parser.add_argument("--prompt", default=".", help="Animation style prompt (e.g. 'Speak with energy and passion')")
    parser.add_argument("--output", default="output.mp4", help="Output video path (default: output.mp4)")
    args = parser.parse_args()

    if not args.audio and not args.text:
        print("Error: provide either --audio <file> or --text <string> (with --voice-id)")
        sys.exit(1)

    if args.text and not args.voice_id:
        print("Error: --text requires --voice-id (or set ELEVENLABS_VOICE_ID in .env)")
        sys.exit(1)

    audio_path = args.audio
    tmp_audio = None

    if args.text:
        tmp_audio = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp_audio.close()
        text_to_speech(args.text, args.voice_id, tmp_audio.name)
        audio_path = tmp_audio.name

    try:
        generate_avatar(args.image, audio_path, args.output, prompt=args.prompt)
    finally:
        if tmp_audio and os.path.exists(tmp_audio.name):
            os.unlink(tmp_audio.name)

    print(f"\nAll done! → {args.output}")


if __name__ == "__main__":
    main()
