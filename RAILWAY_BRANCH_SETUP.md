# Railway Production Branch Configuration

## Configure Railway to Deploy from Production Branch

Railway needs to be configured to deploy from the `production` branch (same as Vercel).

### Option 1: Via Railway Dashboard (Recommended)

1. Go to your Railway project: https://railway.com/project/fa856f9a-ee03-46c0-8e02-e2d819f9459a
2. Click on your service
3. Go to **Settings** tab
4. Scroll to **Source** section
5. Under **Branch**, select `production` from the dropdown
6. Save changes

### Option 2: Via Railway CLI

```bash
# Link to the service first
railway service 19ef5048-9deb-45cf-a9ce-1e3c8a1fa5fe

# Set the branch (if CLI supports it)
# Note: Branch configuration may need to be done via dashboard
```

### Verify Configuration

After setting the branch:
- Railway will only deploy when you push to the `production` branch
- This matches your Vercel deployment workflow
- Both frontend (Vercel) and backend (Railway) will deploy from the same branch

## Current Setup

✅ **Poetry Configuration**: `nixpacks.toml` created to use Poetry exclusively
✅ **Build Command**: `poetry install --no-dev --no-root`
✅ **Start Command**: Uses Poetry to run uvicorn
✅ **Branch**: Needs to be set to `production` in Railway dashboard

## Next Steps

1. Set branch to `production` in Railway dashboard
2. Push your changes to `production` branch
3. Railway will automatically deploy using Poetry

