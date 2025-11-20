# Railway Deployment Guide

## Quick Start

Your project is ready to deploy! Follow these steps:

### Step 1: Login to Railway (Interactive - Required)

Run this command in your terminal (it will open a browser):

```bash
cd /Users/aidanyap/Clipping-automation-2.0
railway login
```

This will open your browser for authentication. Complete the login process.

### Step 2: Initialize Railway Project

After logging in, run:

```bash
railway init
```

Choose:
- **Create a new project** (recommended for first time)
- Or **Link to existing project** if you already have one

### Step 3: Set Environment Variables

Your `.env` file contains the necessary variables. Set them in Railway:

```bash
# Read .env and set variables in Railway
railway variables set $(cat .env | grep -v '^#' | xargs)
```

Or set them individually:

```bash
railway variables set SUPABASE_URL="your-value"
railway variables set SUPABASE_KEY="your-value"
# ... etc
```

### Step 4: Deploy

```bash
railway up
```

This will:
1. Build your project using Poetry (`poetry install --no-dev`)
2. Start your FastAPI server
3. Deploy to Railway

### Step 5: Get Your URL

```bash
railway domain
```

Or check your Railway dashboard for the deployment URL.

### Step 6: Verify Deployment

Test your deployment:

```bash
# Get the URL first
RAILWAY_URL=$(railway domain)

# Test health endpoint
curl $RAILWAY_URL/api/v1/health

# View API docs
open $RAILWAY_URL/docs
```

## Automated Deployment Script

You can also use the Python script:

```bash
python3 scripts/deploy_railway.py
```

**Note**: The login step will still require browser interaction.

## View Logs

```bash
railway logs
```

## Railway Configuration

Your project already has:
- ✅ `railway.json` - Build and deploy configuration
- ✅ `pyproject.toml` - Poetry dependencies
- ✅ `Procfile` - Alternative start command

Railway will automatically:
- Detect Poetry from `pyproject.toml`
- Use `poetry install --no-dev` for building
- Use the start command from `railway.json`

## Troubleshooting

### Build Fails
- Check logs: `railway logs`
- Verify `pyproject.toml` is valid: `poetry check`
- Ensure all dependencies are listed in `pyproject.toml`

### App Crashes
- Check environment variables are set: `railway variables`
- Verify Supabase connection
- Check logs for specific errors

### Port Issues
- Railway sets `$PORT` automatically - your config uses this correctly

## Next Steps After Deployment

1. **Update Frontend**: Set `VITE_API_URL` in Vercel to your Railway URL
2. **Configure CORS**: Update `ALLOWED_ORIGINS` in Railway variables
3. **Monitor**: Check Railway dashboard for metrics and logs
4. **Set Custom Domain**: Configure in Railway Settings → Networking

