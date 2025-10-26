# Social Media Automation Setup Guide

This guide will help you set up the social media automation feature for TikTok and YouTube posting.

## Prerequisites

1. **TikTok Developer Account**
   - Go to [TikTok for Developers](https://developers.tiktok.com/)
   - Create an account and register your application
   - Get your Client Key and Client Secret

2. **YouTube/Google Cloud Console**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable YouTube Data API v3
   - Create OAuth 2.0 credentials
   - Get your Client ID and Client Secret

3. **Redis Server**
   - Install Redis locally or use a cloud service
   - Default connection: `redis://localhost:6379`

## Environment Setup

Add these variables to your `.env` file:

```bash
# Social Media API Keys
TIKTOK_CLIENT_KEY=your_tiktok_client_key
TIKTOK_CLIENT_SECRET=your_tiktok_client_secret
YOUTUBE_CLIENT_ID=your_youtube_client_id
YOUTUBE_CLIENT_SECRET=your_youtube_client_secret

# Background Job Processing
REDIS_URL=redis://localhost:6379

# Frontend URL for OAuth callbacks
FRONTEND_URL=http://localhost:8081
```

## Database Setup

Run the SQL schema in your Supabase SQL Editor:

```sql
-- Social Media Accounts Table
CREATE TABLE IF NOT EXISTS social_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    platform VARCHAR(20) NOT NULL CHECK (platform IN ('tiktok', 'youtube')),
    account_id VARCHAR(255) NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, platform, account_id)
);

-- Posting Queue Table
CREATE TABLE IF NOT EXISTS posting_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clip_id VARCHAR(255) NOT NULL,
    user_id UUID REFERENCES auth.users(id),
    social_account_id UUID REFERENCES social_accounts(id),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'posted', 'failed', 'cancelled')),
    scheduled_at TIMESTAMP,
    posted_at TIMESTAMP,
    post_url TEXT,
    caption TEXT,
    platform_specific_data JSONB,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_posting_queue_status ON posting_queue(status);
CREATE INDEX IF NOT EXISTS idx_posting_queue_scheduled ON posting_queue(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_posting_queue_user ON posting_queue(user_id);
CREATE INDEX IF NOT EXISTS idx_social_accounts_user ON social_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_social_accounts_platform ON social_accounts(platform);

-- Row Level Security (RLS) Policies
ALTER TABLE social_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE posting_queue ENABLE ROW LEVEL SECURITY;

-- Users can only see their own social accounts
CREATE POLICY "Users can view own social accounts" ON social_accounts
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own social accounts" ON social_accounts
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own social accounts" ON social_accounts
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own social accounts" ON social_accounts
    FOR DELETE USING (auth.uid() = user_id);

-- Users can only see their own posting queue
CREATE POLICY "Users can view own posting queue" ON posting_queue
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own posting queue" ON posting_queue
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own posting queue" ON posting_queue
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own posting queue" ON posting_queue
    FOR DELETE USING (auth.uid() = user_id);

-- Functions for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_social_accounts_updated_at 
    BEFORE UPDATE ON social_accounts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_posting_queue_updated_at 
    BEFORE UPDATE ON posting_queue 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## Installation

1. **Install Python Dependencies**
   ```bash
   cd /Users/aidanyap/Clipping-automation-2.0
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Install Redis** (if not already installed)
   ```bash
   # macOS
   brew install redis
   brew services start redis
   
   # Ubuntu/Debian
   sudo apt-get install redis-server
   sudo systemctl start redis
   ```

## Running the System

1. **Start Redis Server**
   ```bash
   redis-server
   ```

2. **Start Celery Worker** (in a separate terminal)
   ```bash
   cd /Users/aidanyap/Clipping-automation-2.0
   source .venv/bin/activate
   celery -A src.posting.celery_app worker --loglevel=info
   ```

3. **Start Celery Beat** (in another terminal for scheduled tasks)
   ```bash
   cd /Users/aidanyap/Clipping-automation-2.0
   source .venv/bin/activate
   celery -A src.posting.celery_app beat --loglevel=info
   ```

4. **Start the API Server**
   ```bash
   cd /Users/aidanyap/Clipping-automation-2.0
   source .venv/bin/activate
   python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. **Start the Frontend**
   ```bash
   cd /Users/aidanyap/Clipping-automation-2.0/frontend
   npm run dev
   ```

## Testing the Integration

### 1. Connect Social Accounts

1. Navigate to `http://localhost:8081/dashboard/social`
2. Click "Connect TikTok" or "Connect YouTube"
3. Complete the OAuth flow
4. Verify accounts appear as connected

### 2. Post a Clip

1. Go to `http://localhost:8081/dashboard/clips`
2. Click "Post to Social" on any clip
3. Select accounts and add caption
4. Choose immediate or scheduled posting
5. Submit the post

### 3. Monitor Posting Queue

1. Go to `http://localhost:8081/dashboard/social`
2. View the posting queue to see status
3. Retry failed posts if needed

## API Endpoints

### Social Media Management
- `GET /api/v1/social/accounts` - Get connected accounts
- `POST /api/v1/social/auth/{platform}/initiate` - Start OAuth flow
- `POST /api/v1/social/auth/{platform}/callback` - Complete OAuth
- `DELETE /api/v1/social/accounts/{account_id}` - Unlink account

### Posting
- `POST /api/v1/social/post` - Schedule/immediate post
- `GET /api/v1/social/queue` - Get posting queue
- `POST /api/v1/social/queue/{queue_id}/retry` - Retry failed post
- `DELETE /api/v1/social/queue/{queue_id}` - Cancel scheduled post

## Troubleshooting

### Common Issues

1. **OAuth Callback Errors**
   - Ensure `FRONTEND_URL` matches your frontend URL
   - Check that redirect URIs are configured in TikTok/YouTube apps
   - Verify state parameter handling

2. **Redis Connection Issues**
   - Ensure Redis server is running
   - Check `REDIS_URL` environment variable
   - Verify Redis is accessible from your application

3. **Video Upload Failures**
   - Check video file size limits (TikTok: 30MB, YouTube: 2GB)
   - Ensure video format is supported (MP4 recommended)
   - Verify access tokens are valid and not expired

4. **Celery Worker Issues**
   - Ensure Redis is running before starting Celery
   - Check worker logs for error messages
   - Verify task imports are correct

### Debug Commands

```bash
# Check Redis connection
redis-cli ping

# Check Celery worker status
celery -A src.posting.celery_app inspect active

# Check Celery beat status
celery -A src.posting.celery_app inspect scheduled

# View Celery logs
celery -A src.posting.celery_app events
```

## Platform-Specific Notes

### TikTok
- Video duration: 15 seconds to 10 minutes
- File size: Up to 30MB
- Formats: MP4, MOV, AVI
- Aspect ratio: 9:16 (vertical) recommended

### YouTube Shorts
- Video duration: Up to 60 seconds
- File size: Up to 2GB
- Formats: MP4, MOV, AVI, WMV
- Aspect ratio: 9:16 (vertical) for Shorts

## Security Considerations

1. **Token Storage**
   - Access tokens are encrypted in the database
   - Refresh tokens are stored securely
   - Tokens expire automatically

2. **OAuth Security**
   - State parameter prevents CSRF attacks
   - Secure redirect URIs only
   - Token exchange happens server-side

3. **Rate Limiting**
   - TikTok: 100 requests per hour
   - YouTube: 10,000 quota units per day
   - Automatic retry with exponential backoff

## Production Deployment

1. **Environment Variables**
   - Use secure secret management
   - Rotate API keys regularly
   - Use production Redis instance

2. **Scaling**
   - Run multiple Celery workers
   - Use Redis Cluster for high availability
   - Monitor queue length and processing time

3. **Monitoring**
   - Set up alerts for failed posts
   - Monitor API quota usage
   - Track posting success rates

## Support

For issues or questions:
1. Check the logs in the terminal
2. Verify environment variables
3. Test OAuth flows manually
4. Check platform API status pages
