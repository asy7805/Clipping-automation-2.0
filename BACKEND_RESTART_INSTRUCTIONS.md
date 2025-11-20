# Backend Restart Instructions

## Issue: 404 Error on Subscription Endpoints

The subscription router exists but returns 404 because the backend needs to be restarted to load it.

## Quick Fix

**Option 1: Kill and Restart (Recommended)**

```bash
# Kill existing backend
pkill -f "uvicorn.*main:app"

# Wait a moment
sleep 2

# Restart backend
cd /Users/aidanyap/Clipping-automation-2.0
python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Option 2: Use Your Start Script**

If you have a `start_api.py` or similar:
```bash
python start_api.py
```

**Option 3: Check Backend Logs**

```bash
tail -f backend.log
# Look for import errors or subscription-related errors
```

## Verify It's Working

After restarting, test:
```bash
# Should return 401 (unauthorized) not 404 (not found)
curl http://localhost:8000/api/v1/subscription/status
```

If you get **401**, the endpoint exists! The frontend will handle authentication automatically.

If you get **404**, check backend logs for import errors.

## Cron Jobs Setup

See `CRON_SETUP_GUIDE.md` for detailed instructions.

**Quick Setup (macOS):**

```bash
# Open crontab editor
crontab -e

# Add these lines (replace paths with your actual paths):
0 2 * * * cd /Users/aidanyap/Clipping-automation-2.0 && /usr/bin/python3 scripts/cleanup_expired_clips.py >> logs/cron_cleanup.log 2>&1
0 1 * * * cd /Users/aidanyap/Clipping-automation-2.0 && /usr/bin/python3 scripts/process_pro_renewals.py >> logs/cron_renewals.log 2>&1

# Save and exit
# Verify with: crontab -l
```

**Find Your Python Path:**
```bash
which python3
# Use that path in the cron job
```

