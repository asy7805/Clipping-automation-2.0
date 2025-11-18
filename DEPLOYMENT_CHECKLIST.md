# 🚀 AscensionClips Deployment Checklist

Quick checklist to deploy AscensionClips to production.

## ✅ Pre-Deployment

- [ ] Vercel is configured (already done ✅)
- [ ] Poetry configuration files created (`pyproject.toml`, `Procfile`, `railway.json`) ✅
- [ ] Production branch has all frontend code
- [ ] All environment variables documented
- [ ] Test Poetry setup locally (optional): `poetry install && poetry shell`

---

## 📋 Step-by-Step Checklist

### 1. Deploy Backend API (Railway + Poetry)

- [ ] Verify `pyproject.toml`, `Procfile`, and `railway.json` are in repository root
- [ ] Sign up/login to [Railway.app](https://railway.app)
- [ ] Create new project → Deploy from GitHub repo
- [ ] Select your repository and `production` branch
- [ ] Railway will auto-detect Poetry from `pyproject.toml`
- [ ] Verify build command (should be auto-detected): `poetry install --no-dev`
- [ ] Verify start command (from Procfile): `cd src/api && poetry run uvicorn main:app --host 0.0.0.0 --port $PORT`
- [ ] Deploy backend
- [ ] Save backend URL: `https://your-app.up.railway.app`

### 2. Configure Backend Environment Variables

Add these to your backend hosting platform:

- [ ] `SUPABASE_URL`
- [ ] `SUPABASE_KEY`
- [ ] `SUPABASE_JWT_SECRET`
- [ ] `TWITCH_CLIENT_ID`
- [ ] `TWITCH_CLIENT_SECRET`
- [ ] `OPENAI_API_KEY` (optional)
- [ ] `CAPTIONS_AI_API_KEY` (optional)
- [ ] `ALLOWED_ORIGINS` (add after getting Vercel domain)

### 3. Test Backend

- [ ] Visit `https://your-backend-url/api/v1/health`
- [ ] Should return `{"status": "healthy"}`
- [ ] Check backend logs for errors

### 4. Configure Frontend (Vercel)

In Vercel Dashboard → Settings → Environment Variables:

- [ ] `VITE_API_URL` = `https://your-backend-url`
- [ ] `VITE_SUPABASE_URL`
- [ ] `VITE_SUPABASE_ANON_KEY`
- [ ] `VITE_ENABLE_ADMIN_CHECK` (optional)

### 5. Redeploy Frontend

- [ ] Go to Vercel → Deployments
- [ ] Redeploy latest deployment to apply env vars

### 6. Connect Domain to Vercel

- [ ] Go to Vercel → Settings → Domains
- [ ] Add your domain (e.g., `ascensionclips.com`)
- [ ] Configure DNS records at your domain registrar
- [ ] Wait for DNS propagation (5 min - 48 hours)
- [ ] Verify SSL certificate is issued

### 7. Update Backend CORS

- [ ] Update `ALLOWED_ORIGINS` in backend to include:
  - `https://your-domain.com`
  - `https://www.your-domain.com`
  - `https://your-vercel-app.vercel.app`
- [ ] Redeploy backend

### 8. Final Testing

- [ ] Visit `https://your-domain.com`
- [ ] Frontend loads correctly
- [ ] Can log in
- [ ] API calls work (check browser console)
- [ ] Can create a monitor
- [ ] Monitor starts successfully
- [ ] Clips are being generated

---

## 🔧 Troubleshooting

### Frontend Issues:
- Check `VITE_API_URL` is correct
- Verify backend is accessible
- Check browser console for errors
- Verify Supabase env vars are set

### Backend Issues:
- Check all env vars are set
- Review backend logs
- Verify Supabase connection
- Check Twitch API credentials

### Domain Issues:
- Verify DNS records are correct
- Wait for DNS propagation
- Check Vercel domain settings

---

## 📚 Documentation

See `docs/DEPLOYMENT_GUIDE.md` for detailed instructions.

---

**Status**: ⏳ Ready to deploy

