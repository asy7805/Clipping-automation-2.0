# Captions.ai Integration Guide

## Overview

The AscensionClips API now includes integration with [Captions.ai](https://www.captions.ai) for professional-grade AI-powered video captioning, translation, and AI video generation.

## Features

### 1. **Automatic Caption Generation** 
Add AI-generated captions to any video with word-level timing and styling.

### 2. **AI Video Translation**
Translate videos to 40+ languages with voice cloning to maintain the original speaker's voice characteristics.

### 3. **AI Video Creation**
Generate talking head videos from text scripts using AI avatars and voices.

---

## Setup

### 1. Get Your API Key

1. Sign up at [captions.ai](https://www.captions.ai)
2. Navigate to API settings in your account
3. Generate a new API key

### 2. Configure Environment

Add to your `.env` file or PowerShell startup script:

```bash
CAPTIONS_AI_API_KEY=your_api_key_here
```

### 3. Verify Installation

Start the API and check the health endpoint:

```bash
GET http://localhost:8000/api/v1/captions/health
```

Expected response when configured:
```json
{
  "status": "healthy",
  "service": "Captions.ai",
  "available": true
}
```

---

## API Endpoints

All endpoints are prefixed with `/api/v1/captions`

### 1. Add Captions to Video

**Endpoint:** `POST /api/v1/captions/add`

**Request Body:**
```json
{
  "video_url": "https://your-video-url.com/video.mp4",
  "language": "en",
  "style": "default"
}
```

**Parameters:**
- `video_url` (required): URL of the video to caption
- `language` (optional): Language code (default: "en")
  - Supported: en, es, fr, de, it, pt, ru, zh, ja, ko, ar, hi
- `style` (optional): Caption style preference (default: "default")

**Response:**
```json
{
  "success": true,
  "job_id": "caption-job-abc123",
  "status": "processing",
  "message": "Caption job started successfully"
}
```

**Example using curl:**
```bash
curl -X POST http://localhost:8000/api/v1/captions/add \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://mpcvgknfjcxsalbtxabk.supabase.co/storage/v1/object/public/raw/tenz/clip_123.mp4",
    "language": "en",
    "style": "modern"
  }'
```

---

### 2. Translate Video

**Endpoint:** `POST /api/v1/captions/translate`

**Request Body:**
```json
{
  "video_url": "https://your-video-url.com/video.mp4",
  "source_language": "en",
  "target_language": "es",
  "voice_clone": true
}
```

**Parameters:**
- `video_url` (required): URL of the video to translate
- `source_language` (optional): Original language code (default: "en")
- `target_language` (required): Target language code
- `voice_clone` (optional): Clone the original voice (default: true)

**Response:**
```json
{
  "success": true,
  "job_id": "translate-job-xyz789",
  "status": "processing",
  "message": "Translation from en to es started"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/captions/translate \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://example.com/clip.mp4",
    "source_language": "en",
    "target_language": "es",
    "voice_clone": true
  }'
```

---

### 3. Create AI Video

**Endpoint:** `POST /api/v1/captions/ai-video`

**Request Body:**
```json
{
  "script": "Welcome to my channel! Today we're going to talk about...",
  "avatar": "default",
  "voice": "default"
}
```

**Parameters:**
- `script` (required): Text script for the video
- `avatar` (optional): Avatar/character to use (default: "default")
- `voice` (optional): Voice profile to use (default: "default")

**Response:**
```json
{
  "success": true,
  "job_id": "ai-video-job-def456",
  "status": "processing",
  "message": "AI video generation started"
}
```

---

### 4. Check Job Status

**Endpoint:** `GET /api/v1/captions/job/{job_id}`

**Response:**
```json
{
  "job_id": "caption-job-abc123",
  "status": "completed",
  "progress": 100,
  "result_url": "https://captions.ai/results/video-captioned.mp4",
  "error": null
}
```

**Status Values:**
- `queued`: Job is waiting to be processed
- `processing`: Job is currently being processed
- `completed`: Job finished successfully
- `failed`: Job failed (see error field)

**Example:**
```bash
curl http://localhost:8000/api/v1/captions/job/caption-job-abc123
```

---

### 5. Get Supported Languages

**Endpoint:** `GET /api/v1/captions/languages`

**Response:**
```json
{
  "languages": [
    {"code": "en", "name": "English"},
    {"code": "es", "name": "Spanish"},
    {"code": "fr", "name": "French"},
    ...
  ]
}
```

---

### 6. Health Check

**Endpoint:** `GET /api/v1/captions/health`

**Response (healthy):**
```json
{
  "status": "healthy",
  "service": "Captions.ai",
  "available": true
}
```

**Response (not configured):**
```json
{
  "status": "unavailable",
  "message": "Captions.ai client not initialized. Check API key."
}
```

---

## Workflow Examples

### Example 1: Caption a Twitch Clip

1. **Capture a clip** from a live stream (using existing monitors)
2. **Get the clip URL** from Supabase storage
3. **Add captions** using the API:

```bash
curl -X POST http://localhost:8000/api/v1/captions/add \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://mpcvgknfjcxsalbtxabk.supabase.co/storage/v1/object/public/raw/shroud/clip_20241110_123456.mp4",
    "language": "en"
  }'
```

4. **Check status** periodically:

```bash
curl http://localhost:8000/api/v1/captions/job/caption-job-abc123
```

5. **Download the result** when status is "completed"

---

### Example 2: Multi-Language Content Creation

1. **Capture original clip** in English
2. **Translate to Spanish** with voice cloning:

```bash
curl -X POST http://localhost:8000/api/v1/captions/translate \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://example.com/original-en.mp4",
    "source_language": "en",
    "target_language": "es",
    "voice_clone": true
  }'
```

3. **Translate to French**:

```bash
curl -X POST http://localhost:8000/api/v1/captions/translate \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://example.com/original-en.mp4",
    "source_language": "en",
    "target_language": "fr",
    "voice_clone": true
  }'
```

Now you have one clip in 3 languages!

---

## Integration with Existing Workflows

### With Live Monitor

You can create a workflow that automatically captions clips as they're captured:

1. Monitor captures interesting moments
2. Clips are uploaded to Supabase
3. A webhook or background task triggers captioning
4. Captioned videos are stored separately

### With Social Media Publishing

1. Capture and caption a clip
2. Use the captioned version for posting to TikTok/YouTube
3. Better engagement with professional captions

---

## Error Handling

### API Key Not Configured

If the `CAPTIONS_AI_API_KEY` is not set, all endpoints will return:

```json
{
  "detail": "Captions.ai service is not available. Check API key configuration."
}
```

**Status Code:** 503 Service Unavailable

### Invalid Video URL

If the video URL is not accessible:

```json
{
  "detail": "Failed to process video: Unable to access video URL"
}
```

**Status Code:** 500 Internal Server Error

### Rate Limiting

Captions.ai may have rate limits. Check their documentation for current limits.

---

## Pricing

Captions.ai is a paid service. Check [captions.ai/pricing](https://www.captions.ai/pricing) for current rates.

**Typical costs:**
- Caption generation: ~$0.10-0.30 per minute of video
- Translation: ~$0.50-1.00 per minute of video
- AI video creation: Varies by length and complexity

---

## Tips & Best Practices

1. **Video Quality**: Higher quality source videos produce better caption accuracy
2. **Audio Clarity**: Clear audio with minimal background noise works best
3. **Video Length**: Shorter videos (30-90 seconds) process faster
4. **Caching Results**: Store job IDs to avoid re-processing the same video
5. **Batch Processing**: Process multiple clips in parallel for efficiency

---

## Troubleshooting

### "Service unavailable" error
- Check that `CAPTIONS_AI_API_KEY` is set in your environment
- Verify the API key is valid at captions.ai
- Restart the API server after setting the key

### "Job failed" status
- Check the `error` field in the job status response
- Verify the video URL is publicly accessible
- Ensure the video format is supported (MP4, MOV, etc.)

### Slow processing
- Large videos take longer to process
- Check captions.ai service status
- Consider splitting long videos into smaller chunks

---

## API Documentation

For interactive API testing, visit:
- **Swagger UI**: http://localhost:8000/docs
- Look for the "captions" tag to see all endpoints

---

## Support

- **Captions.ai API Docs**: https://docs.captions.ai
- **Project Issues**: Create an issue in the GitHub repository
- **Feature Requests**: Open a GitHub issue with the "enhancement" label

---

## Next Steps

1. ✅ Get your Captions.ai API key
2. ✅ Add it to your environment configuration
3. ✅ Test the health endpoint
4. 🎬 Start captioning your Twitch clips!
5. 🌍 Experiment with multi-language translations
6. 🤖 Try creating AI-generated videos

Happy captioning! 🎬✨

