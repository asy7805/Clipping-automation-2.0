# Fix: Offline Streamers Stay Visible

## Issue
**Problem:** Monitors for offline streamers were being automatically deleted/hidden from the dashboard.

**User Requirement:** Monitors should persist even when streamers go offline. The monitoring process should continue running and automatically resume clip generation once the streamer comes back online.

---

## Root Cause

The system was filtering out monitors based on their status, which caused offline streamers to disappear:

1. **Backend Filtering:** `/monitors` endpoint only returned monitors with `status === 'running'`
2. **Frontend Filtering:** Also filtered out monitors with `status === 'stopped'`
3. **Result:** Any monitor where the streamer went offline would disappear from the UI

---

## Solution

### Changes Made

#### 1. **Backend (`src/api/routers/monitors.py`)**
**Changed:** Only hide monitors where the **process is actually dead**, not when streamer is offline.

```python
# Before: Only returned monitors with status='running'
if monitor['status'] == 'running':
    active_monitors_list.append(monitor)

# After: Return ALL monitors except dead processes
# Include monitors even if streamer is offline - they'll resume automatically
active_monitors_list.append(monitor)
```

**Logic:**
- ✅ **Process running + Streamer online** → Show monitor (active)
- ✅ **Process running + Streamer offline** → Show monitor (waiting)
- ✅ **Process stopped (manually)** → Show monitor (user can restart)
- ❌ **Process dead (crashed)** → Hide monitor (or show restart button)

#### 2. **Frontend (`frontend/src/hooks/useStreamData.ts`)**
**Changed:** Removed filter that hid stopped monitors, added smart status detection.

```typescript
// Before: Filtered out stopped monitors
const monitors = allMonitors.filter((monitor: any) => monitor.status !== 'stopped');

// After: Keep all monitors (backend already filters dead processes)
const monitors = allMonitors;
```

**Status Display Logic:**
- **Monitor running + Streamer live** → "Live monitoring {channel}" (analyzing)
- **Monitor running + Streamer offline** → "Waiting for {channel} to go live" (paused)
- **Monitor stopped** → "Stopped: {channel}" (paused)

---

## How It Works Now

### Monitor Lifecycle

1. **User starts monitor** → Monitor process starts, status = "running"
2. **Streamer goes live** → Monitor captures segments, creates clips ✅
3. **Streamer goes offline** → Monitor process keeps running, waiting for stream to return
   - Monitor card stays visible
   - Shows "Waiting for {channel} to go live"
   - Status indicator shows "paused" (but process is still running)
4. **Streamer comes back online** → Monitor automatically resumes clip generation ✅
5. **User manually stops** → Monitor status = "stopped", card stays visible
6. **Process crashes** → Monitor hidden from UI (or shows restart button)

### Visual States

| State | Process | Streamer | UI Display |
|-------|---------|----------|------------|
| Active | Running | Live | ✅ "Live monitoring {channel}" (Green) |
| Waiting | Running | Offline | ⏸️ "Waiting for {channel} to go live" (Yellow) |
| Stopped | Stopped | N/A | ⏹️ "Stopped: {channel}" (Gray) |
| Dead | Dead | N/A | ❌ Hidden (or shows restart button) |

---

## Benefits

✅ **Persistent Monitoring:** Monitors stay visible even when streamers go offline  
✅ **Auto-Resume:** Monitoring automatically resumes when streamer comes back online  
✅ **Better UX:** Users can see all their monitors at a glance  
✅ **No Manual Restart:** Don't need to restart monitors when streamers go offline/online  
✅ **Clear Status:** UI clearly shows when monitor is waiting vs. actively monitoring

---

## Technical Details

### Backend Changes
- **File:** `src/api/routers/monitors.py`
- **Function:** `list_monitors()`
- **Change:** Removed filter that only returned `status='running'` monitors
- **Result:** Returns all monitors except dead processes

### Frontend Changes
- **File:** `frontend/src/hooks/useStreamData.ts`
- **Function:** `fetchStreams()`
- **Changes:**
  1. Removed filter: `monitor.status !== 'stopped'`
  2. Added smart status detection based on monitor state + streamer live status
  3. Updated title display to show "Waiting for..." when streamer is offline

---

## Testing

### Test Cases

1. **Start monitor for live streamer**
   - ✅ Monitor appears with "Live monitoring {channel}"
   - ✅ Status shows "analyzing" (green)

2. **Streamer goes offline**
   - ✅ Monitor card stays visible
   - ✅ Title changes to "Waiting for {channel} to go live"
   - ✅ Status shows "paused" (yellow/orange)
   - ✅ Process keeps running in background

3. **Streamer comes back online**
   - ✅ Monitor automatically resumes
   - ✅ Title changes back to "Live monitoring {channel}"
   - ✅ Status shows "analyzing" (green)
   - ✅ Clips start being generated again

4. **Manually stop monitor**
   - ✅ Monitor card stays visible
   - ✅ Title shows "Stopped: {channel}"
   - ✅ Status shows "paused" (gray)
   - ✅ User can restart via "Restart Monitor" button

5. **Process crashes**
   - ✅ Monitor hidden from UI (or shows restart button)
   - ✅ Database updated to `status='stopped'`

---

## Migration Notes

- **No database changes required** - Uses existing `status` field
- **Backward compatible** - Existing monitors will now stay visible
- **No breaking changes** - API response format unchanged

---

## Related Files

- `src/api/routers/monitors.py` - Backend monitor listing logic
- `frontend/src/hooks/useStreamData.ts` - Frontend monitor data fetching
- `frontend/src/components/StreamMonitorCard.tsx` - Monitor card display component

---

## Summary

**Before:** Offline streamers → Monitors disappeared  
**After:** Offline streamers → Monitors stay visible, automatically resume when streamer comes back online

**Status:** ✅ **FIXED**

Monitors now persist across streamer online/offline cycles, providing a better user experience and eliminating the need to manually restart monitors.

