# Video Captioning Script

This script adds captions to raw video footage using automatic transcription.

## Overview

`preedit_and_post.py` processes videos by:
1. **Extracting audio** from the video file
2. **Transcribing** the audio using WhisperX (OpenAI Whisper)
3. **Generating SRT** subtitle file with timestamps
4. **Burning captions** into the video using FFmpeg

## Prerequisites

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements-ml.txt
   ```

2. **FFmpeg** (already installed via WinGet on your system)

## Usage

### Basic Usage
```bash
python scripts/preedit_and_post.py --input raw_footage.mp4 --output edited_with_captions.mp4
```

### Available Options

- `--input`, `-i`: Input video file (required)
- `--output`, `-o`: Output video file (required)
- `--model`: WhisperX model to use (default: `large-v3`)
  - Options: `tiny`, `base`, `small`, `medium`, `large`, `large-v2`, `large-v3`
  - Smaller models are faster but less accurate
  - Larger models are more accurate but slower
- `--style`: Caption style (default: `default`)
  - Options: `default`, `modern`, `bold`, `minimal`
- `--keep-srt`: Keep the SRT subtitle file after processing

### Examples

**Add captions with default style:**
```bash
python scripts/preedit_and_post.py -i video.mp4 -o captioned.mp4
```

**Add captions with modern bold style:**
```bash
python scripts/preedit_and_post.py -i video.mp4 -o captioned.mp4 --style modern
```

**Use faster model for quick preview:**
```bash
python scripts/preedit_and_post.py -i video.mp4 -o captioned.mp4 --model small
```

**Keep the SRT file for editing:**
```bash
python scripts/preedit_and_post.py -i video.mp4 -o captioned.mp4 --keep-srt
```

## Caption Styles

- **default**: Standard white text with black background outline
- **modern**: Bold Arial Black, larger text, enhanced outline
- **bold**: Extra bold with cyan highlight color
- **minimal**: Clean look with minimal styling

## Processing Time

- **Model Sizes** (affects transcription speed):
  - `tiny`: ~5-10x faster than large-v3
  - `small`: ~3-5x faster
  - `large-v3`: Most accurate (~2-3x slower)

- **Video Length**: Expect ~1-2 seconds of processing per second of video (with large-v3)

## Troubleshooting

### FFmpeg not found
If you get "FFmpeg not found" error:
- Install FFmpeg via WinGet: `winget install Gyan.FFmpeg`
- Or manually place ffmpeg.exe in the `tools/` directory

### CUDA not available
The script automatically uses CPU if CUDA is not available. Processing will be slower but will still work.

### Poor transcription quality
- Use `large-v3` model for best accuracy
- Ensure the audio is clear and not too quiet
- For noisy audio, consider preprocessing with audio cleaning tools

## Output Files

By default, the script creates:
- `[output].mp4` - Video with burned-in captions

If `--keep-srt` is used, you'll also get:
- `[output].srt` - SRT subtitle file that can be edited

## Editing Captions

If you keep the SRT file, you can:
1. Manually edit it with any text editor
2. Fix any transcription mistakes
3. Re-run the script to burn updated captions

Example SRT format:
```
1
00:00:00,000 --> 00:00:03,500
Hello, welcome to my video

2
00:00:03,500 --> 00:00:07,000
This is another subtitle line
```

## Notes

- The original video is never modified
- Audio stream is copied, not re-encoded
- Video quality is preserved (CRF 23)
- Processing can take several minutes for longer videos

