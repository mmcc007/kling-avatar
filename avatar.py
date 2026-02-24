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

    # Skip confirmation prompt
    python3 avatar.py --image pele.png --audio speech.mp3 --yes --output pele.mp4

Requirements:
    pip install fal-client elevenlabs requests mutagen

Env vars:
    FAL_KEY          - fal.ai API key
    ELEVENLABS_KEY   - ElevenLabs API key (only needed for TTS)
    ELEVENLABS_VOICE_ID - default ElevenLabs voice ID
"""

import fal_client
import requests
import sys
import os
import shutil
import argparse
import tempfile
import signal
from elevenlabs import ElevenLabs

PRICE_PER_SECOND = 0.0562  # fal.ai Kling Avatar v2 standard


def get_audio_duration(path: str) -> float:
    """Return duration in seconds of an audio file."""
    try:
        from mutagen.mp3 import MP3
        from mutagen import File as MutagenFile
        audio = MutagenFile(path)
        return audio.info.length if audio else 0.0
    except Exception:
        # Fallback: use ffprobe
        import subprocess
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True
        )
        return float(result.stdout.strip()) if result.stdout.strip() else 0.0


def upload_to_fal(path: str) -> str:
    """Upload a local file to fal.ai storage and return its public URL."""
    print(f"  Uploading {os.path.basename(path)}...")
    # fal.ai rejects URLs with non-ASCII characters — copy to a safe temp path
    filename = os.path.basename(path)
    if not filename.isascii():
        ext = os.path.splitext(filename)[1]
        tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        tmp.close()
        shutil.copy2(path, tmp.name)
        upload_path = tmp.name
    else:
        upload_path = path
        tmp = None
    try:
        url = fal_client.upload_file(upload_path)
    finally:
        if tmp and os.path.exists(tmp.name):
            os.unlink(tmp.name)
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


def confirm_cost(audio_path: str, yes: bool = False):
    """Show cost estimate and ask for confirmation before submitting."""
    duration = get_audio_duration(audio_path)
    cost = round(duration * PRICE_PER_SECOND, 2)
    mins = int(duration // 60)
    secs = int(duration % 60)

    print(f"\n  Audio duration : {mins}m {secs}s ({duration:.1f}s)")
    print(f"  Estimated cost : ~${cost:.2f} USD")

    if yes:
        return

    answer = input("\n  Proceed? [y/N] ").strip().lower()
    if answer != "y":
        print("  Cancelled.")
        sys.exit(0)


def generate_avatar(image_path: str, audio_path: str, output_path: str, prompt: str = ".", yes: bool = False):
    """Generate a talking head video using fal.ai Kling Avatar v2."""
    if not os.environ.get("FAL_KEY"):
        print("Error: set FAL_KEY environment variable")
        sys.exit(1)

    print(f"\n[Avatar] Preparing job...")

    image_url = image_path if image_path.startswith("http") else upload_to_fal(image_path)
    audio_url = audio_path if audio_path.startswith("http") else upload_to_fal(audio_path)

    confirm_cost(audio_path if not audio_path.startswith("http") else audio_path, yes=yes)

    print(f"\n  Prompt : {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
    print(f"  Model  : fal-ai/kling-video/ai-avatar/v2/standard")
    print(f"  Output : {output_path}")
    print(f"\n  Submitting... (Ctrl+C to cancel)\n")

    request_id = None

    def handle_sigint(sig, frame):
        if request_id:
            print(f"\n\n  Cancelling job {request_id}...")
            try:
                fal_client.cancel("fal-ai/kling-video/ai-avatar/v2/standard", request_id)
                print("  Job cancelled.")
            except Exception as e:
                print(f"  Cancel failed: {e}")
        sys.exit(1)

    signal.signal(signal.SIGINT, handle_sigint)

    def on_queue_update(update):
        nonlocal request_id
        if hasattr(update, "request_id"):
            request_id = update.request_id
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

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    video_url = result["video"]["url"]
    duration = result.get("duration", "?")
    actual_cost = round(float(duration) * PRICE_PER_SECOND, 2) if duration != "?" else "?"
    print(f"\n  Duration : {duration}s  |  Actual cost : ~${actual_cost}")
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
    parser.add_argument("--yes", "-y", action="store_true", help="Skip cost confirmation prompt")
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
        generate_avatar(args.image, audio_path, args.output, prompt=args.prompt, yes=args.yes)
    finally:
        if tmp_audio and os.path.exists(tmp_audio.name):
            os.unlink(tmp_audio.name)

    print(f"\nAll done! → {args.output}")


if __name__ == "__main__":
    main()
