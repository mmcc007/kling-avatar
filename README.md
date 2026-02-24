# kling-avatar

Generate talking head videos from a portrait image using Kling AI Avatar v2 (via fal.ai) and ElevenLabs voice cloning.

## Pipeline

```
text  →  ElevenLabs TTS (cloned voice)  →  MP3
image + MP3  →  fal.ai Kling Avatar v2  →  MP4
```

Or skip TTS and bring your own audio:

```
image + audio  →  fal.ai Kling Avatar v2  →  MP4
```

## Setup

```bash
pip install fal-client elevenlabs requests
cp .env.example .env
# Fill in your API keys in .env
```

### API Keys

| Key | Where to get it |
|-----|----------------|
| `FAL_KEY` | [fal.ai/dashboard](https://fal.ai/dashboard) |
| `ELEVENLABS_KEY` | [elevenlabs.io](https://elevenlabs.io) → Profile → API Keys |
| `ELEVENLABS_VOICE_ID` | ElevenLabs → Voices → your cloned voice → Voice ID |

### .env

```
FAL_KEY=your_fal_key_here
ELEVENLABS_KEY=your_elevenlabs_key_here
ELEVENLABS_VOICE_ID=your_voice_id_here
```

## Usage

### Full pipeline (text → voice → video)

With `ELEVENLABS_VOICE_ID` set in `.env`, no need to pass `--voice-id`:

```bash
source .env
python3 avatar.py \
  --image pele.png \
  --text "Hello, I am Pelé. Football is the beautiful game." \
  --prompt "Speak with energy and passion" \
  --output pele.mp4
```

Or override the voice explicitly:

```bash
python3 avatar.py \
  --image pele.png \
  --text "Hello, I am Pelé." \
  --voice-id <other_voice_id> \
  --output pele.mp4
```

### Existing audio file (skip TTS)

```bash
source .env
python3 avatar.py \
  --image pele.png \
  --audio speech.mp3 \
  --output pele.mp4
```

### With animation prompt

The `--prompt` parameter guides the animation style (e.g. emotion, movement):

```bash
--prompt "Speak calmly and confidently"
--prompt "Energetic, expressive gestures"
```

### Trim audio first (save cost)

```bash
# Cut first 30 seconds
ffmpeg -ss 0 -t 30 -i input.mp3 clip.mp3

# Cut from 1:00 to 1:30
ffmpeg -ss 60 -t 30 -i input.mp3 clip.mp3
```

## Finding your ElevenLabs Voice ID

1. Go to [elevenlabs.io](https://elevenlabs.io) → Voices
2. Click your cloned voice
3. Copy the Voice ID from the URL or voice settings

## Pricing

| Service | Cost |
|---------|------|
| fal.ai Kling Avatar v2 | ~$0.056/sec of output |
| ElevenLabs TTS | Depends on plan (~free tier: 10k chars/month) |

**Examples:**
- 30 second video ≈ $1.70
- 1 minute video ≈ $3.37
- 4.5 minute video ≈ $15
