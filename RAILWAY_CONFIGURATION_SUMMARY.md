# Railway Configuration Summary

## ✅ What's Been Configured

### 1. Poetry-Only Build
- ✅ Created `nixpacks.toml` to force Railway to use Poetry exclusively
- ✅ Updated `railway.json` with Poetry build command: `poetry install --no-dev --no-root`
- ✅ `requirements.txt` is kept for reference but won't be used by Railway (Nixpacks will use `nixpacks.toml` instead)

### 2. Production Branch Deployment
- ✅ `railway.json` includes `"github": { "branch": "production" }`
- ⚠️ **Action Required**: You still need to configure the branch in Railway Dashboard:
  1. Go to: https://railway.com/project/fa856f9a-ee03-46c0-8e02-e2d819f9459a
  2. Click your service
  3. Settings → Source → Branch: Select `production`
  4. Save

### 3. Build Configuration

**Nixpacks Configuration** (`nixpacks.toml`):
- Uses Python 3.12 and Poetry
- Installs dependencies via: `poetry install --no-dev --no-root`
- Starts app via: `poetry run uvicorn main:app`

**Railway JSON** (`railway.json`):
- Builder: NIXPACKS
- Build Command: `poetry install --no-dev --no-root`
- Start Command: `cd src/api && poetry run uvicorn main:app --host 0.0.0.0 --port $PORT`

## How It Works Now

1. **When you push to `production` branch:**
   - Railway detects the push
   - Nixpacks reads `nixpacks.toml` (not `requirements.txt`)
   - Installs Poetry and Python 3.12
   - Runs `poetry install --no-dev --no-root` (uses `pyproject.toml` and `poetry.lock`)
   - Starts the FastAPI server using Poetry

2. **Dependency Management:**
   - All dependencies come from `pyproject.toml`
   - `poetry.lock` ensures consistent versions
   - `requirements.txt` is ignored by Railway (but kept for reference)

## Next Steps

1. **Set Production Branch in Railway Dashboard** (if not done):
   - Railway Dashboard → Service → Settings → Source → Branch: `production`

2. **Commit and Push Configuration:**
   ```bash
   git add nixpacks.toml railway.json requirements.txt
   git commit -m "Configure Railway to use Poetry exclusively and deploy from production branch"
   git push origin production
   ```

3. **Monitor Deployment:**
   - Railway will automatically deploy when you push to `production`
   - Check build logs in Railway dashboard
   - Test: `curl https://your-url.up.railway.app/api/v1/health`

## Verification

After deployment, verify:
- ✅ Build logs show `poetry install` (not `pip install -r requirements.txt`)
- ✅ All dependencies install from Poetry
- ✅ App starts successfully
- ✅ Only deploys from `production` branch (matches Vercel)

