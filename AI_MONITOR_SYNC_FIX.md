# AI Monitor Sync Fix

## Problem

The monitor cards were showing AI health status (red indicator) that was out of sync with the actual monitor state. Specifically:

- **Symptom**: Monitor card showing:
  - 🔴 AI: Red (process not running)
  - ✅ Stream: Green (Twitch stream live)
  - Last clip: 14d ago
  - 18 segments, 6 clips

- **Root Cause**: 
  - Monitor process crashed/died 14 days ago
  - Database still had monitor status as "running"
  - Dead monitors were still being displayed in UI
  - No automatic cleanup of dead processes

## Solution

### Backend Changes (`src/api/routers/monitors.py`)

1. **Enhanced Dead Process Detection**:
   - `/monitors` endpoint now actively checks if each monitor's process is still alive
   - If process is dead, immediately updates database status to "stopped"
   - **Filters out stopped monitors** from API response

```python
# Update status for each monitor and filter out stopped ones
active_monitors_list = []
for monitor in monitors.data or []:
    pid = monitor.get('process_id')
    if monitor['status'] == 'running' and pid:
        if not is_process_running(pid):
            # Update database if process died
            monitor['status'] = 'stopped'
            sb.table('monitors')\
                .update({'status': 'stopped', 'stopped_at': datetime.utcnow().isoformat()})\
                .eq('id', monitor['id'])\
                .execute()
            # Skip stopped monitors - don't show them in UI
            continue
    
    # Only include running monitors in the response
    if monitor['status'] == 'running':
        active_monitors_list.append(monitor)
```

### Frontend Changes (`frontend/src/components/StreamMonitorCard.tsx`)

1. **Restart Warning UI**:
   - When `health.process_alive` is `false`, shows a prominent warning card
   - Displays clear message: "Monitor Process Stopped"
   - Provides one-click "Restart Monitor" button

```tsx
{/* Show restart warning when AI process is dead */}
{!health.process_alive && (
  <div className="mt-3 p-3 bg-destructive/10 border border-destructive/30 rounded-lg">
    <div className="flex items-start gap-2 mb-2">
      <AlertTriangle className="w-4 h-4 text-destructive mt-0.5 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-destructive">Monitor Process Stopped</p>
        <p className="text-xs text-muted-foreground mt-1">
          The AI monitoring process has stopped. Restart it to continue capturing clips.
        </p>
      </div>
    </div>
    <Button onClick={handleRestart}>
      <Play className="w-4 h-4 mr-2" />
      Restart Monitor
    </Button>
  </div>
)}
```

## How It Works Now

1. **When user loads dashboard**:
   - Backend queries all monitors from database
   - For each monitor marked as "running", checks if process (PID) is actually alive
   - If process is dead → updates DB to "stopped" → filters out from response
   - Only active, running monitors are returned to frontend

2. **If a process dies while user is viewing**:
   - Health check endpoint detects dead process
   - AI indicator turns red
   - Restart warning appears with one-click restart button
   - User can immediately restart the monitor without manual cleanup

3. **Automatic Cleanup**:
   - Every time `/monitors` is called, dead processes are detected and marked as stopped
   - No more "zombie" monitors cluttering the UI
   - Database stays in sync with actual process state

## Benefits

✅ **Automatic dead process detection** - No manual cleanup needed
✅ **Clear user feedback** - Obvious when a monitor needs attention
✅ **One-click restart** - Easy recovery from crashes
✅ **Database consistency** - Monitor status always reflects reality
✅ **Cleaner UI** - Dead monitors automatically removed from display

## Testing

1. **Test automatic cleanup**:
   ```bash
   # Kill a monitor process manually
   kill -9 <monitor_pid>
   
   # Refresh dashboard
   # Monitor should disappear from UI automatically
   ```

2. **Test restart button**:
   - Kill a monitor process
   - Before it's filtered out, click "Restart Monitor"
   - Monitor should restart successfully

3. **Test with old stopped monitors**:
   ```bash
   # Check database for old stopped monitors
   # They should not appear in UI
   ```

## Migration Notes

- Existing stopped monitors in database will be automatically filtered out
- No database migrations required
- Changes are backward compatible

## Related Files

- `src/api/routers/monitors.py` - Backend monitor management
- `frontend/src/components/StreamMonitorCard.tsx` - Monitor card UI
- `frontend/src/hooks/useStreamData.ts` - Already had client-side filtering

## Future Improvements

- Add automatic process restart on crash detection
- Add monitor health history/logs
- Add email/notification alerts when monitors stop
- Add "Auto-restart" toggle in monitor settings

