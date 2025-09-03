# Clipping Automation 2.0 API Guide

## Overview

The Clipping Automation API provides REST endpoints for managing clips, streams, and analytics. It's built with FastAPI and integrates with your existing Supabase database and ML models.

## Quick Start

### 1. Install Dependencies

```bash
# Activate your core environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install new API dependencies
pip install -r requirements.txt
```

### 2. Start the API Server

```bash
# From the project root
python scripts/start_api.py
```

The API will be available at:
- **API Base URL**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc

## API Endpoints

### Health Check
- `GET /api/v1/health` - Basic health check
- `GET /api/v1/health/detailed` - Detailed health with service status

### Clips
- `POST /api/v1/clips/predict` - Predict if transcript is clip-worthy
- `GET /api/v1/clips` - List clips with filtering
- `GET /api/v1/clips/{clip_id}` - Get specific clip
- `POST /api/v1/clips` - Create new clip

### Analytics
- `GET /api/v1/analytics/summary` - Get analytics summary
- `GET /api/v1/analytics/performance` - Get model performance metrics
- `GET /api/v1/analytics/channels` - Get channel analytics
- `GET /api/v1/analytics/trends` - Get trending data

### Streams
- `GET /api/v1/streams` - List streams with filtering
- `GET /api/v1/streams/{stream_id}` - Get specific stream
- `POST /api/v1/streams` - Create new stream
- `GET /api/v1/streams/live` - Get live streams
- `GET /api/v1/streams/{stream_id}/clips` - Get clips for stream

## Example Usage

### Predict Clip Worthiness

```bash
curl -X POST "http://localhost:8000/api/v1/clips/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "transcript": "This is an amazing moment that everyone should see!",
    "model_version": "latest"
  }'
```

### Get Analytics Summary

```bash
curl "http://localhost:8000/api/v1/analytics/summary?days=7"
```

### Create a New Clip

```bash
curl -X POST "http://localhost:8000/api/v1/clips" \
  -H "Content-Type: application/json" \
  -d '{
    "transcript": "Check out this incredible play!",
    "channel_name": "example_channel",
    "duration": 30.5
  }'
```

## Integration with Existing Code

The API integrates with your existing modules:

- **`predict.py`** - Uses `is_clip_worthy_by_model()` for predictions
- **`supabase_integration.py`** - Uses `SupabaseManager` for database operations
- **Environment Variables** - Uses your existing `.env` configuration

## Development

### Adding New Endpoints

1. Create a new router in `src/api/routers/`
2. Add Pydantic models for request/response validation
3. Include the router in `src/api/main.py`
4. Update this documentation

### Database Integration

The API currently uses placeholder responses. To integrate with your Supabase database:

1. Import your `SupabaseManager` class
2. Replace placeholder responses with actual database queries
3. Add proper error handling for database operations

### Authentication (Future)

For production use, consider adding:
- API key authentication
- JWT tokens
- Rate limiting
- CORS configuration for your frontend

## Environment Variables

The API uses your existing environment variables:
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_ANON_KEY` - Supabase anonymous key
- `SUPABASE_SERVICE_ROLE_KEY` - For privileged operations
- `OPENAI_API_KEY` - For AI features
- `TWITCH_CLIENT_ID` - Twitch API client ID
- `TWITCH_CLIENT_SECRET` - Twitch API client secret

## Production Deployment

For production deployment:

1. Set `reload=False` in the uvicorn configuration
2. Use a production ASGI server like Gunicorn
3. Configure proper CORS origins
4. Add authentication and rate limiting
5. Set up monitoring and logging

```bash
# Production example with Gunicorn
gunicorn src.api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```
