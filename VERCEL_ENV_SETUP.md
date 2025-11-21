# Vercel Environment Variables Setup Guide

## 🚨 Current Issue
Frontend is missing Supabase configuration, causing console errors:
- `❌ Supabase configuration missing!`
- `Uncaught Error: supabaseUrl is required`

## ✅ Required Environment Variables for Vercel

You need to set these in **Vercel Dashboard** → Your Project → **Settings** → **Environment Variables**:

### 1. Supabase Configuration (REQUIRED)
```bash
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-supabase-anon-key
```

### 2. Backend API URL (REQUIRED)
```bash
VITE_API_URL=https://your-service.up.railway.app
```
**Note:** Replace with your actual Railway backend URL. Get it from Railway dashboard → Settings → Networking.

### 3. Optional Variables
```bash
VITE_ENABLE_ADMIN_CHECK=true  # Optional: Enable admin check
```

## 📋 Step-by-Step Setup

### Step 1: Get Supabase Credentials
1. Go to **Supabase Dashboard**: https://app.supabase.com
2. Select your project
3. Go to **Settings** → **API**
4. Copy:
   - **Project URL** → Use for `VITE_SUPABASE_URL`
   - **anon public** key → Use for `VITE_SUPABASE_ANON_KEY`

### Step 2: Get Railway Backend URL
1. Go to **Railway Dashboard**: https://railway.app
2. Select your **AscensionClips** project
3. Click on your backend service
4. Go to **Settings** → **Networking**
5. Copy the Railway-generated URL (format: `https://xxx.up.railway.app`)
   - Or generate a domain if not set
6. Use this for `VITE_API_URL`

### Step 3: Set Environment Variables in Vercel
1. Go to **Vercel Dashboard**: https://vercel.com
2. Select your project (likely `acensionclips.com`)
3. Go to **Settings** → **Environment Variables**
4. Add each variable:

   **Variable 1:**
   - **Key:** `VITE_SUPABASE_URL`
   - **Value:** `https://your-project.supabase.co`
   - **Environment:** Production, Preview, Development (select all)

   **Variable 2:**
   - **Key:** `VITE_SUPABASE_ANON_KEY`
   - **Value:** `your-supabase-anon-key`
   - **Environment:** Production, Preview, Development (select all)

   **Variable 3:**
   - **Key:** `VITE_API_URL`
   - **Value:** `https://your-service.up.railway.app`
   - **Environment:** Production, Preview, Development (select all)

### Step 4: Redeploy Vercel
After adding environment variables:
1. Go to **Deployments** tab
2. Click **⋯** (three dots) on latest deployment
3. Click **Redeploy**
4. Or push a new commit to trigger redeploy

## 🔍 How to Verify

After redeploying, check the browser console:
- ✅ Should see: `✅ Supabase connection OK`
- ❌ Should NOT see: `❌ Supabase configuration missing!`

## 🐛 Troubleshooting

### Issue: Still seeing errors after redeploy
**Solution:**
- Make sure you selected **all environments** (Production, Preview, Development)
- Clear browser cache and hard refresh (Cmd+Shift+R / Ctrl+Shift+R)
- Check Vercel deployment logs for build errors

### Issue: Can't find Railway backend URL
**Solution:**
- Railway may not have deployed yet
- Check Railway dashboard for deployment status
- If not deployed, wait for deployment to complete
- Or use `http://localhost:8000` for local development

### Issue: Supabase credentials not working
**Solution:**
- Double-check you copied the **anon public** key (not service role key)
- Verify the Supabase URL is correct (no trailing slash)
- Check Supabase project is active and not paused

## 📝 Environment Variable Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `VITE_SUPABASE_URL` | ✅ Yes | Supabase project URL | `https://xxx.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | ✅ Yes | Supabase anonymous key | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` |
| `VITE_API_URL` | ✅ Yes | Railway backend API URL | `https://xxx.up.railway.app` |
| `VITE_ENABLE_ADMIN_CHECK` | ⚠️ Optional | Enable admin features | `true` |

## ✅ Quick Checklist

- [ ] Got Supabase URL and anon key from Supabase dashboard
- [ ] Got Railway backend URL from Railway dashboard
- [ ] Added `VITE_SUPABASE_URL` to Vercel
- [ ] Added `VITE_SUPABASE_ANON_KEY` to Vercel
- [ ] Added `VITE_API_URL` to Vercel
- [ ] Selected all environments (Production, Preview, Development)
- [ ] Redeployed Vercel application
- [ ] Verified no console errors after redeploy

