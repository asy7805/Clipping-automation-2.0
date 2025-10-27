#!/usr/bin/env python3
"""
Monitor TenZ stream capture process
"""
import os
import sys
import time
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.db.supabase_client import get_client

def check_processes():
    """Check if capture processes are running"""
    try:
        # Check for python processes
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], 
                              capture_output=True, text=True)
        python_processes = [line for line in result.stdout.split('\n') if 'python.exe' in line]
        
        print(f"🐍 Found {len(python_processes)} Python processes")
        for proc in python_processes:
            print(f"   {proc.strip()}")
        
        # Check for streamlink processes
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq streamlink.exe'], 
                              capture_output=True, text=True)
        streamlink_processes = [line for line in result.stdout.split('\n') if 'streamlink.exe' in line]
        
        print(f"📺 Found {len(streamlink_processes)} Streamlink processes")
        for proc in streamlink_processes:
            print(f"   {proc.strip()}")
            
        return len(python_processes) > 0 and len(streamlink_processes) > 0
        
    except Exception as e:
        print(f"❌ Error checking processes: {e}")
        return False

def check_supabase_connection():
    """Check Supabase connection"""
    try:
        sb = get_client()
        # Try a simple query
        result = sb.table('streams').select('*').limit(1).execute()
        print("✅ Supabase connection working")
        return True
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False

def check_tenz_stream():
    """Check if TenZ is currently streaming"""
    try:
        result = subprocess.run(['streamlink', 'https://www.twitch.tv/tenz', '--stream-url'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and 'm3u8' in result.stdout:
            print("✅ TenZ is currently live streaming")
            return True
        else:
            print("❌ TenZ is not currently streaming")
            return False
    except Exception as e:
        print(f"❌ Error checking TenZ stream: {e}")
        return False

def main():
    print("🔍 Monitoring TenZ Stream Capture")
    print("=" * 50)
    
    # Check environment
    print(f"SUPABASE_URL: {'SET' if os.getenv('SUPABASE_URL') else 'NOT SET'}")
    print(f"SUPABASE_ANON_KEY: {'SET' if os.getenv('SUPABASE_ANON_KEY') else 'NOT SET'}")
    print()
    
    # Check components
    supabase_ok = check_supabase_connection()
    tenz_live = check_tenz_stream()
    processes_ok = check_processes()
    
    print()
    print("📊 Status Summary:")
    print(f"   Supabase: {'✅' if supabase_ok else '❌'}")
    print(f"   TenZ Live: {'✅' if tenz_live else '❌'}")
    print(f"   Capture Processes: {'✅' if processes_ok else '❌'}")
    
    if supabase_ok and tenz_live and processes_ok:
        print("\n🎉 TenZ capture is running successfully!")
    else:
        print("\n⚠️  Some components need attention")

if __name__ == "__main__":
    main()

