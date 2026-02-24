#!/usr/bin/env python3
"""
Clone a voice on ElevenLabs using one or more audio samples.

Prints the new voice ID on success — add it to your .env as ELEVENLABS_VOICE_ID.

Usage:
    python3 clone_voice.py --name "Pelé" --files sample1.mp3 sample2.mp3
    python3 clone_voice.py --name "Pelé" --files samples/*.mp3 --description "Brazilian footballer"

Requirements:
    pip install elevenlabs

Env vars:
    ELEVENLABS_KEY - ElevenLabs API key

Tips for best results:
    - Use at least 1 minute of audio (3-5 min recommended)
    - Single speaker only, no background music or noise
    - MP3 or WAV format
    - Varied speech (different sentences, not the same phrase repeated)
"""

import argparse
import os
import sys
from elevenlabs import ElevenLabs


def clone_voice(name: str, files: list[str], description: str = ""):
    api_key = os.environ.get("ELEVENLABS_KEY", "")
    if not api_key:
        print("Error: set ELEVENLABS_KEY environment variable")
        sys.exit(1)

    for f in files:
        if not os.path.exists(f):
            print(f"Error: file not found: {f}")
            sys.exit(1)

    print(f"Cloning voice '{name}' from {len(files)} file(s):")
    for f in files:
        size_mb = os.path.getsize(f) / 1024 / 1024
        print(f"  {f} ({size_mb:.1f} MB)")

    client = ElevenLabs(api_key=api_key)
    file_handles = [open(f, "rb") for f in files]
    try:
        voice = client.voices.ivc.create(
            name=name,
            files=file_handles,
            description=description or None,
        )
    finally:
        for fh in file_handles:
            fh.close()

    voice_id = voice.voice_id
    print(f"\nVoice cloned successfully!")
    print(f"  Name:     {name}")
    print(f"  Voice ID: {voice_id}")
    print(f"\nAdd to your .env:")
    print(f"  ELEVENLABS_VOICE_ID={voice_id}")


def main():
    parser = argparse.ArgumentParser(description="Clone a voice on ElevenLabs")
    parser.add_argument("--name", required=True, help="Name for the cloned voice")
    parser.add_argument("--files", required=True, nargs="+", help="Audio file(s) to clone from (MP3/WAV)")
    parser.add_argument("--description", default="", help="Optional description of the voice")
    args = parser.parse_args()

    clone_voice(args.name, args.files, args.description)


if __name__ == "__main__":
    main()
