# Railway Dashboard Deployment Checklist

## 🔍 How to Check Railway Deployment Status

### Step 1: Access Railway Dashboard
1. Go to **https://railway.app**
2. Log in to your account
3. Select project: **AscensionClips**

### Step 2: Check Service Status
1. **Find your backend service** (may be named "AscensionClips" or similar)
2. **Check deployment status:**
   - ✅ **Active/Deployed** = Success
   - ⏳ **Building** = In progress
   - ❌ **Failed** = Error occurred
   - ⚠️ **Stopped** = Not running

### Step 3: Review Latest Deployment
Click on the most recent deployment to see:

#### Build Phase:
- ✅ Setup phase (pip, poetry install)
- ✅ Install phase (dependencies ~3-4 min)
- ✅ Build phase (cleanup)
- ✅ Import to Docker (should complete now with Hobby plan)

#### Runtime Phase:
- ✅ Container starting
- ✅ Application logs
- Look for: `🚀 Starting Clipping Automation API...`
- Check for any errors

### Step 4: Check Logs
1. Click **"View Logs"** or **"Deployments"** → Latest deployment
2. Look for:
   - ✅ `Starting Clipping Automation API...`
   - ✅ `✅ Subscription router imported successfully`
   - ✅ `Uvicorn running on http://0.0.0.0:PORT`
   - ❌ Any `ImportError` or `ModuleNotFoundError`
   - ❌ Any connection errors

### Step 5: Verify Environment Variables
1. Go to **Settings** → **Variables**
2. Verify these are set:
   - ✅ `SUPABASE_URL`
   - ✅ `SUPABASE_KEY` (or `SUPABASE_ANON_KEY`)
   - ✅ `SUPABASE_JWT_SECRET`
   - ✅ `TWITCH_CLIENT_ID`
   - ✅ `TWITCH_CLIENT_SECRET`
   - ✅ `PORT` (usually auto-set by Railway)
   - ⚠️ `OPENAI_API_KEY` (optional)
   - ⚠️ `CAPTIONS_AI_API_KEY` (optional)
   - ⚠️ `ALLOWED_ORIGINS` (optional)

### Step 6: Get Railway Backend URL
1. Go to **Settings** → **Networking** or **Domains**
2. Look for Railway-generated URL:
   - Format: `https://your-service-name.up.railway.app`
   - Or check **"Generate Domain"** if not set

### Step 7: Test Backend API
Test the Railway backend URL directly:

```bash
# Health check
curl https://your-service.up.railway.app/api/v1/health

# Should return:
# {"status":"healthy","version":"2.0.0"}
```

## 🐛 Common Issues & Solutions

### Issue: "ImportError: attempted relative import"
**Status:** ✅ **FIXED** in commit `67f289fc`
- Start command now uses: `uvicorn src.api.main:app`
- Should be resolved in latest deployment

### Issue: Build timeout
**Status:** ✅ **FIXED** - Upgraded to Hobby plan (40 min timeout)
- Build should complete successfully now

### Issue: Image size > 4GB
**Status:** ✅ **OPTIMIZED** in commit `f93c3958`
- Removed frontend (729MB)
- Removed unnecessary scripts and files
- Should be under 4GB now

### Issue: Service not found
**Solution:** 
- Check if service exists in Railway dashboard
- May need to create new service or link existing one
- Run: `railway service` to link via CLI

## 📊 Expected Deployment Times

With Hobby plan and optimizations:
- **Build time:** ~8-12 minutes
- **Upload time:** ~2-5 minutes (depends on image size)
- **Total:** ~10-17 minutes (well under 40 min limit)

## ✅ Success Indicators

Your deployment is successful if you see:
1. ✅ Deployment status: **Active/Deployed**
2. ✅ Logs show: `Uvicorn running on http://0.0.0.0:PORT`
3. ✅ Health endpoint returns: `{"status":"healthy"}`
4. ✅ No errors in logs
5. ✅ Service is **Running** (green status)

## 🔗 Quick Links

- **Railway Dashboard:** https://railway.app
- **Project:** AscensionClips
- **Branch:** production
- **Domain:** https://acensionclips.com (points to Vercel frontend)

## 📝 Next Steps After Successful Deployment

1. **Get Railway backend URL** from dashboard
2. **Update frontend** (Vercel) environment variable:
   - `VITE_API_URL=https://your-service.up.railway.app`
3. **Test API endpoints** via Railway URL
4. **Configure custom domain** (optional) for Railway backend

