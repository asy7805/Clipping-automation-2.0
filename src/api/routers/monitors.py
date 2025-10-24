"""
Monitor management endpoints for starting/stopping stream monitors.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
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

router = APIRouter()

# Initialize Twitch API client
twitch_api = TwitchEngagementFetcher()

# In-memory store for active monitors (in production, use database)
active_monitors: Dict[str, Dict[str, Any]] = {}

def discover_running_monitors():
    """
    Discover and register any live_ingest.py processes that are already running.
    This helps restore monitors after API restart.
    """
    discovered = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline', [])
            if cmdline and 'live_ingest.py' in ' '.join(cmdline):
                # Extract channel name from command line
                if '--channel' in cmdline:
                    channel_idx = cmdline.index('--channel')
                    if channel_idx + 1 < len(cmdline):
                        channel_name = cmdline[channel_idx + 1].lower()
                        
                        # Check if not already registered
                        if channel_name not in active_monitors:
                            # Estimate start time from process creation time
                            create_time = datetime.fromtimestamp(proc.create_time())
                            
                            monitor_info = {
                                'channel_name': channel_name,
                                'process_id': proc.pid,
                                'started_at': create_time.isoformat(),
                                'user_id': None,
                                'status': 'running',
                                'rediscovered': True  # Mark as rediscovered
                            }
                            active_monitors[channel_name] = monitor_info
                            discovered.append(channel_name)
        except (psutil.NoSuchProcess, psutil.AccessDenied, IndexError):
            continue
    
    return discovered

# Discover running monitors on module load
discovered_channels = discover_running_monitors()
if discovered_channels:
    print(f"🔍 Discovered {len(discovered_channels)} running monitor(s): {', '.join(discovered_channels)}")

class StartMonitorRequest(BaseModel):
    """Request model for starting a monitor."""
    twitch_url: str
    user_id: Optional[str] = None

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
    # Handle various Twitch URL formats:
    # - https://www.twitch.tv/channelname
    # - https://twitch.tv/channelname
    # - twitch.tv/channelname
    # - channelname
    
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
        # Zombie processes are considered "not running" for our purposes
        if process.status() == psutil.STATUS_ZOMBIE:
            return False
        return process.is_running()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False

@router.post("/monitors/start", response_model=MonitorResponse)
async def start_monitor(request: StartMonitorRequest) -> MonitorResponse:
    """
    Start monitoring a Twitch stream.
    
    Args:
        request: Contains twitch_url and optional user_id
        
    Returns:
        Monitor status including process ID and start time
    """
    try:
        # Extract channel name from URL
        channel_name = extract_channel_from_url(request.twitch_url)
        
        # Check if already monitoring this channel
        if channel_name in active_monitors:
            monitor = active_monitors[channel_name]
            if is_process_running(monitor.get('process_id', 0)):
                return MonitorResponse(
                    id=channel_name,
                    channel_name=channel_name,
                    status="already_running",
                    started_at=monitor['started_at'],
                    process_id=monitor.get('process_id'),
                    message=f"Already monitoring {channel_name}"
                )
            else:
                # Process died, remove it
                del active_monitors[channel_name]
        
        # Start the monitoring process
        script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "live_ingest.py"
        
        # Use the same Python interpreter that's running this API (from .venv)
        python_executable = sys.executable
        
        # Start the process in the background with proper environment
        import os
        env = os.environ.copy()
        
        # Create log file for this monitor
        log_dir = Path(__file__).parent.parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"monitor_{channel_name}.log"
        log_handle = open(log_file, 'a')
        
        process = subprocess.Popen(
            [
                python_executable,
                str(script_path),
                "--channel", channel_name,
            ],
            stdout=log_handle,
            stderr=subprocess.STDOUT,  # Redirect stderr to stdout (log file)
            env=env,
            start_new_session=True  # Detach from parent
        )
        
        print(f"📝 Monitor logs: {log_file}")
        
        # Store monitor info
        monitor_info = {
            'channel_name': channel_name,
            'process_id': process.pid,
            'started_at': datetime.utcnow().isoformat(),
            'user_id': request.user_id,
            'status': 'running'
        }
        active_monitors[channel_name] = monitor_info
        
        return MonitorResponse(
            id=channel_name,
            channel_name=channel_name,
            status="started",
            started_at=monitor_info['started_at'],
            process_id=process.pid,
            message=f"Successfully started monitoring {channel_name}"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid Twitch URL: {str(e)}")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Monitoring script not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start monitor: {str(e)}")

@router.post("/monitors/stop/{channel_name}")
async def stop_monitor(channel_name: str):
    """
    Stop monitoring a Twitch stream.
    
    Args:
        channel_name: Name of the channel to stop monitoring
        
    Returns:
        Status message
    """
    channel_name = channel_name.lower()
    
    if channel_name not in active_monitors:
        raise HTTPException(status_code=404, detail=f"Monitor for {channel_name} not found")
    
    monitor = active_monitors[channel_name]
    pid = monitor.get('process_id')
    
    if pid and is_process_running(pid):
        try:
            # Send SIGTERM to gracefully stop the process
            os.kill(pid, signal.SIGTERM)
            del active_monitors[channel_name]
            return {
                "status": "stopped",
                "channel_name": channel_name,
                "message": f"Successfully stopped monitoring {channel_name}"
            }
        except ProcessLookupError:
            del active_monitors[channel_name]
            raise HTTPException(status_code=404, detail=f"Process {pid} not found")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to stop monitor: {str(e)}")
    else:
        del active_monitors[channel_name]
        raise HTTPException(status_code=404, detail=f"Process for {channel_name} is not running")

@router.get("/monitors")
async def list_monitors():
    """
    List all active monitors.
    
    Returns:
        List of active monitor information
    """
    # Rediscover any new monitors that might have been started
    discover_running_monitors()
    
    # Update status of monitors but DON'T delete them
    # Let the watchdog handle restarts, and only delete on manual stop
    for channel in list(active_monitors.keys()):
        monitor = active_monitors[channel]
        pid = monitor.get('process_id')
        if pid and not is_process_running(pid):
            # Mark as stopped but keep in list
            monitor['status'] = 'stopped'
            monitor['stopped_at'] = datetime.utcnow().isoformat()
            # Don't delete - let user see it failed and manually remove or let watchdog restart
    
    return {
        "monitors": list(active_monitors.values()),
        "total": len(active_monitors)
    }

@router.get("/monitors/{channel_name}")
async def get_monitor_status(channel_name: str):
    """
    Get status of a specific monitor.
    
    Args:
        channel_name: Name of the channel
        
    Returns:
        Monitor status
    """
    channel_name = channel_name.lower()
    
    if channel_name not in active_monitors:
        raise HTTPException(status_code=404, detail=f"Monitor for {channel_name} not found")
    
    monitor = active_monitors[channel_name]
    pid = monitor.get('process_id')
    
    # Update status if process is not running, but don't delete
    if pid and not is_process_running(pid):
        monitor['status'] = 'stopped'
        if 'stopped_at' not in monitor:
            monitor['stopped_at'] = datetime.utcnow().isoformat()
    
    return monitor

@router.get("/monitors/{channel_name}/health")
async def get_monitor_health(channel_name: str):
    """
    Get comprehensive health status for a monitor including Twitch stream data.
    
    Returns:
        Dict with process health, Twitch stream status, and system metrics
    """
    channel_name = channel_name.lower()
    
    # Check if monitor exists
    if channel_name not in active_monitors:
        raise HTTPException(status_code=404, detail=f"Monitor for {channel_name} not found")
    
    monitor = active_monitors[channel_name]
    pid = monitor.get('process_id')
    
    # Check process health
    process_alive = is_process_running(pid) if pid else False
    
    # Get Twitch stream info
    twitch_info = twitch_api.get_stream_info(channel_name)
    
    # Get system metrics if process is running
    cpu_percent = 0.0
    memory_mb = 0.0
    
    if pid and process_alive:
        try:
            process = psutil.Process(pid)
            
            # Double-check it's not a zombie
            if process.status() == psutil.STATUS_ZOMBIE:
                print(f"Process {pid} for {channel_name} is a zombie")
                process_alive = False
            else:
                cpu_percent = process.cpu_percent(interval=0.1)
                memory_mb = process.memory_info().rss / (1024 * 1024)
        except psutil.ZombieProcess as e:
            print(f"Process {pid} for {channel_name} is a zombie: {e}")
            process_alive = False
        except Exception as e:
            print(f"Error getting process metrics: {e}")
    
    # Calculate uptime
    try:
        started_at = datetime.fromisoformat(monitor['started_at'].replace('Z', '+00:00'))
        uptime_seconds = (datetime.utcnow().replace(tzinfo=started_at.tzinfo) - started_at).total_seconds()
    except:
        uptime_seconds = 0
    
    # Format uptime
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    uptime_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
    
    # Build warnings list
    warnings = []
    
    # Check if process became a zombie after initial check
    if pid and not process_alive:
        try:
            p = psutil.Process(pid)
            if p.status() == psutil.STATUS_ZOMBIE:
                warnings.append(f"Process is a zombie (PID {pid})")
            else:
                warnings.append("Process not running")
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            warnings.append("Process not running")
    elif not process_alive:
        warnings.append("Process not running")
        
    if twitch_info and not twitch_info.get('is_live', False):
        warnings.append("Stream is offline")
    if cpu_percent > 80:
        warnings.append(f"High CPU usage: {cpu_percent}%")
    if memory_mb > 1000:
        warnings.append(f"High memory usage: {memory_mb:.0f} MB")
    
    return {
        # Process health
        "process_alive": process_alive,
        "process_id": pid,
        "uptime": uptime_str,
        "uptime_seconds": int(uptime_seconds),
        
        # Twitch stream data
        "is_live": twitch_info.get('is_live', False) if twitch_info else False,
        "viewer_count": twitch_info.get('viewer_count', 0) if twitch_info else 0,
        "stream_title": twitch_info.get('title', '') if twitch_info else '',
        "game_name": twitch_info.get('game_name', '') if twitch_info else '',
        "thumbnail_url": twitch_info.get('thumbnail_url', '') if twitch_info else '',
        "stream_started_at": twitch_info.get('started_at', '') if twitch_info else '',
        
        # System metrics
        "cpu_percent": round(cpu_percent, 1),
        "memory_mb": round(memory_mb, 1),
        
        # Overall health status
        "healthy": process_alive and (twitch_info.get('is_live', False) if twitch_info else True),
        "warnings": warnings
    }

@router.get("/monitors/{channel_name}/stats")
async def get_monitor_stats(channel_name: str):
    """
    Get real-time statistics for a specific monitor.
    
    Args:
        channel_name: Name of the channel
        
    Returns:
        Statistics including clips captured, segments analyzed, etc.
    """
    from supabase import create_client
    import os
    
    channel_name = channel_name.lower()
    
    # Check if monitor exists
    if channel_name not in active_monitors:
        raise HTTPException(status_code=404, detail=f"Monitor for {channel_name} not found")
    
    try:
        # Create Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            return {
                "clips_captured": 0,
                "segments_analyzed": 0,
                "last_clip_time": None,
                "total_size_mb": 0
            }
        
        sb = create_client(supabase_url, supabase_key)
        
        # Count clips recursively in storage for this channel
        def count_clips_recursive(path="raw"):
            """Recursively count MP4 files for a channel"""
            try:
                items = sb.storage.from_("raw").list(path, {'limit': 1000})
                count = 0
                total_size = 0
                latest_time = None
                
                for item in items:
                    item_name = item.get('name', '')
                    
                    # If it's an MP4 file, count it
                    if item_name.endswith('.mp4'):
                        count += 1
                        size = item.get('metadata', {}).get('size', 0)
                        total_size += size
                        created = item.get('created_at') or item.get('metadata', {}).get('lastModified')
                        if created and (not latest_time or created > latest_time):
                            latest_time = created
                    
                    # If it's a folder, recurse
                    elif '.' not in item_name:
                        subfolder_path = f"{path}/{item_name}"
                        sub_count, sub_size, sub_time = count_clips_recursive(subfolder_path)
                        count += sub_count
                        total_size += sub_size
                        if sub_time and (not latest_time or sub_time > latest_time):
                            latest_time = sub_time
                
                return count, total_size, latest_time
            except Exception as e:
                print(f"Error counting clips in {path}: {e}")
                return 0, 0, None
        
        # Count clips for this specific channel
        clips_count, total_size, last_clip_time = count_clips_recursive(f"raw/{channel_name}")
        
        # Calculate time ago for last clip
        last_clip_str = None
        if last_clip_time:
            from datetime import datetime
            try:
                last_time = datetime.fromisoformat(last_clip_time.replace('Z', '+00:00'))
                now = datetime.now(last_time.tzinfo)
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
            "clips_captured": clips_count,
            "segments_analyzed": clips_count * 3,  # Rough estimate: ~3 segments per clip
            "last_clip_time": last_clip_str,
            "total_size_mb": round(total_size / (1024 * 1024), 1)
        }
        
    except Exception as e:
        print(f"Error getting stats for {channel_name}: {e}")
        return {
            "clips_captured": 0,
            "segments_analyzed": 0,
            "last_clip_time": None,
            "total_size_mb": 0
        }


    try:
        # Create Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            return {
                "clips_captured": 0,
                "segments_analyzed": 0,
                "last_clip_time": None,
                "total_size_mb": 0
            }
        
        sb = create_client(supabase_url, supabase_key)
        
        # Count clips recursively in storage for this channel
        def count_clips_recursive(path="raw"):
            """Recursively count MP4 files for a channel"""
            try:
                items = sb.storage.from_("raw").list(path, {'limit': 1000})
                count = 0
                total_size = 0
                latest_time = None
                
                for item in items:
                    item_name = item.get('name', '')
                    
                    # If it's an MP4 file, count it
                    if item_name.endswith('.mp4'):
                        count += 1
                        size = item.get('metadata', {}).get('size', 0)
                        total_size += size
                        created = item.get('created_at') or item.get('metadata', {}).get('lastModified')
                        if created and (not latest_time or created > latest_time):
                            latest_time = created
                    
                    # If it's a folder, recurse
                    elif '.' not in item_name:
                        subfolder_path = f"{path}/{item_name}"
                        sub_count, sub_size, sub_time = count_clips_recursive(subfolder_path)
                        count += sub_count
                        total_size += sub_size
                        if sub_time and (not latest_time or sub_time > latest_time):
                            latest_time = sub_time
                
                return count, total_size, latest_time
            except Exception as e:
                print(f"Error counting clips in {path}: {e}")
                return 0, 0, None
        
        # Count clips for this specific channel
        clips_count, total_size, last_clip_time = count_clips_recursive(f"raw/{channel_name}")
        
        # Calculate time ago for last clip
        last_clip_str = None
        if last_clip_time:
            from datetime import datetime
            try:
                last_time = datetime.fromisoformat(last_clip_time.replace('Z', '+00:00'))
                now = datetime.now(last_time.tzinfo)
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
            "clips_captured": clips_count,
            "segments_analyzed": clips_count * 3,  # Rough estimate: ~3 segments per clip
            "last_clip_time": last_clip_str,
            "total_size_mb": round(total_size / (1024 * 1024), 1)
        }
        
    except Exception as e:
        print(f"Error getting stats for {channel_name}: {e}")
        return {
            "clips_captured": 0,
            "segments_analyzed": 0,
            "last_clip_time": None,
            "total_size_mb": 0
        }

