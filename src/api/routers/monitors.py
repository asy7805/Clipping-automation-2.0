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
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and 'live_ingest.py' in ' '.join(cmdline):
                    if '--channel' in cmdline:
                        channel_idx = cmdline.index('--channel')
                        if channel_idx + 1 < len(cmdline):
                            channel_name = cmdline[channel_idx + 1].lower()
                            running_pids[channel_name] = proc.pid
            except (psutil.NoSuchProcess, psutil.AccessDenied, IndexError):
                continue
        
        # Update cache and database
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
                # Process not running, mark as stopped in database
                sb.table('monitors')\
                    .update({
                        'status': 'stopped',
                        'stopped_at': datetime.utcnow().isoformat()
                    })\
                    .eq('id', monitor['id'])\
                    .execute()
        
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

def is_process_running(pid: int) -> bool:
    """Check if a process is still running (excludes zombies)."""
    try:
        process = psutil.Process(pid)
        if process.status() == psutil.STATUS_ZOMBIE:
            return False
        return process.is_running()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False

@router.post("/monitors/start", response_model=MonitorResponse)
async def start_monitor(
    request: StartMonitorRequest,
    user_id: str = Depends(get_current_user_id)
) -> MonitorResponse:
    """
    Start monitoring a Twitch stream.
    Requires authentication.
    """
    try:
        sb = get_client()
        
        # Extract channel name from URL
        channel_name = extract_channel_from_url(request.twitch_url)
        
        # Check if this user is already monitoring this channel
        existing = sb.table('monitors')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('channel_name', channel_name)\
            .eq('status', 'running')\
            .execute()
        
        if existing.data and len(existing.data) > 0:
            monitor = existing.data[0]
            if is_process_running(monitor.get('process_id', 0)):
                return MonitorResponse(
                    id=str(monitor['id']),
                    channel_name=channel_name,
                    status="already_running",
                    started_at=monitor['started_at'],
                    process_id=monitor.get('process_id'),
                    message=f"Already monitoring {channel_name}"
                )
        
        # Start the monitoring process
        script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "live_ingest.py"
        python_executable = sys.executable
        env = os.environ.copy()
        
        # Add user_id to environment for the ingest script
        env['MONITOR_USER_ID'] = user_id
        
        # Create log file
        log_dir = Path(__file__).parent.parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"monitor_{user_id[:8]}_{channel_name}.log"
        log_handle = open(log_file, 'a')
        
        process = subprocess.Popen(
            [python_executable, str(script_path), "--channel", channel_name],
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True
        )
        
        print(f"📝 Monitor logs: {log_file}")
        
        # Save to database
        monitor_data = {
            'user_id': user_id,
            'channel_name': channel_name,
            'process_id': process.pid,
            'status': 'running',
            'started_at': datetime.utcnow().isoformat()
        }
        
        result = sb.table('monitors').insert(monitor_data).execute()
        
        if result.data and len(result.data) > 0:
            monitor = result.data[0]
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
        
        # Get monitor from database (user-specific)
        monitor_result = sb.table('monitors')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('channel_name', channel_name)\
            .eq('status', 'running')\
            .execute()
        
        if not monitor_result.data or len(monitor_result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Monitor for {channel_name} not found")
        
        monitor = monitor_result.data[0]
        pid = monitor.get('process_id')
        
        if pid and is_process_running(pid):
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        
        # Update database
        sb.table('monitors')\
            .update({
                'status': 'stopped',
                'stopped_at': datetime.utcnow().isoformat()
            })\
            .eq('id', monitor['id'])\
            .execute()
        
        # Remove from cache
        if channel_name in active_monitors:
            del active_monitors[channel_name]
        
        return {
            "status": "stopped",
            "channel_name": channel_name,
            "message": f"Successfully stopped monitoring {channel_name}"
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
        
        # Update status for each monitor
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
        
        return {
            "monitors": monitors.data or [],
            "total": len(monitors.data) if monitors.data else 0
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
        
        # Update status if process is not running
        if monitor['status'] == 'running' and pid and not is_process_running(pid):
            monitor['status'] = 'stopped'
            sb.table('monitors')\
                .update({'status': 'stopped', 'stopped_at': datetime.utcnow().isoformat()})\
                .eq('id', monitor['id'])\
                .execute()
        
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
        
        if not monitor_result.data or len(monitor_result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Monitor for {channel_name} not found")
        
        monitor = monitor_result.data[0]
        pid = monitor.get('process_id')
        
        # Check process health
        process_alive = is_process_running(pid) if pid else False
        
        # Get Twitch stream info
        twitch_info = twitch_api.get_stream_info(channel_name)
        
        # Get system metrics
        cpu_percent = 0.0
        memory_mb = 0.0
        
        if pid and process_alive:
            try:
                process = psutil.Process(pid)
                if process.status() != psutil.STATUS_ZOMBIE:
                    cpu_percent = process.cpu_percent(interval=0.1)
                    memory_mb = process.memory_info().rss / (1024 * 1024)
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
        if cpu_percent > 80:
            warnings.append(f"High CPU usage: {cpu_percent}%")
        if memory_mb > 1000:
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
            "cpu_percent": round(cpu_percent, 1),
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
        
        # Verify user owns this monitor
        monitor_result = sb.table('monitors')\
            .select('id')\
            .eq('user_id', user_id)\
            .eq('channel_name', channel_name)\
            .execute()
        
        if not monitor_result.data or len(monitor_result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Monitor for {channel_name} not found")
        
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
        
        return {
            "clips_captured": len(clips),
            "segments_analyzed": len(clips) * 3,
            "last_clip_time": last_clip_str,
            "total_size_mb": round(total_size / (1024 * 1024), 1)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting stats for {channel_name}: {e}")
        return {
            "clips_captured": 0,
            "segments_analyzed": 0,
            "last_clip_time": None,
            "total_size_mb": 0
        }
