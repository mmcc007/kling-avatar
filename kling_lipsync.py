#!/usr/bin/env python3
"""
Kling AI Lip Sync pipeline.

Step 1: Generate a video from an image (image-to-video)
Step 2: Run lip sync on that video with an audio file

Usage:
    python3 kling_lipsync.py <image_path> <audio_url_or_path> [output.mp4]

Requirements:
    pip install pyjwt requests

Auth:
    Set KLING_ACCESS_KEY and KLING_SECRET_KEY env vars, or edit the script.
"""

import jwt
import time
import requests
import json
import sys
import os

ACCESS_KEY = os.environ.get("KLING_ACCESS_KEY", "")
SECRET_KEY = os.environ.get("KLING_SECRET_KEY", "")

BASE_URL = "https://api-singapore.klingai.com"


def get_token() -> str:
    now = int(time.time())
    payload = {
        "iss": ACCESS_KEY,
        "exp": now + 1800,
        "nbf": now - 5,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256", headers={"alg": "HS256", "typ": "JWT"})


def auth_headers() -> dict:
    return {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json",
    }


def poll(url: str, interval: int = 5, max_attempts: int = 120) -> dict:
    for attempt in range(max_attempts):
        time.sleep(interval)
        resp = requests.get(url, headers=auth_headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()["data"]
        status = data["task_status"]
        print(f"  [{attempt + 1}/{max_attempts}] Status: {status}")
        if status == "succeed":
            return data
        if status == "failed":
            raise RuntimeError(f"Task failed: {data.get('task_status_msg', 'unknown error')}")
    raise RuntimeError("Timed out waiting for task")


def image_to_video(image_path: str, model: str = "kling-v1-6") -> str:
    """Upload image and generate a short video. Returns the video URL."""
    print(f"\n[Step 1] Generating video from image: {image_path}")

    # image_path can be a public URL or a local file path
    # If local, host it somewhere publicly accessible first (e.g. upload to tmpfiles.org)
    if image_path.startswith("http"):
        image_url = image_path
    else:
        print("  Uploading image to tmpfiles.org for public URL...")
        with open(image_path, "rb") as f:
            upload_resp = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, timeout=30)
        upload_resp.raise_for_status()
        # tmpfiles.org returns https://tmpfiles.org/XXXXXX/filename — convert to direct URL
        page_url = upload_resp.json()["data"]["url"]
        image_url = page_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
        print(f"  Image URL: {image_url}")

    payload = {
        "model_name": model,
        "image": image_url,
        "duration": "5",
        "mode": "std",
        "cfg_scale": 0.5,
    }

    resp = requests.post(
        f"{BASE_URL}/v1/videos/image2video",
        headers=auth_headers(),
        json=payload,
        timeout=30,
    )
    print(f"  image2video response: {resp.status_code} {resp.text[:300]}")
    resp.raise_for_status()

    task_id = resp.json()["data"]["task_id"]
    print(f"  Task ID: {task_id}")

    result = poll(f"{BASE_URL}/v1/videos/image2video/{task_id}")
    video_url = result["task_result"]["videos"][0]["url"]
    video_id = result["task_result"]["videos"][0]["id"]
    print(f"  Video ready: {video_url}")
    return video_url, video_id


def lip_sync(video_url: str, audio_path: str, model: str = "kling-v2-1") -> str:
    """Run lip sync on a video with an audio file. Returns the output video URL."""
    print(f"\n[Step 2] Running lip sync with audio: {audio_path}")

    payload = {
        "input": {
            "model_name": model,
            "mode": "audio2video",
            "video_url": video_url,
        }
    }

    if audio_path.startswith("http"):
        payload["input"]["audio_type"] = "url"
        payload["input"]["audio_url"] = audio_path
    else:
        print("  Uploading audio to tmpfiles.org for public URL...")
        with open(audio_path, "rb") as f:
            upload_resp = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, timeout=60)
        upload_resp.raise_for_status()
        page_url = upload_resp.json()["data"]["url"]
        audio_url = page_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
        print(f"  Audio URL: {audio_url}")
        payload["input"]["audio_type"] = "url"
        payload["input"]["audio_url"] = audio_url

    resp = requests.post(
        f"{BASE_URL}/v1/videos/lip-sync",
        headers=auth_headers(),
        json=payload,
        timeout=30,
    )
    print(f"  lip-sync response: {resp.status_code} {resp.text[:300]}")
    resp.raise_for_status()

    task_id = resp.json()["data"]["task_id"]
    print(f"  Task ID: {task_id}")

    result = poll(f"{BASE_URL}/v1/videos/lip-sync/{task_id}", interval=5, max_attempts=120)
    video_url = result["task_result"]["videos"][0]["url"]
    print(f"  Lip sync video ready: {video_url}")
    return video_url


def download(url: str, output_path: str):
    print(f"\n[Step 3] Downloading to {output_path}...")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(resp.content)
    print(f"  Saved: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 kling_lipsync.py <image_path> <audio_path> [output.mp4]")
        sys.exit(1)

    if not ACCESS_KEY or not SECRET_KEY:
        print("Error: Set KLING_ACCESS_KEY and KLING_SECRET_KEY environment variables")
        sys.exit(1)

    image_path = sys.argv[1]
    audio_path = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else "output.mp4"

    video_url, video_id = image_to_video(image_path)
    lip_sync_url = lip_sync(video_url, audio_path)
    download(lip_sync_url, output_path)

    print(f"\nDone! Output saved to: {output_path}")
