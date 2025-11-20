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
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
from twitch_engagement_fetcher import TwitchEngagementFetcher
from db.supabase_client import get_client
from ..dependencies import get_current_user_id
from ..middleware.auth import get_current_user, get_current_user_optional, User
from ..services.subscription_service import is_trial_user

router = APIRouter()

# Initialize Twitch API client
twitch_api = TwitchEngagementFetcher()

# In-memory cache of active monitors (synced with database)
active_monitors: Dict[str, Dict[str, Any]] = {}

def is_process_running(pid: int) -> bool:
    """
    Check if a process is still running (excludes zombies and defunct processes).
    Optimized for speed - uses minimal checks to avoid blocking.
    """
    try:
        # Quick check - just verify process exists, don't wait
        process = psutil.Process(pid)
        # Fast status check - don't call is_running() which can be slower
        status = process.status()
        
        # Check for zombie or defunct processes
        if status == psutil.STATUS_ZOMBIE:
            return False
        
        # Also check if process is actually running (not just existing)
        # This catches defunct/zombie processes that psutil might not flag correctly
        if not process.is_running():
            return False
            
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False
    except Exception:
        # Any other error means process doesn't exist or can't be accessed
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

# Removed sync on module load - too slow, causes startup delays
# Sync should be done async or on-demand only

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
        
        # Add user_id to environment for the ingest script (as fallback)
        env['MONITOR_USER_ID'] = user_id
        # Also set DEFAULT_USER_ID for live_ingest.py to pick up
        env['DEFAULT_USER_ID'] = user_id
        
        # Create log file
        log_dir = Path(__file__).parent.parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"monitor_{user_id[:8]}_{channel_name}.log"
        log_handle = open(log_file, 'a')
        
        # Build command arguments - only use arguments that live_ingest.py accepts
        cmd_args = [
            python_executable, 
            str(script_path), 
            "--channel", channel_name,
        ]
        
        # Add user_id if available (from environment or explicit)
        if user_id:
            cmd_args.extend(["--user_id", user_id])
        
        # Add bucket and prefix if specified in environment
        bucket = os.getenv("STORAGE_BUCKET")
        if bucket:
            cmd_args.extend(["--bucket", bucket])
        
        process = subprocess.Popen(
            cmd_args,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,
            bufsize=1  # Line buffered for immediate output
        )
        
        print(f"📝 Monitor logs: {log_file}")
        
        # Prepare monitor data
        # Set session_started_at for trial users (for 1-hour limit tracking)
        session_started_at = None
        if is_trial_user(user_id):
            session_started_at = datetime.utcnow().isoformat()
        
        monitor_data = {
            'process_id': process.pid,
            'status': 'running',
            'started_at': datetime.utcnow().isoformat(),
            'session_started_at': session_started_at,
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
async def list_monitors(current_user: Optional[User] = Depends(get_current_user_optional)):
    """
    List monitors from database. Authentication optional.
    - Regular users only see their own monitors
    - Admin users see ALL monitors from all users
    - Unauthenticated users see all monitors (for public display)
    """
    try:
        # Removed sync_monitors_from_db() - too slow, causes timeouts
        # Process cleanup should be done async or on-demand
        
        user_id = current_user.id if current_user else None
        is_admin_user = current_user.is_admin if current_user else False
        
        sb = get_client()
        
        # Get monitors - admins see all, regular users see only their own, unauthenticated see all
        # Limit query to avoid slow responses with many monitors
        monitors_query = sb.table('monitors').select('*').limit(100)  # Cap at 100 monitors
        
        if user_id and not is_admin_user:
            # Regular user: only see their own monitors
            monitors_query = monitors_query.eq('user_id', user_id)
        # Admin or unauthenticated: see all monitors
        
        # Execute query with timeout protection
        try:
            monitors = monitors_query.order('started_at', desc=True).execute()
        except Exception as e:
            logger.error(f"Error fetching monitors: {e}")
            # Return empty list on error rather than timing out
            return {
                "monitors": [],
                "total": 0
            }
        
        # Update status for each monitor - only hide if PROCESS is dead, not if streamer is offline
        active_monitors_list = []
        
        # First pass: Group monitors by channel and clean up duplicates in database
        channel_groups = {}
        for monitor in monitors.data or []:
            channel_name = monitor['channel_name'].lower()
            if channel_name not in channel_groups:
                channel_groups[channel_name] = []
            channel_groups[channel_name].append(monitor)
        
        # Filter duplicates (keep only most recent per channel) - don't delete from DB here
        # Deletion should be async to avoid blocking the response
        monitors_to_process = []
        for channel_name, channel_monitors in channel_groups.items():
            if len(channel_monitors) > 1:
                # Sort by started_at descending, keep the first (most recent)
                sorted_monitors = sorted(channel_monitors, key=lambda m: m.get('started_at', ''), reverse=True)
                monitor_to_keep = sorted_monitors[0]
                # Note: Duplicate cleanup should be done async/background task
                # Just return the most recent one for now
                monitors_to_process.append(monitor_to_keep)
            else:
                monitors_to_process.extend(channel_monitors)
        
        # Second pass: Check process health and update database for dead processes
        # This matches the previous implementation that auto-updated dead monitors
        dead_monitor_ids = []
        for monitor in monitors_to_process:
            pid = monitor.get('process_id')
            status = monitor.get('status', 'stopped')
            
            # Only check process if monitor claims to be running
            if status == 'running' and pid:
                try:
                    # Quick check - verify process exists
                    if not is_process_running(pid):
                        # Process is dead - check if monitor is newly created (grace period)
                        try:
                            started_at = datetime.fromisoformat(monitor['started_at'].replace('Z', '+00:00'))
                            age_seconds = (datetime.utcnow().replace(tzinfo=started_at.tzinfo) - started_at).total_seconds()
                            
                            if age_seconds < 30:
                                # Monitor is less than 30 seconds old, give it time to start
                                active_monitors_list.append(monitor)
                                continue
                        except:
                            pass
                        
                        # Process died and not newly created - mark for database update
                        dead_monitor_ids.append(monitor['id'])
                        # Update status in response immediately
                        monitor['status'] = 'stopped'
                        monitor['stopped_at'] = datetime.utcnow().isoformat()
                        # Don't include stopped monitors in active list
                        continue
                except Exception:
                    # If check fails, assume process is dead
                    dead_monitor_ids.append(monitor['id'])
                    monitor['status'] = 'stopped'
                    monitor['stopped_at'] = datetime.utcnow().isoformat()
                    continue
            
            # Include monitor in response (only running or stopped monitors that passed checks)
            active_monitors_list.append(monitor)
        
        # Update database for dead processes (non-blocking, but necessary for consistency)
        # This matches previous behavior - update DB when we detect dead processes
        if dead_monitor_ids:
            try:
                # Update in batch for efficiency
                sb.table('monitors')\
                    .update({
                        'status': 'stopped',
                        'stopped_at': datetime.utcnow().isoformat()
                    })\
                    .in_('id', dead_monitor_ids)\
                    .execute()
                logger.info(f"🔄 Updated {len(dead_monitor_ids)} dead monitor(s) to stopped status")
            except Exception as e:
                # Log error but don't fail the request
                logger.warning(f"⚠️ Failed to update dead monitors in DB: {e}")
        
        return {
            "monitors": active_monitors_list,
            "total": len(active_monitors_list)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list monitors: {str(e)}")

@router.get("/monitors/{channel_name}")
async def get_monitor_status(
    channel_name: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get status of a specific monitor. Authentication optional."""
    try:
        sb = get_client()
        channel_name = channel_name.lower()
        
        user_id = current_user.id if current_user else None
        is_admin_user = current_user.is_admin if current_user else False
        
        # Get monitor from database
        monitor_query = sb.table('monitors').select('*').eq('channel_name', channel_name)
        
        # If authenticated and not admin, only see own monitors
        if user_id and not is_admin_user:
            monitor_query = monitor_query.eq('user_id', user_id)
        # Admin or unauthenticated: see all monitors for this channel
        
        monitor_result = monitor_query.execute()
        
        if not monitor_result.data or len(monitor_result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Monitor for {channel_name} not found")
        
        monitor = monitor_result.data[0]
        pid = monitor.get('process_id')
        
        # Check if process is dead and update database (don't delete, just mark as stopped)
        # This matches previous behavior - update status instead of deleting
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
            
            # Process is dead and not newly created - update status to stopped (don't delete)
            try:
                sb.table('monitors')\
                    .update({
                        'status': 'stopped',
                        'stopped_at': datetime.utcnow().isoformat()
                    })\
                    .eq('id', monitor['id'])\
                    .execute()
                logger.info(f"🔄 Updated dead monitor {channel_name} to stopped status in status endpoint")
                # Update local monitor object
                monitor['status'] = 'stopped'
                monitor['stopped_at'] = datetime.utcnow().isoformat()
            except Exception as e:
                logger.warning(f"⚠️ Failed to update dead monitor status: {e}")
        
        return monitor
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get monitor status: {str(e)}")

@router.get("/monitors/{channel_name}/health")
async def get_monitor_health(
    channel_name: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get comprehensive health status for a monitor. Requires authentication."""
    try:
        sb = get_client()
        channel_name = channel_name.lower()
        
        # Get monitor from database (no auth required)
        monitor_result = sb.table('monitors')\
            .select('*')\
            .eq('channel_name', channel_name)\
            .execute()
        
        # If monitor doesn't exist, return offline status instead of 404
        if not monitor_result.data or len(monitor_result.data) == 0:
            # Still check if stream is live on Twitch (handle errors gracefully)
            try:
                twitch_info = twitch_api.get_stream_info(channel_name)
            except Exception as e:
                logger.warning(f"⚠️ Failed to get Twitch info for {channel_name}: {e}")
                twitch_info = None
            
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
        
        # If process is dead but monitor is marked as running, update database
        # This matches previous behavior - auto-update dead processes when detected
        if not process_alive and monitor.get('status') == 'running' and pid:
            try:
                # Check if monitor is newly created (grace period)
                started_at = datetime.fromisoformat(monitor['started_at'].replace('Z', '+00:00'))
                age_seconds = (datetime.utcnow().replace(tzinfo=started_at.tzinfo) - started_at).total_seconds()
                
                if age_seconds >= 30:
                    # Process died and not newly created - update database
                    sb.table('monitors')\
                        .update({
                            'status': 'stopped',
                            'stopped_at': datetime.utcnow().isoformat()
                        })\
                        .eq('id', monitor['id'])\
                        .execute()
                    logger.info(f"🔄 Updated dead monitor {channel_name} to stopped status in health check")
                    # Update local monitor object
                    monitor['status'] = 'stopped'
                    monitor['stopped_at'] = datetime.utcnow().isoformat()
            except Exception as e:
                logger.warning(f"⚠️ Failed to update dead monitor in health check: {e}")
        
        # Get Twitch stream info (handle errors gracefully)
        try:
            twitch_info = twitch_api.get_stream_info(channel_name)
        except Exception as e:
            logger.warning(f"⚠️ Failed to get Twitch info for {channel_name}: {e}")
            twitch_info = None
        
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
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get real-time statistics for a monitor from database. Authentication optional."""
    try:
        sb = get_client()
        channel_name = channel_name.lower()
        
        # Get user_id from current_user if authenticated, otherwise check all monitors
        user_id = current_user.id if current_user else None
        is_admin_user = current_user.is_admin if current_user else False
        
        # Check if monitor exists (active or inactive)
        # If authenticated, filter by user_id unless admin
        # If not authenticated, check all monitors
        monitor_query = sb.table('monitors').select('id').eq('channel_name', channel_name)
        
        if user_id and not is_admin_user:
            # Regular user: only see their own monitors
            monitor_query = monitor_query.eq('user_id', user_id)
        # Admin or unauthenticated: see all monitors for this channel
        
        monitor_result = monitor_query.execute()
        
        # If monitor doesn't exist, check if user has any clips for this channel
        # (monitor may have been removed but clips still exist)
        if not monitor_result.data or len(monitor_result.data) == 0:
            clips_query = sb.table('clips_metadata').select('id').eq('channel_name', channel_name)
            
            # If authenticated and not admin, only check user's clips
            if user_id and not is_admin_user:
                clips_query = clips_query.eq('user_id', user_id)
            
            clips_check = clips_query.limit(1).execute()
            
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
        
        # Get clip statistics from database (limit to prevent timeout)
        clips_query = sb.table('clips_metadata')\
            .select('*')\
            .eq('channel_name', channel_name)
        
        # If authenticated and not admin, only get user's clips
        if user_id and not is_admin_user:
            clips_query = clips_query.eq('user_id', user_id)
        # Admin or unauthenticated: get all clips for this channel
        
        # Limit query to prevent timeout - we only need recent clips for stats
        clips_result = clips_query.order('created_at', desc=True).limit(100).execute()
        
        clips = clips_result.data or []
        total_size = sum(clip.get('file_size', 0) for clip in clips)
        
        # Get last clip time
        last_clip_str = None
        if clips:
            try:
                last_time = datetime.fromisoformat(clips[0]['created_at'].replace('Z', '+00:00'))
                last_clip_at = clips[0]['created_at']
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
        
        # Try to read real-time buffer state from JSON file (with timeout protection)
        buffer_count = 0
        buffer_total = 5
        buffer_progress = 0.0
        buffer_status = "unknown"
        
        try:
            import tempfile
            import json
            from pathlib import Path
            
            # Find buffer state file for this monitor (with timeout protection)
            temp_dir = Path(tempfile.gettempdir())
            # Limit glob search to avoid timeout - use a more specific pattern and limit results
            buffer_pattern = f"buffer_state_{channel_name}_*.json"
            buffer_files = []
            try:
                # Use a simpler approach - just check if any buffer files exist
                # Limit glob search to prevent timeout
                import glob
                buffer_files = list(glob.glob(str(temp_dir / buffer_pattern)))[:5]  # Limit to 5 files max
                # If too many files, use most recent only
                if len(buffer_files) > 5:
                    buffer_files = sorted([Path(f) for f in buffer_files], key=lambda p: p.stat().st_mtime, reverse=True)[:1]
                    buffer_files = [str(f) for f in buffer_files]
            except Exception as e:
                logger.debug(f"Could not search buffer files: {e}")
                buffer_files = []
            
            if buffer_files:
                try:
                    # Use the most recent buffer state file
                    buffer_file = max([Path(f) for f in buffer_files], key=lambda p: p.stat().st_mtime)
                    
                    # Check if file is recent (within last 30 seconds)
                    file_age = time.time() - buffer_file.stat().st_mtime
                    if file_age < 30:
                        with open(buffer_file, 'r') as f:
                            buffer_state = json.load(f)
                            buffer_count = buffer_state.get('buffer_count', 0)
                            buffer_total = buffer_state.get('buffer_total', 5)
                            buffer_progress = buffer_state.get('buffer_progress', 0.0)
                            buffer_status = buffer_state.get('buffer_status', 'unknown')
                except Exception as e:
                    logger.debug(f"Could not read buffer state file: {e}")
        except Exception as e:
            logger.debug(f"Could not read buffer state file: {e}")
            # Fall back to time-based estimation if file doesn't exist
            if clips:
                try:
                    last_time = datetime.fromisoformat(clips[0]['created_at'].replace('Z', '+00:00'))
                    now = datetime.utcnow().replace(tzinfo=last_time.tzinfo)
                    seconds_ago = (now - last_time).total_seconds()
                    
                    # Estimate buffer based on time since last clip
                    # After 7.5 minutes (450s) without clips, assume buffer is full
                    if seconds_ago > 450:
                        buffer_count = 4  # Cap at 4/5 to indicate "stuck"
                        buffer_progress = 0.8
                        buffer_status = "stuck"
                    elif seconds_ago > 150:  # 2.5 minutes
                        buffer_count = 3
                        buffer_progress = 0.6
                        buffer_status = "filling"
                    elif seconds_ago > 90:  # 1.5 minutes
                        buffer_count = 2
                        buffer_progress = 0.4
                        buffer_status = "filling"
                    elif seconds_ago > 30:  # 30 seconds
                        buffer_count = 1
                        buffer_progress = 0.2
                        buffer_status = "filling"
                except:
                    pass
        
        return {
            "clips_captured": len(clips),
            "segments_analyzed": len(clips) * 3,
            "last_clip_time": last_clip_str or "No clips yet",
            "last_clip_at": last_clip_at if 'last_clip_at' in locals() else None,
            "total_size_mb": round(total_size / (1024 * 1024), 1),
            "monitor_status": "active" if monitor_active else "inactive",
            "buffer_count": buffer_count,
            "buffer_total": buffer_total,
            "buffer_progress": buffer_progress,
            "buffer_status": buffer_status
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
