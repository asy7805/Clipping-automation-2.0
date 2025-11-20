# Quick Fix Guide

## Issue 1: 404 Error on `/api/v1/subscription/check-trial`

### Problem
The endpoint returns 404 because the backend needs to be restarted to load the new subscription router.

### Solution

**Option A: Restart Backend Manually**

1. Find the backend process:
   ```bash
   ps aux | grep uvicorn
   ```

2. Kill it:
   ```bash
   pkill -f "uvicorn.*main:app"
   ```

3. Restart it:
   ```bash
   cd /Users/aidanyap/Clipping-automation-2.0
   python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
   ```

**Option B: Use Your Existing Start Script**

If you have a `start_api.py` or similar script:
```bash
python start_api.py
```

**Option C: Check Backend Logs**

Check if there are any import errors:
```bash
tail -f backend.log
# or
tail -f logs/backend.log
```

### Verify It's Working

After restarting, test the endpoint:
```bash
# Should return 401 (unauthorized) not 404 (not found)
curl http://localhost:8000/api/v1/subscription/status
```

If you get 401, the endpoint exists! The frontend will handle authentication automatically.

## Issue 2: Cron Jobs Setup

### What Are Cron Jobs?

Cron jobs are scheduled tasks that run automatically. We need two:

1. **Cleanup expired clips** - Daily at 2 AM
2. **Process Pro renewals** - Daily at 1 AM

### Easiest Setup (macOS)

1. **Open crontab editor:**
   ```bash
   crontab -e
   ```

2. **Add these two lines** (replace paths with your actual paths):
   ```bash
   0 2 * * * cd /Users/aidanyap/Clipping-automation-2.0 && /Users/aidanyap/Clipping-automation-2.0/.venv/bin/python scripts/cleanup_expired_clips.py >> /Users/aidanyap/Clipping-automation-2.0/logs/cron_cleanup.log 2>&1
   0 1 * * * cd /Users/aidanyap/Clipping-automation-2.0 && /Users/aidanyap/Clipping-automation-2.0/.venv/bin/python scripts/process_pro_renewals.py >> /Users/aidanyap/Clipping-automation-2.0/logs/cron_renewals.log 2>&1
   ```

3. **Save and exit** (in nano: `Ctrl+X`, then `Y`, then Enter)

4. **Verify:**
   ```bash
   crontab -l
   ```

### Find Your Python Path

If you're not sure where Python is:
```bash
which python3
# or
which python
```

If using a virtual environment:
```bash
# Activate your venv first
source .venv/bin/activate  # or venv/bin/activate
which python
```

### Test Manually First

Before setting up cron, test the scripts manually:

```bash
# Test cleanup
python scripts/cleanup_expired_clips.py

# Test renewals  
python scripts/process_pro_renewals.py
```

If they work manually, they'll work in cron!

### For Production (Railway/Render/Vercel)

**Railway:**
- Add a "Cron Job" service
- Command: `python scripts/cleanup_expired_clips.py`
- Schedule: `0 2 * * *` (2 AM daily)

**Render:**
- Create a "Cron Job"
- Same settings as above

**Vercel:**
- Use Vercel Cron Jobs in `vercel.json`:
```json
{
  "crons": [
    {
      "path": "/api/cron/cleanup",
      "schedule": "0 2 * * *"
    }
  ]
}
```

## Quick Test Commands

```bash
# Test subscription endpoint (should get 401, not 404)
curl http://localhost:8000/api/v1/subscription/status

# Test with auth token (replace TOKEN)
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/subscription/status

# Check backend is running
ps aux | grep uvicorn

# Check backend logs
tail -f backend.log
```

## Still Having Issues?

1. **Check backend logs** for import errors
2. **Verify Python path** in cron jobs
3. **Test scripts manually** before adding to cron
4. **Check file permissions**: `chmod +x scripts/*.py`

