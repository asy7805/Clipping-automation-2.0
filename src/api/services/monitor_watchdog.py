"""
Monitor Watchdog Service
Monitors running stream monitors and auto-restarts them on failure.
"""

import asyncio
import logging
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class MonitorWatchdog:
    """Watches over active monitors and restarts them if they fail"""
    
    def __init__(self, active_monitors: Dict[str, Dict[str, Any]], twitch_api):
        """
        Initialize the watchdog.
        
        Args:
            active_monitors: Reference to the active_monitors dict from monitors.py
            twitch_api: TwitchEngagementFetcher instance
        """
        self.active_monitors = active_monitors
        self.twitch_api = twitch_api
        self.check_interval = 30  # Check every 30 seconds
        self.running = False
        self.last_check_times = {}
        
    def is_process_running(self, pid: int) -> bool:
        """Check if a process is still running (excludes zombies)"""
        try:
            process = psutil.Process(pid)
            # Check if process exists and is not a zombie
            if process.status() == psutil.STATUS_ZOMBIE:
                logger.warning(f"Process {pid} is a zombie, considering it as not running")
                return False
            return process.is_running()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    async def check_monitor_health(self, channel: str, monitor: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check the health of a single monitor.
        
        Returns:
            Dict with health status and any issues found
        """
        issues = []
        
        # Check 1: Process still running?
        pid = monitor.get('process_id')
        if not pid or not self.is_process_running(pid):
            issues.append(f"Process {pid} is not running")
            return {"healthy": False, "issues": issues, "action": "restart"}
        
        # Check 2: Is Twitch stream still live?
        try:
            stream_info = self.twitch_api.get_stream_info(channel)
            if stream_info and not stream_info.get('is_live', False):
                issues.append("Stream went offline on Twitch")
                # Don't auto-restart if stream is offline, just pause
                return {"healthy": False, "issues": issues, "action": "pause"}
        except Exception as e:
            logger.warning(f"Could not check Twitch status for {channel}: {e}")
        
        # Check 3: Has it produced segments recently?
        last_segment_time = monitor.get('last_segment_time')
        if last_segment_time:
            time_since_segment = (datetime.utcnow() - last_segment_time).total_seconds()
            if time_since_segment > 120:  # No segments for 2 minutes
                issues.append(f"No segments produced in {time_since_segment:.0f}s")
                return {"healthy": False, "issues": issues, "action": "restart"}
        
        # Check 4: High resource usage?
        try:
            process = psutil.Process(pid)
            
            # Check if process is a zombie
            if process.status() == psutil.STATUS_ZOMBIE:
                logger.warning(f"Process for {channel} is a zombie (pid={pid}), marking for restart")
                issues.append(f"Process is a zombie (terminated but not cleaned up)")
                return {"healthy": False, "issues": issues, "action": "restart"}
            
            cpu_percent = process.cpu_percent(interval=0.1)
            memory_mb = process.memory_info().rss / (1024 * 1024)
            
            if cpu_percent > 95:
                issues.append(f"Critically high CPU usage: {cpu_percent}%")
            if memory_mb > 2048:  # 2GB
                issues.append(f"High memory usage: {memory_mb:.0f} MB")
        except psutil.NoSuchProcess:
            logger.warning(f"Process for {channel} no longer exists (pid={pid})")
            issues.append("Process no longer exists")
            return {"healthy": False, "issues": issues, "action": "restart"}
        except psutil.ZombieProcess as e:
            logger.warning(f"Process for {channel} is a zombie (pid={pid}): {e}")
            issues.append("Process is a zombie (terminated but not cleaned up)")
            return {"healthy": False, "issues": issues, "action": "restart"}
        except Exception as e:
            logger.warning(f"Could not check process metrics for {channel}: {e}")
        
        if issues:
            return {"healthy": False, "issues": issues, "action": "warn"}
        
        return {"healthy": True, "issues": [], "action": None}
    
    async def restart_monitor(self, channel: str):
        """
        Restart a failed monitor.
        
        Args:
            channel: Channel name to restart
        """
        logger.warning(f"🔄 Attempting to restart monitor for {channel}")
        
        monitor = self.active_monitors.get(channel)
        if not monitor:
            return
        
        # Kill the old process if it's still running or is a zombie
        pid = monitor.get('process_id')
        if pid:
            try:
                process = psutil.Process(pid)
                
                # If it's a zombie, we need to wait() on it to clean it up
                if process.status() == psutil.STATUS_ZOMBIE:
                    logger.info(f"Cleaning up zombie process {pid} for {channel}")
                    try:
                        # Try to reap the zombie by waiting on it
                        process.wait(timeout=1)
                    except:
                        pass
                elif process.is_running():
                    # It's a real running process, terminate it
                    logger.info(f"Terminating running process {pid} for {channel}")
                    process.terminate()
                    await asyncio.sleep(2)
                    if process.is_running():
                        logger.warning(f"Process {pid} didn't terminate gracefully, killing it")
                        process.kill()
            except psutil.NoSuchProcess:
                logger.info(f"Process {pid} for {channel} already gone")
            except psutil.ZombieProcess:
                logger.info(f"Process {pid} for {channel} is a zombie, will create new process")
            except Exception as e:
                logger.warning(f"Error cleaning up old process {pid} for {channel}: {e}")
        
        # Start new process
        try:
            import subprocess
            import sys
            script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "live_ingest.py"
            
            # Use the same Python interpreter that's running this API (from .venv)
            python_executable = sys.executable
            
            process = subprocess.Popen(
                [
                    python_executable,
                    str(script_path),
                    "--channel", channel,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
            
            # Update monitor info
            monitor['process_id'] = process.pid
            monitor['restarted_at'] = datetime.utcnow().isoformat()
            monitor['restart_count'] = monitor.get('restart_count', 0) + 1
            
            logger.info(f"✅ Restarted monitor for {channel} with new PID: {process.pid}")
            
        except Exception as e:
            logger.error(f"❌ Failed to restart monitor for {channel}: {e}")
    
    async def run_watchdog_loop(self):
        """Main watchdog loop that checks all monitors"""
        self.running = True
        logger.info("🐕 Monitor Watchdog started")
        
        while self.running:
            try:
                # Check each active monitor
                for channel in list(self.active_monitors.keys()):
                    monitor = self.active_monitors[channel]
                    
                    # Perform health check
                    health_status = await self.check_monitor_health(channel, monitor)
                    
                    if not health_status['healthy']:
                        issues_str = ", ".join(health_status['issues'])
                        logger.warning(f"⚠️ Monitor {channel} unhealthy: {issues_str}")
                        
                        # Take action based on health check result
                        action = health_status.get('action')
                        
                        if action == "restart":
                            # Process died or not producing segments - restart it
                            await self.restart_monitor(channel)
                            
                        elif action == "pause":
                            # Stream went offline - just log, don't restart
                            logger.info(f"ℹ️ Stream {channel} is offline, keeping monitor paused")
                            monitor['status'] = 'paused'
                            
                        elif action == "warn":
                            # Issues but not critical - just log warnings
                            logger.warning(f"⚠️ Monitor {channel} has warnings: {issues_str}")
                    
                    # Update last check time
                    self.last_check_times[channel] = datetime.utcnow()
                
            except Exception as e:
                logger.error(f"❌ Error in watchdog loop: {e}")
            
            # Wait before next check
            await asyncio.sleep(self.check_interval)
    
    def stop(self):
        """Stop the watchdog"""
        self.running = False
        logger.info("🛑 Monitor Watchdog stopped")


