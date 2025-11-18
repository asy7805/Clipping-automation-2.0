# AscensionClips Deployment Guide

Complete guide to deploy AscensionClips to production.

## Overview

Your deployment consists of:
1. **Frontend** (Vite/React) → Deployed on **Vercel** ✅ (Already configured)
2. **Backend** (FastAPI) → Deployed on **Railway** using **Poetry** for dependency management ✅
3. **Database** (Supabase) → Already configured ✅
4. **Domain** → Connect to Vercel

## Pre-Deployment Setup (Local)

This project uses **Poetry** for Python dependency management. To set up locally:

1. **Install Poetry** (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Install dependencies**:
   ```bash
   poetry install
   ```

3. **Activate Poetry shell**:
   ```bash
   poetry shell
   ```

4. **Run the API locally**:
   ```bash
   cd src/api && poetry run uvicorn main:app --reload
   ```

**Note**: Railway will automatically use Poetry when it detects `pyproject.toml` in your repository.

---

## Step 1: Deploy Backend API

Choose one of these hosting platforms for your FastAPI backend:

### Option A: Render (Recommended for simplicity)

1. **Sign up/Login** to [Render.com](https://render.com)

2. **Create a new Web Service**
   - Connect your GitHub repository
   - Select the `production` branch
   - Service Type: **Web Service**

3. **Configure the service:**
   - **Name**: `ascension-clips-api`
   - **Region**: Choose closest to your users
   - **Branch**: `production`
   - **Root Directory**: Leave empty (root of repo)
   - **Runtime**: `Python 3`
   - **Build Command**: 
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command**: 
     ```bash
     cd src/api && python -m uvicorn main:app --host 0.0.0.0 --port $PORT
     ```
   - **Instance Type**: Choose based on your needs (Free tier available, but limited)

4. **Environment Variables** (see Step 3 below)

5. **Click "Create Web Service"**

### Option B: Railway (Recommended - Using Poetry) ⭐

1. **Sign up/Login** to [Railway.app](https://railway.app)

2. **Create a new project** → **Deploy from GitHub repo**
   - Select your repository
   - Branch: `production`

3. **Configure the service:**
   - Railway will auto-detect Python and Poetry (via `pyproject.toml`)
   - If using `Procfile`, Railway will automatically use it
   - If using `railway.json`, it will be detected automatically
   - **Build Command** (auto-detected, but you can verify):
     ```bash
     poetry install --no-dev
     ```
   - **Start Command** (from `Procfile` or `railway.json`):
     ```bash
     cd src/api && poetry run uvicorn main:app --host 0.0.0.0 --port $PORT
     ```

4. **Environment Variables** (see Step 3 below)

5. **Deploy** - Railway will automatically:
   - Detect Poetry from `pyproject.toml`
   - Run `poetry install --no-dev` to install dependencies
   - Start your FastAPI server using the Procfile or railway.json config

**Note**: Make sure `pyproject.toml`, `Procfile`, and/or `railway.json` are in your repository root.

### Option C: Fly.io

1. **Install Fly CLI**: 
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login**: 
   ```bash
   fly auth login
   ```

3. **Create app**: 
   ```bash
   fly launch
   ```

4. **Configure `fly.toml`**:
   ```toml
   app = "ascension-clips-api"
   primary_region = "iad"  # Choose your region
   
   [build]
   
   [http_service]
     internal_port = 8000
     force_https = true
     auto_stop_machines = true
     auto_start_machines = true
     min_machines_running = 0
   
   [[services]]
     protocol = "tcp"
     internal_port = 8000
   ```

5. **Deploy**: 
   ```bash
   fly deploy
   ```

---

## Step 2: Get Your Backend URL

After deploying, you'll get a URL like:
- **Render**: `https://ascension-clips-api.onrender.com`
- **Railway**: `https://ascension-clips-api.up.railway.app`
- **Fly.io**: `https://ascension-clips-api.fly.dev`

**Save this URL** - you'll need it for the frontend configuration.

---

## Step 3: Configure Backend Environment Variables

Add these environment variables in your backend hosting platform:

### Required Variables:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_JWT_SECRET=your-supabase-jwt-secret

# Twitch API
TWITCH_CLIENT_ID=your-twitch-client-id
TWITCH_CLIENT_SECRET=your-twitch-client-secret

# OpenAI (Optional - for advanced features)
OPENAI_API_KEY=your-openai-api-key

# Captions.ai (Optional)
CAPTIONS_AI_API_KEY=your-captions-ai-api-key

# CORS Origins (Update with your Vercel domain)
ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

### How to find these values:

1. **Supabase**:
   - Go to your Supabase project → Settings → API
   - Copy `URL`, `anon public` key, and `JWT Secret`

2. **Twitch**:
   - Go to [Twitch Developer Console](https://dev.twitch.tv/console)
   - Create/select your app
   - Copy `Client ID` and `Client Secret`

3. **OpenAI & Captions.ai**:
   - From your account settings

### Update CORS in Backend:

After getting your Vercel domain, update `src/api/main.py`:

```python
# Update this line (around line 50):
allow_origins=["*"],  # Change this

# To:
allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
allow_origins=allowed_origins if allowed_origins[0] else ["*"],
```

Or keep it as `["*"]` for development and restrict in production using the env var.

---

## Step 4: Configure Frontend Environment Variables (Vercel)

1. **Go to Vercel Dashboard** → Your project → Settings → Environment Variables

2. **Add these variables:**

```bash
# Backend API URL (from Step 2)
VITE_API_URL=https://your-backend-url.onrender.com

# Supabase Configuration
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-supabase-anon-key

# Admin Check (optional)
VITE_ENABLE_ADMIN_CHECK=true
```

3. **Redeploy** your Vercel app to apply changes:
   - Go to Deployments tab
   - Click the "..." menu on the latest deployment
   - Select "Redeploy"

---

## Step 5: Connect Your Domain to Vercel

1. **Go to Vercel Dashboard** → Your project → Settings → Domains

2. **Add your domain**:
   - Enter your domain (e.g., `ascensionclips.com`)
   - Click "Add"

3. **Configure DNS**:
   - Vercel will show you DNS records to add
   - Go to your domain registrar (e.g., Namecheap, GoDaddy)
   - Add the DNS records:
     - **Type**: `A` or `CNAME`
     - **Name**: `@` or `www`
     - **Value**: Vercel-provided IP or CNAME

4. **Wait for DNS propagation** (5 minutes to 48 hours)

5. **SSL Certificate**: Vercel automatically provisions SSL certificates

---

## Step 6: Update Backend CORS for Production

Once your domain is live, update backend CORS:

1. **In your backend hosting platform**, update environment variable:
   ```bash
   ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com,https://your-vercel-app.vercel.app
   ```

2. **Redeploy the backend** to apply changes

---

## Step 7: Test Your Deployment

1. **Frontend**: Visit `https://your-domain.com`
   - Should load the AscensionClips interface
   - Check browser console for errors

2. **Backend Health Check**: Visit `https://your-backend-url/api/v1/health`
   - Should return `{"status": "healthy"}`

3. **API Connection**: 
   - Try logging in on your frontend
   - Check if API calls are working (open DevTools → Network tab)

4. **Test Monitor Creation**:
   - Create a monitor from the dashboard
   - Verify it starts correctly

---

## Step 8: Monitor Logs

### Vercel (Frontend):
- Dashboard → Your project → Deployments → Click on deployment → View Build Logs

### Backend:
- **Render**: Dashboard → Your service → Logs
- **Railway**: Dashboard → Your service → Deployments → View Logs
- **Fly.io**: `fly logs` or Dashboard → Your app → Logs

---

## Troubleshooting

### Frontend can't connect to backend:
- ✅ Check `VITE_API_URL` in Vercel environment variables
- ✅ Verify backend URL is correct and accessible
- ✅ Check backend CORS settings
- ✅ Ensure backend is running (check health endpoint)

### Backend errors:
- ✅ Check all environment variables are set
- ✅ Verify Supabase connection (check logs)
- ✅ Check Twitch API credentials
- ✅ Review backend logs for specific errors

### Domain not working:
- ✅ Verify DNS records are correct
- ✅ Wait for DNS propagation (can take up to 48 hours)
- ✅ Check Vercel domain settings show "Valid Configuration"

### Monitors not starting:
- ✅ Check backend has required dependencies installed
- ✅ Verify `scripts/live_ingest.py` has executable permissions
- ✅ Check backend logs for monitor errors
- ✅ Ensure backend has enough resources (CPU/memory)

---

## Environment Variables Checklist

### Frontend (Vercel):
- [ ] `VITE_API_URL`
- [ ] `VITE_SUPABASE_URL`
- [ ] `VITE_SUPABASE_ANON_KEY`
- [ ] `VITE_ENABLE_ADMIN_CHECK` (optional)

### Backend (Render/Railway/Fly.io):
- [ ] `SUPABASE_URL`
- [ ] `SUPABASE_KEY`
- [ ] `SUPABASE_JWT_SECRET`
- [ ] `TWITCH_CLIENT_ID`
- [ ] `TWITCH_CLIENT_SECRET`
- [ ] `OPENAI_API_KEY` (optional)
- [ ] `CAPTIONS_AI_API_KEY` (optional)
- [ ] `ALLOWED_ORIGINS` (for CORS)

---

## Next Steps After Deployment

1. **Monitor Performance**: Set up monitoring/alerts for your backend
2. **Set up Backups**: Ensure Supabase backups are configured
3. **Update README**: Document your production URLs
4. **Set up CI/CD**: Automate testing before production deploys
5. **Security**: 
   - Review API rate limiting
   - Enable Supabase Row Level Security (RLS)
   - Rotate API keys regularly

---

## Recommended Resources

- **Render Docs**: https://render.com/docs
- **Railway Docs**: https://docs.railway.app
- **Fly.io Docs**: https://fly.io/docs
- **Vercel Docs**: https://vercel.com/docs
- **Supabase Docs**: https://supabase.com/docs

---

## Support

If you encounter issues:
1. Check logs in your hosting platform
2. Review this deployment guide
3. Check GitHub issues
4. Review backend/frontend error messages

---

**Last Updated**: 2025-01-17

