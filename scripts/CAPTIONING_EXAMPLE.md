# Captioning Example

Quick guide to add captions to your videos.

## Quick Start

### Test with the provided clip:
```bash
python scripts/preedit_and_post.py --input test_clip.mp4 --output test_clip_captioned.mp4
```

This will:
1. Transcribe the audio using WhisperX
2. Generate captions automatically
3. Burn the captions into the video

### Example with different styles:

**Modern bold style:**
```bash
python scripts/preedit_and_post.py --input test_clip.mp4 --output test_captioned_modern.mp4 --style modern
```

**Bold cyan style:**
```bash
python scripts/preedit_and_post.py --input test_clip.mp4 --output test_captioned_bold.mp4 --style bold
```

**Minimal clean style:**
```bash
python scripts/preedit_and_post.py --input test_clip.mp4 --output test_captioned_minimal.mp4 --style minimal
```

### Keep the SRT file for manual editing:
```bash
python scripts/preedit_and_post.py --input test_clip.mp4 --output test_captioned.mp4 --keep-srt
```

Then edit `test_captioned.srt` to fix any transcription mistakes.

## Processing Time

- **test_clip.mp4**: ~30 seconds to 2 minutes (depending on length)
- **5-minute video**: ~5-10 minutes
- **30-minute video**: ~30-60 minutes

## What to Expect

The script will show progress messages:
```
🎤 Extracting audio from video...
📥 Loading WhisperX model: large-v3
✅ Model loaded on cuda
🎤 Transcribing audio...
✅ Transcription complete
✅ SRT file created: test_clip_captioned.srt
🎬 Burning captions into video...
✅ Video with captions created: test_clip_captioned.mp4
✅ Complete! Video with captions created successfully.
```

## Tips

1. **First-time setup**: Install dependencies first:
   ```bash
   pip install -r requirements-ml.txt
   ```

2. **Faster transcription**: Use a smaller model:
   ```bash
   python scripts/preedit_and_post.py -i video.mp4 -o output.mp4 --model small
   ```

3. **Best accuracy**: Use the default `large-v3` model (slower but better)

4. **Edit captions**: Use `--keep-srt` to keep the SRT file, edit it, then manually re-run with your modified SRT

## Troubleshooting

**"FFmpeg not found" error:**
- FFmpeg is already installed in your `tools/` directory
- The script should find it automatically

**Out of memory:**
- Use a smaller model: `--model small`
- Or process shorter clips

**Poor transcription:**
- Ensure audio is clear and not too quiet
- Background noise will reduce accuracy
- Consider preprocessing the audio first

## Output

The output video will have captions burned-in (hardcoded). The original video is never modified.

Captions will appear at the bottom of the screen with:
- White text
- Black background/outline
- Automatic timing based on speech
- Professional formatting

