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
from pathlib import Path

router = APIRouter()

# In-memory store for active monitors (in production, use database)
active_monitors: Dict[str, Dict[str, Any]] = {}

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
    """Check if a process is still running."""
    try:
        process = psutil.Process(pid)
        return process.is_running()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
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
        
        # Start the process in the background
        process = subprocess.Popen(
            [
                "python3",
                str(script_path),
                "--channel", channel_name,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True  # Detach from parent
        )
        
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
    # Clean up dead processes
    for channel in list(active_monitors.keys()):
        monitor = active_monitors[channel]
        pid = monitor.get('process_id')
        if pid and not is_process_running(pid):
            del active_monitors[channel]
    
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
    
    # Check if process is still running
    if pid and not is_process_running(pid):
        del active_monitors[channel_name]
        raise HTTPException(status_code=404, detail=f"Monitor for {channel_name} has stopped")
    
    return monitor

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

