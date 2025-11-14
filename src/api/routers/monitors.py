"""
Monitor management endpoints for starting/stopping stream monitors.
Now uses database for persistence and requires authentication.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import subprocess
import os
import signal
import psutil
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
from twitch_engagement_fetcher import TwitchEngagementFetcher
from db.supabase_client import get_client
from ..dependencies import get_current_user_id
from ..middleware.auth import get_current_user, User

router = APIRouter()

# Initialize Twitch API client
twitch_api = TwitchEngagementFetcher()

# In-memory cache of active monitors (synced with database)
active_monitors: Dict[str, Dict[str, Any]] = {}

def is_process_running(pid: int) -> bool:
    """Check if a process is still running (excludes zombies)."""
    try:
        process = psutil.Process(pid)
        if process.status() == psutil.STATUS_ZOMBIE:
            return False
        return process.is_running()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False

def sync_monitors_from_db():
    """
    Sync in-memory monitor cache with database.
    Discovers running processes and updates database accordingly.
    """
    try:
        sb = get_client()
        
        # Get all monitors from database
        db_monitors = sb.table('monitors')\
            .select('*')\
            .eq('status', 'running')\
            .execute()
        
        # Discover running processes
        running_pids = {}
        valid_pids = set()
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and 'live_ingest.py' in ' '.join(cmdline):
                    if '--channel' in cmdline:
                        channel_idx = cmdline.index('--channel')
                        if channel_idx + 1 < len(cmdline):
                            channel_name = cmdline[channel_idx + 1].lower()
                            pid = proc.pid
                            running_pids[channel_name] = pid
                            valid_pids.add(pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied, IndexError):
                continue
        
        # Get all valid PIDs from database
        db_pids = set()
        for monitor in db_monitors.data or []:
            pid = monitor.get('process_id')
            if pid:
                db_pids.add(pid)
        
        # Kill orphaned processes (running but not in database)
        orphaned_pids = valid_pids - db_pids
        for pid in orphaned_pids:
            try:
                process = psutil.Process(pid)
                print(f"⚠️ Killing orphaned process PID {pid} (not in database)")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except psutil.TimeoutExpired:
                    process.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Also kill orphaned FFmpeg processes (whose parent Python process is not in database)
        for proc in psutil.process_iter(['pid', 'name', 'ppid', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                name = proc.info.get('name', '').lower()
                if 'ffmpeg' in name and 'seg_' in ' '.join(cmdline):
                    ppid = proc.info.get('ppid')
                    # Check if parent is a valid monitor process
                    if ppid and ppid not in db_pids:
                        try:
                            parent = psutil.Process(ppid)
                            parent_cmd = ' '.join(parent.cmdline()) if parent.cmdline() else ''
                            if 'live_ingest' in parent_cmd:
                                print(f"⚠️ Killing orphaned FFmpeg PID {proc.pid} (parent PID {ppid} not in database)")
                                proc.terminate()
                                try:
                                    proc.wait(timeout=2)
                                except psutil.TimeoutExpired:
                                    proc.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            # Parent already dead, kill this FFmpeg
                            try:
                                print(f"⚠️ Killing orphaned FFmpeg PID {proc.pid} (parent dead)")
                                proc.terminate()
                                try:
                                    proc.wait(timeout=2)
                                except psutil.TimeoutExpired:
                                    proc.kill()
                            except:
                                pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Update cache and database
        dead_monitor_ids = []
        for monitor in db_monitors.data or []:
            channel = monitor['channel_name']
            process_id = monitor.get('process_id')
            
            # Check if process is actually running
            if process_id and is_process_running(process_id):
                # Process is running, add to cache
                active_monitors[channel] = monitor
            elif channel in running_pids:
                # Found running process, update database with new PID
                new_pid = running_pids[channel]
                sb.table('monitors')\
                    .update({'process_id': new_pid})\
                    .eq('id', monitor['id'])\
                    .execute()
                monitor['process_id'] = new_pid
                active_monitors[channel] = monitor
            else:
                # Process not running - but check if monitor is newly created
                # Give new monitors a 30 second grace period to start up
                try:
                    started_at = datetime.fromisoformat(monitor['started_at'].replace('Z', '+00:00'))
                    age_seconds = (datetime.utcnow().replace(tzinfo=started_at.tzinfo) - started_at).total_seconds()
                    
                    if age_seconds < 30:
                        # Monitor is less than 30 seconds old, give it time to start
                        active_monitors[channel] = monitor
                        continue
                except:
                    pass
                
                # Process not running and not newly created - delete from database (zombie cleanup)
                dead_monitor_ids.append(monitor['id'])
        
        # Delete dead monitors from database
        if dead_monitor_ids:
            sb.table('monitors')\
                .delete()\
                .in_('id', dead_monitor_ids)\
                .execute()
            print(f"🗑️ Deleted {len(dead_monitor_ids)} dead monitor(s) during sync")
        
        return len(active_monitors)
    except Exception as e:
        print(f"Error syncing monitors from DB: {e}")
        return 0

# Sync on module load
synced_count = sync_monitors_from_db()
if synced_count > 0:
    print(f"🔄 Synced {synced_count} monitor(s) from database")

class StartMonitorRequest(BaseModel):
    """Request model for starting a monitor."""
    twitch_url: str

class MonitorResponse(BaseModel):
    """Response model for monitor status."""
    id: str
    channel_name: str
    status: str
    started_at: str
    process_id: Optional[int] = None
    message: str

def extract_channel_from_url(url: str) -> str:
    """Extract Twitch channel name from URL."""
    url = url.strip().lower()
    
    # Remove protocol
    if url.startswith('http://') or url.startswith('https://'):
        url = url.split('://', 1)[1]
    
    # Remove www.
    if url.startswith('www.'):
        url = url[4:]
    
    # Remove twitch.tv/
    if url.startswith('twitch.tv/'):
        url = url[10:]
    
    # Remove any trailing slashes or query parameters
    url = url.split('?')[0].split('/')[0].strip('/')
    
    if not url or len(url) < 2:
        raise ValueError("Invalid Twitch channel name")
    
    return url

@router.post("/monitors/start", response_model=MonitorResponse)
async def start_monitor(
    request: StartMonitorRequest,
    current_user: User = Depends(get_current_user)
) -> MonitorResponse:
    """
    Start monitoring a Twitch stream.
    Requires authentication.
    - Regular users can only monitor ONE stream at a time
    - Admin users can monitor multiple streams
    """
    try:
        sb = get_client()
        user_id = current_user.id
        is_admin = current_user.is_admin
        
        # Extract channel name from URL
        channel_name = extract_channel_from_url(request.twitch_url)
        
        # Check if this user already has a monitor for this channel (any status)
        existing = sb.table('monitors')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('channel_name', channel_name)\
            .execute()
        
        # If multiple monitors exist for this channel, clean up duplicates
        # Keep only the most recent one (or the running one if any)
        if existing.data and len(existing.data) > 1:
            # Find the monitor to keep (prefer running, then most recent)
            monitors_to_keep = [m for m in existing.data if m['status'] == 'running' and is_process_running(m.get('process_id', 0))]
            if not monitors_to_keep:
                # No running monitors, keep the most recent one
                monitors_to_keep = [max(existing.data, key=lambda m: m.get('started_at', ''))]
            
            monitor_to_keep = monitors_to_keep[0]
            monitor_ids_to_delete = [m['id'] for m in existing.data if m['id'] != monitor_to_keep['id']]
            
            # Delete duplicate monitors
            if monitor_ids_to_delete:
                sb.table('monitors')\
                    .delete()\
                    .in_('id', monitor_ids_to_delete)\
                    .execute()
                print(f"🧹 Cleaned up {len(monitor_ids_to_delete)} duplicate monitor(s) for {channel_name}")
            
            # Update existing to only contain the monitor we're keeping
            existing.data = [monitor_to_keep]
        
        # If monitor exists and is running, check if process is actually running
        if existing.data and len(existing.data) > 0:
            monitor = existing.data[0]
            if monitor['status'] == 'running' and is_process_running(monitor.get('process_id', 0)):
                return MonitorResponse(
                    id=str(monitor['id']),
                    channel_name=channel_name,
                    status="already_running",
                    started_at=monitor['started_at'],
                    process_id=monitor.get('process_id'),
                    message=f"Already monitoring {channel_name}"
                )
            # If monitor exists but is stopped, we'll update it instead of inserting
        
        # For non-admin users: Check if they already have a running monitor
        if not is_admin:
            running_monitors = sb.table('monitors')\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('status', 'running')\
                .execute()
            
            # Check if any of the running monitors actually have a live process
            active_count = 0
            for monitor in running_monitors.data or []:
                pid = monitor.get('process_id')
                if pid and is_process_running(pid):
                    active_count += 1
            
            # If user already has an active monitor, prevent starting a new one
            if active_count > 0:
                raise HTTPException(
                    status_code=403,
                    detail="You can only monitor one stream at a time."
                )
        
        # Start the monitoring process
        script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "live_ingest.py"
        # Resolve to absolute path to avoid issues with working directory
        script_path = script_path.resolve()
        if not script_path.exists():
            raise FileNotFoundError(f"Monitoring script not found at {script_path}")
        python_executable = sys.executable
        env = os.environ.copy()
        
        # Add user_id to environment for the ingest script
        env['MONITOR_USER_ID'] = user_id
        
        # Create log file
        log_dir = Path(__file__).parent.parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"monitor_{user_id[:8]}_{channel_name}.log"
        log_handle = open(log_file, 'a')
        
        # Use optimized defaults: best quality and auto-detect encoder (will use hardware if available)
        # FFmpeg will downscale to 1280px width anyway, so we get "best" from Twitch then downscale
        process = subprocess.Popen(
            [
                python_executable, 
                str(script_path), 
                "--channel", channel_name,
                "--quality", "best",  # Get best available (will be downscaled by FFmpeg)
                "--encoder", "auto",  # Auto-detect best encoder (hardware if available)
            ],
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,
            bufsize=1  # Line buffered for immediate output
        )
        
        print(f"📝 Monitor logs: {log_file}")
        
        # Prepare monitor data
        monitor_data = {
            'process_id': process.pid,
            'status': 'running',
            'started_at': datetime.utcnow().isoformat(),
            'stopped_at': None  # Clear stopped_at if it exists
        }
        
        # If monitor exists (stopped), update it; otherwise insert new
        if existing.data and len(existing.data) > 0:
            # Update existing monitor
            monitor_id = existing.data[0]['id']
            result = sb.table('monitors')\
                .update(monitor_data)\
                .eq('id', monitor_id)\
                .execute()
            
            if result.data and len(result.data) > 0:
                monitor = result.data[0]
            else:
                # If update didn't return data, fetch it
                fetch_result = sb.table('monitors')\
                    .select('*')\
                    .eq('id', monitor_id)\
                    .execute()
                monitor = fetch_result.data[0] if fetch_result.data else None
        else:
            # Insert new monitor
            monitor_data['user_id'] = user_id
            monitor_data['channel_name'] = channel_name
            result = sb.table('monitors').insert(monitor_data).execute()
            monitor = result.data[0] if result.data and len(result.data) > 0 else None
        
        if monitor:
            active_monitors[channel_name] = monitor
            
            return MonitorResponse(
                id=str(monitor['id']),
                channel_name=channel_name,
                status="started",
                started_at=monitor['started_at'],
                process_id=process.pid,
                message=f"Successfully started monitoring {channel_name}"
            )
        else:
            raise Exception("Failed to save monitor to database")
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid Twitch URL: {str(e)}")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Monitoring script not found")
    except HTTPException:
        # Re-raise HTTPExceptions (like our 403 error) without modification
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start monitor: {str(e)}")

@router.post("/monitors/stop/{channel_name}")
async def stop_monitor(
    channel_name: str,
    user_id: str = Depends(get_current_user_id)
):
    """Stop monitoring a Twitch stream. Requires authentication."""
    try:
        sb = get_client()
        channel_name = channel_name.lower()
        
        # Get monitor from database (user-specific) - check all statuses, not just running
        # This allows stopping monitors that are already stopped (cleanup) or running
        monitor_result = sb.table('monitors')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('channel_name', channel_name)\
            .execute()
        
        if not monitor_result.data or len(monitor_result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Monitor for {channel_name} not found")
        
        # Collect monitor IDs to delete
        monitor_ids_to_delete = []
        
        # If multiple monitors exist, stop all of them (shouldn't happen after deduplication, but handle it)
        for monitor in monitor_result.data:
            pid = monitor.get('process_id')
            
            # Kill process if it's running
            if pid and is_process_running(pid):
                try:
                    os.kill(pid, signal.SIGTERM)
                    # Wait a moment for graceful shutdown
                    time.sleep(0.5)
                    # Force kill if still running
                    if is_process_running(pid):
                        os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    # Process already dead
                    pass
            
            # Collect monitor ID for deletion
            monitor_ids_to_delete.append(monitor['id'])
        
        # Delete monitors from database (not just mark as stopped)
        if monitor_ids_to_delete:
            sb.table('monitors')\
                .delete()\
                .in_('id', monitor_ids_to_delete)\
                .execute()
            print(f"🗑️ Deleted {len(monitor_ids_to_delete)} monitor(s) for {channel_name}")
        
        # Remove from cache
        if channel_name in active_monitors:
            del active_monitors[channel_name]
        
        return {
            "status": "stopped",
            "channel_name": channel_name,
            "message": f"Successfully stopped and removed monitoring for {channel_name}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop monitor: {str(e)}")

@router.get("/monitors")
async def list_monitors(current_user: User = Depends(get_current_user)):
    """
    List monitors from database. Requires authentication.
    - Regular users only see their own monitors
    - Admin users see ALL monitors from all users
    """
    try:
        # Sync monitors from DB first to detect dead processes
        sync_monitors_from_db()
        
        user_id = current_user.id
        is_admin = current_user.is_admin
        
        sb = get_client()
        
        # Get monitors - admins see all, regular users see only their own
        if is_admin:
            monitors = sb.table('monitors')\
                .select('*')\
                .order('started_at', desc=True)\
                .execute()
        else:
            monitors = sb.table('monitors')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('started_at', desc=True)\
                .execute()
        
        # Update status for each monitor - only hide if PROCESS is dead, not if streamer is offline
        active_monitors_list = []
        
        # First pass: Group monitors by channel and clean up duplicates in database
        channel_groups = {}
        for monitor in monitors.data or []:
            channel_name = monitor['channel_name'].lower()
            if channel_name not in channel_groups:
                channel_groups[channel_name] = []
            channel_groups[channel_name].append(monitor)
        
        # Delete duplicate monitors from database (keep only most recent per channel)
        monitors_to_process = []
        for channel_name, channel_monitors in channel_groups.items():
            if len(channel_monitors) > 1:
                # Sort by started_at descending, keep the first (most recent)
                sorted_monitors = sorted(channel_monitors, key=lambda m: m.get('started_at', ''), reverse=True)
                monitor_to_keep = sorted_monitors[0]
                duplicates_to_delete = [m['id'] for m in sorted_monitors[1:]]
                
                if duplicates_to_delete:
                    sb.table('monitors')\
                        .delete()\
                        .in_('id', duplicates_to_delete)\
                        .execute()
                    print(f"🧹 Cleaned up {len(duplicates_to_delete)} duplicate monitor(s) for {channel_name}")
                
                # Only process the monitor we kept
                monitors_to_process.append(monitor_to_keep)
            else:
                monitors_to_process.extend(channel_monitors)
        
        # Second pass: Process monitors and filter dead processes
        dead_monitor_ids = []
        for monitor in monitors_to_process:
            pid = monitor.get('process_id')
            
            # Check if process is actually running
            if monitor['status'] == 'running' and pid:
                if not is_process_running(pid):
                    # Check if monitor is newly created (grace period)
                    try:
                        started_at = datetime.fromisoformat(monitor['started_at'].replace('Z', '+00:00'))
                        age_seconds = (datetime.utcnow().replace(tzinfo=started_at.tzinfo) - started_at).total_seconds()
                        
                        if age_seconds < 30:
                            # Monitor is less than 30 seconds old, give it time to start
                            active_monitors_list.append(monitor)
                            continue
                    except:
                        pass
                    
                    # Process died and not newly created - delete from database instead of marking as stopped
                    dead_monitor_ids.append(monitor['id'])
                    continue
            
            # Include monitor (already deduplicated in first pass)
            active_monitors_list.append(monitor)
        
        # Delete dead processes from database
        if dead_monitor_ids:
            sb.table('monitors')\
                .delete()\
                .in_('id', dead_monitor_ids)\
                .execute()
            print(f"🗑️ Deleted {len(dead_monitor_ids)} dead monitor process(es)")
        
        return {
            "monitors": active_monitors_list,
            "total": len(active_monitors_list)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list monitors: {str(e)}")

@router.get("/monitors/{channel_name}")
async def get_monitor_status(
    channel_name: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get status of a specific monitor. Requires authentication."""
    try:
        sb = get_client()
        channel_name = channel_name.lower()
        
        # Get monitor from database (user-specific)
        monitor_result = sb.table('monitors')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('channel_name', channel_name)\
            .execute()
        
        if not monitor_result.data or len(monitor_result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Monitor for {channel_name} not found")
        
        monitor = monitor_result.data[0]
        pid = monitor.get('process_id')
        
        # Delete monitor if process is dead (zombie cleanup) - but with grace period for new monitors
        if monitor['status'] == 'running' and pid and not is_process_running(pid):
            # Check if monitor is newly created (grace period)
            try:
                started_at = datetime.fromisoformat(monitor['started_at'].replace('Z', '+00:00'))
                age_seconds = (datetime.utcnow().replace(tzinfo=started_at.tzinfo) - started_at).total_seconds()
                
                if age_seconds < 30:
                    # Monitor is less than 30 seconds old, give it time to start
                    return monitor
            except:
                pass
            
            # Process is dead and not newly created - delete it
            sb.table('monitors')\
                .delete()\
                .eq('id', monitor['id'])\
                .execute()
            raise HTTPException(status_code=404, detail=f"Monitor for {channel_name} not found (process died)")
        
        return monitor
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get monitor status: {str(e)}")

@router.get("/monitors/{channel_name}/health")
async def get_monitor_health(
    channel_name: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get comprehensive health status for a monitor. Requires authentication."""
    try:
        sb = get_client()
        channel_name = channel_name.lower()
        
        # Get monitor from database
        monitor_result = sb.table('monitors')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('channel_name', channel_name)\
            .execute()
        
        # If monitor doesn't exist, return offline status instead of 404
        if not monitor_result.data or len(monitor_result.data) == 0:
            # Still check if stream is live on Twitch
            twitch_info = twitch_api.get_stream_info(channel_name)
            return {
                "healthy": False,
                "process_alive": False,
                "is_live": twitch_info.get('is_live', False) if twitch_info else False,
                "viewer_count": twitch_info.get('viewer_count', 0) if twitch_info else 0,
                "stream_title": twitch_info.get('title', '') if twitch_info else '',
                "cpu_percent": 0.0,
                "memory_mb": 0.0,
                "total_cpu_percent": 0.0,
                "uptime": "Not running",
                "warnings": ["Monitor is not active"],
                "monitor_status": "inactive"
            }
        
        monitor = monitor_result.data[0]
        pid = monitor.get('process_id')
        
        # Check process health
        process_alive = is_process_running(pid) if pid else False
        
        # Get Twitch stream info
        twitch_info = twitch_api.get_stream_info(channel_name)
        
        # Get system metrics
        cpu_percent = 0.0
        memory_mb = 0.0
        total_cpu_percent = 0.0  # Include child processes (FFmpeg)
        
        if pid and process_alive:
            try:
                process = psutil.Process(pid)
                if process.status() != psutil.STATUS_ZOMBIE:
                    cpu_percent = process.cpu_percent(interval=0.1)
                    memory_mb = process.memory_info().rss / (1024 * 1024)
                    total_cpu_percent = cpu_percent
                    
                    # Add CPU from child processes (FFmpeg)
                    try:
                        children = process.children(recursive=True)
                        for child in children:
                            try:
                                total_cpu_percent += child.cpu_percent(interval=0.1)
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                    except:
                        pass
                else:
                    process_alive = False
            except (psutil.ZombieProcess, psutil.NoSuchProcess):
                process_alive = False
        
        # Calculate uptime
        try:
            started_at = datetime.fromisoformat(monitor['started_at'].replace('Z', '+00:00'))
            uptime_seconds = (datetime.utcnow().replace(tzinfo=started_at.tzinfo) - started_at).total_seconds()
        except:
            uptime_seconds = 0
        
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        uptime_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
        
        # Build warnings
        warnings = []
        if not process_alive:
            warnings.append("Process not running")
        if twitch_info and not twitch_info.get('is_live', False):
            warnings.append("Stream is offline")
        # Use total CPU (including FFmpeg child processes) for warning threshold
        # Video encoding can use high CPU, so threshold is higher (150% for multi-core)
        if total_cpu_percent > 150:
            warnings.append(f"Very high CPU usage: {total_cpu_percent:.1f}%")
        # Memory threshold increased for video processing (2GB is reasonable)
        if memory_mb > 2000:
            warnings.append(f"High memory usage: {memory_mb:.0f} MB")
        
        return {
            "process_alive": process_alive,
            "process_id": pid,
            "uptime": uptime_str,
            "uptime_seconds": int(uptime_seconds),
            "is_live": twitch_info.get('is_live', False) if twitch_info else False,
            "viewer_count": twitch_info.get('viewer_count', 0) if twitch_info else 0,
            "stream_title": twitch_info.get('title', '') if twitch_info else '',
            "game_name": twitch_info.get('game_name', '') if twitch_info else '',
            "thumbnail_url": twitch_info.get('thumbnail_url', '') if twitch_info else '',
            "stream_started_at": twitch_info.get('started_at', '') if twitch_info else '',
            "cpu_percent": round(total_cpu_percent, 1),  # Return total CPU including children
            "memory_mb": round(memory_mb, 1),
            "healthy": process_alive and (twitch_info.get('is_live', False) if twitch_info else True),
            "warnings": warnings
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get monitor health: {str(e)}")

@router.get("/monitors/{channel_name}/stats")
async def get_monitor_stats(
    channel_name: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get real-time statistics for a monitor from database. Requires authentication."""
    try:
        sb = get_client()
        channel_name = channel_name.lower()
        
        # Check if monitor exists (active or inactive)
        monitor_result = sb.table('monitors')\
            .select('id')\
            .eq('user_id', user_id)\
            .eq('channel_name', channel_name)\
            .execute()
        
        # If monitor doesn't exist, check if user has any clips for this channel
        # (monitor may have been removed but clips still exist)
        if not monitor_result.data or len(monitor_result.data) == 0:
            clips_check = sb.table('clips_metadata')\
                .select('id')\
                .eq('user_id', user_id)\
                .eq('channel_name', channel_name)\
                .limit(1)\
                .execute()
            
            # If no clips exist either, return empty stats instead of 404
            if not clips_check.data or len(clips_check.data) == 0:
                return {
                    "clips_captured": 0,
                    "segments_analyzed": 0,
                    "last_clip_time": "No clips yet",
                    "total_size_mb": 0,
                    "monitor_status": "inactive"
                }
            # Has clips but monitor is inactive, continue to show stats
        
        # Get clip statistics from database
        clips_result = sb.table('clips_metadata')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('channel_name', channel_name)\
            .order('created_at', desc=True)\
            .execute()
        
        clips = clips_result.data or []
        total_size = sum(clip.get('file_size', 0) for clip in clips)
        
        # Get last clip time
        last_clip_str = None
        if clips:
            try:
                last_time = datetime.fromisoformat(clips[0]['created_at'].replace('Z', '+00:00'))
                now = datetime.utcnow().replace(tzinfo=last_time.tzinfo)
                seconds_ago = (now - last_time).total_seconds()
                
                if seconds_ago < 60:
                    last_clip_str = f"{int(seconds_ago)}s ago"
                elif seconds_ago < 3600:
                    last_clip_str = f"{int(seconds_ago / 60)}m ago"
                elif seconds_ago < 86400:
                    last_clip_str = f"{int(seconds_ago / 3600)}h ago"
                else:
                    last_clip_str = f"{int(seconds_ago / 86400)}d ago"
            except:
                last_clip_str = "recently"
        
        monitor_active = bool(monitor_result.data and len(monitor_result.data) > 0)
        
        return {
            "clips_captured": len(clips),
            "segments_analyzed": len(clips) * 3,
            "last_clip_time": last_clip_str or "No clips yet",
            "total_size_mb": round(total_size / (1024 * 1024), 1),
            "monitor_status": "active" if monitor_active else "inactive"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting stats for {channel_name}: {e}")
        return {
            "clips_captured": 0,
            "segments_analyzed": 0,
            "last_clip_time": "Error loading stats",
            "total_size_mb": 0,
            "monitor_status": "error"
        }
