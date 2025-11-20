# Cron Jobs Setup Guide

## What are Cron Jobs?

Cron jobs are scheduled tasks that run automatically at specified times. We need two cron jobs for the subscription system:

1. **Cleanup Expired Clips** - Runs daily at 2 AM to delete expired free trial clips
2. **Process Pro Renewals** - Runs daily at 1 AM to handle Pro subscription renewals and expirations

## Setup Instructions

### Option 1: Using macOS/Linux Cron (Recommended for Local Development)

1. **Open your crontab editor:**
   ```bash
   crontab -e
   ```

2. **Add these lines at the end of the file:**
   ```bash
   # Cleanup expired clips daily at 2 AM
   0 2 * * * cd /Users/aidanyap/Clipping-automation-2.0 && /Users/aidanyap/Clipping-automation-2.0/.venv/bin/python scripts/cleanup_expired_clips.py >> logs/cron_cleanup.log 2>&1

   # Process Pro renewals daily at 1 AM
   0 1 * * * cd /Users/aidanyap/Clipping-automation-2.0 && /Users/aidanyap/Clipping-automation-2.0/.venv/bin/python scripts/process_pro_renewals.py >> logs/cron_renewals.log 2>&1
   ```

3. **Save and exit** (in vim: press `Esc`, type `:wq`, press Enter)

4. **Verify your cron jobs:**
   ```bash
   crontab -l
   ```

### Option 2: Using Systemd Timers (Linux)

Create two timer files:

**`/etc/systemd/system/cleanup-clips.timer`:**
```ini
[Unit]
Description=Daily cleanup of expired clips

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

**`/etc/systemd/system/cleanup-clips.service`:**
```ini
[Unit]
Description=Cleanup expired clips

[Service]
Type=oneshot
WorkingDirectory=/Users/aidanyap/Clipping-automation-2.0
ExecStart=/Users/aidanyap/Clipping-automation-2.0/.venv/bin/python scripts/cleanup_expired_clips.py
```

Then enable with:
```bash
sudo systemctl enable cleanup-clips.timer
sudo systemctl start cleanup-clips.timer
```

### Option 3: Using Railway/Render Scheduled Tasks

If deploying to Railway or Render:

**Railway:**
1. Go to your project settings
2. Add a new service
3. Set command: `python scripts/cleanup_expired_clips.py`
4. Set schedule: `0 2 * * *` (cron format)

**Render:**
1. Create a new "Cron Job"
2. Set command: `python scripts/cleanup_expired_clips.py`
3. Set schedule: `0 2 * * *`

### Option 4: Manual Testing (No Cron)

For testing, you can run the scripts manually:

```bash
# Test cleanup script
python scripts/cleanup_expired_clips.py

# Test renewal script
python scripts/process_pro_renewals.py
```

## Important Notes

1. **Python Path**: Make sure to use the full path to your Python executable (`.venv/bin/python` or your virtual environment path)

2. **Working Directory**: The scripts need to run from the project root directory

3. **Environment Variables**: Make sure your `.env` file is accessible and contains:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY` (required for admin operations)
   - `STORAGE_BUCKET`

4. **Logs**: The cron jobs will write logs to `logs/cron_cleanup.log` and `logs/cron_renewals.log`

5. **Testing**: Test the scripts manually first before setting up cron:
   ```bash
   # Test cleanup
   python scripts/cleanup_expired_clips.py
   
   # Test renewals
   python scripts/process_pro_renewals.py
   ```

## Troubleshooting

**Cron job not running?**
- Check cron logs: `grep CRON /var/log/syslog` (Linux) or check Console.app (macOS)
- Verify Python path is correct
- Check file permissions: `chmod +x scripts/cleanup_expired_clips.py`
- Test manually first

**Permission errors?**
- Make sure scripts are executable: `chmod +x scripts/*.py`
- Check that the user running cron has access to the project directory

**Environment variables not found?**
- Cron jobs don't inherit your shell environment
- Either set them in the crontab or use absolute paths to `.env` file
- Or add `source ~/.bashrc` or `source ~/.zshrc` before the command

## Quick Setup (Copy-Paste Ready)

For macOS with virtual environment in `.venv`:

```bash
# Add to crontab
(crontab -l 2>/dev/null; echo "0 2 * * * cd /Users/aidanyap/Clipping-automation-2.0 && /Users/aidanyap/Clipping-automation-2.0/.venv/bin/python scripts/cleanup_expired_clips.py >> /Users/aidanyap/Clipping-automation-2.0/logs/cron_cleanup.log 2>&1") | crontab -

(crontab -l 2>/dev/null; echo "0 1 * * * cd /Users/aidanyap/Clipping-automation-2.0 && /Users/aidanyap/Clipping-automation-2.0/.venv/bin/python scripts/process_pro_renewals.py >> /Users/aidanyap/Clipping-automation-2.0/logs/cron_renewals.log 2>&1") | crontab -
```

