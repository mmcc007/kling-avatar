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

The `--prompt` parameter guides the animation style. Prompts are stored in `prompts.yaml` for reuse.

**Talking** (use when avatar is speaking):
```bash
source .env
python3 avatar.py \
  --image pele.png \
  --audio speech.mp3 \
  --prompt "Confident, warm, and relaxed demeanor. Occasional natural hand gestures to emphasise speech — right hand rises to chest height then returns to hip. Subtle weight shift side to side. Soccer ball remains still under right foot throughout. Engaged eye contact with camera. Expressive micro-expressions matching audio tone. Static full-body portrait shot, black background, soft warm light." \
  --output pele_talking.mp4
```

**Listening** (use when avatar is listening/nodding):
```bash
source .env
python3 avatar.py \
  --image pele.png \
  --audio ambient_or_silence.mp3 \
  --prompt "Attentive and thoughtful expression, mouth closed. Slow nodding twice as if absorbing what is being said. Faint warm smile forms gradually. Left hand shifts slightly then settles at hip. Subtle forward lean of interest then eases back. Soccer ball stays still under right foot. Eyes focused and calm, occasional slow blink. Static full-body portrait shot, black background, soft warm light." \
  --output pele_listening.mp4
```

These prompts are designed for interactive avatar training videos where you need both talking and listening clips. See `prompts.yaml` for the full library.

### Trim audio first (save cost)

```bash
# Cut first 30 seconds
ffmpeg -ss 0 -t 30 -i input.mp3 clip.mp3

# Cut from 1:00 to 1:30
ffmpeg -ss 60 -t 30 -i input.mp3 clip.mp3
```

## Cloning a Voice with ElevenLabs

1. Go to [elevenlabs.io](https://elevenlabs.io) → **Voices** → **Add Voice** → **Voice Clone**
2. Choose **Instant Voice Clone**
3. Upload your audio samples:
   - Minimum: 1 minute of clean speech
   - Recommended: 3–5 minutes for better quality
   - Must be a single speaker, minimal background noise/music
   - MP3 or WAV format
4. Name your voice and click **Create**
5. Copy the **Voice ID** (see below) and add it to your `.env` as `ELEVENLABS_VOICE_ID`

## Finding your ElevenLabs Voice ID

Option 1 — via script:
```bash
source .env && python3 -c "
from elevenlabs import ElevenLabs
client = ElevenLabs(api_key='$ELEVENLABS_KEY')
for v in client.voices.get_all().voices:
    print(v.voice_id, v.name)
"
```

Option 2 — via dashboard:
1. Go to [elevenlabs.io](https://elevenlabs.io) → Voices
2. Click your cloned voice
3. Copy the Voice ID from the voice settings panel

## Pricing

| Service | Cost |
|---------|------|
| fal.ai Kling Avatar v2 | ~$0.056/sec of output |
| ElevenLabs TTS | Depends on plan (~free tier: 10k chars/month) |

**Examples:**
- 30 second video ≈ $1.70
- 1 minute video ≈ $3.37
- 4.5 minute video ≈ $15
