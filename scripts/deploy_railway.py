#!/usr/bin/env python3
"""
Railway Deployment Automation Script
Automates Railway CLI setup and deployment
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, check=True, capture_output=True):
    """Run a shell command and return the result."""
    print(f"🔧 Running: {' '.join(cmd)}")
    if capture_output:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if check and result.returncode != 0:
            print(f"❌ Error: {result.stderr}")
            sys.exit(1)
        return result
    else:
        # For interactive commands like login
        result = subprocess.run(cmd)
        if check and result.returncode != 0:
            sys.exit(1)
        return result

def check_railway_cli():
    """Check if Railway CLI is installed."""
    result = run_command(["which", "railway"], check=False)
    if result.returncode == 0:
        print("✅ Railway CLI is installed")
        return True
    return False

def install_railway_cli():
    """Install Railway CLI."""
    print("📦 Installing Railway CLI...")
    
    # Try different installation methods
    if run_command(["which", "brew"], check=False).returncode == 0:
        print("  Using Homebrew...")
        run_command(["brew", "install", "railway"])
    elif run_command(["which", "npm"], check=False).returncode == 0:
        print("  Using npm...")
        run_command(["npm", "install", "-g", "@railway/cli"])
    else:
        print("  Using shell script...")
        run_command(["bash", "-c", "bash <(curl -fsSL cli.new)"])
    
    print("✅ Railway CLI installed")

def login_railway():
    """Login to Railway."""
    print("🔐 Logging into Railway...")
    print("   (This will open a browser window for authentication)")
    run_command(["railway", "login"], capture_output=False)

def init_railway_project():
    """Initialize or link Railway project."""
    railway_dir = Path(".railway")
    if railway_dir.exists() and (railway_dir / "project.json").exists():
        print("✅ Project already linked")
        return
    
    print("📝 Setting up Railway project...")
    print("   Follow the prompts to create or link a project")
    run_command(["railway", "init"], capture_output=False)

def set_environment_variables_from_file(env_file_path):
    """Set environment variables from a file."""
    env_file = Path(env_file_path)
    if not env_file.exists():
        print(f"⚠️  {env_file_path} not found. Skipping environment variables.")
        return False
    
    print(f"📝 Setting environment variables from {env_file_path}...")
    vars_set = 0
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            
            if "=" not in line:
                continue
            
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            
            if not key:
                continue
            
            print(f"  Setting {key}...")
            # Try setting variable
            result = run_command(
                ["railway", "variables", "set", f"{key}={value}"],
                check=False
            )
            if result.returncode == 0:
                vars_set += 1
            else:
                print(f"    ⚠️  Failed to set {key}, you may need to set it manually")
    
    print(f"✅ Set {vars_set} environment variables")
    return True

def deploy():
    """Deploy to Railway."""
    print("🚀 Deploying to Railway...")
    run_command(["railway", "up"], capture_output=False)

def main():
    """Main deployment flow."""
    print("🚀 Railway Deployment Automation")
    print("=" * 40)
    print()
    
    # Check/install Railway CLI
    if not check_railway_cli():
        install_railway_cli()
    
    # Login
    print()
    login_railway()
    
    # Initialize project
    print()
    init_railway_project()
    
    # Set environment variables (try .env first, then .env.railway)
    print()
    env_set = False
    for env_file in [".env", ".env.railway"]:
        if Path(env_file).exists():
            set_environment_variables_from_file(env_file)
            env_set = True
            break
    
    if not env_set:
        print("⚠️  No .env or .env.railway file found.")
        print("   You'll need to set environment variables manually in Railway dashboard")
        print("   Required variables:")
        print("   - SUPABASE_URL")
        print("   - SUPABASE_KEY")
        print("   - SUPABASE_JWT_SECRET")
        print("   - TWITCH_CLIENT_ID")
        print("   - TWITCH_CLIENT_SECRET")
        print("   - LLMOBSERVE_API_KEY (optional)")
        print("   - ALLOWED_ORIGINS (optional)")
    
    # Deploy
    print()
    deploy()
    
    print()
    print("✅ Deployment initiated!")
    print()
    print("📋 Next steps:")
    print("   1. Check your Railway dashboard for deployment status")
    print("   2. View logs: railway logs")
    print("   3. Get URL: railway domain")
    print("   4. Test health endpoint: <your-url>/api/v1/health")

if __name__ == "__main__":
    main()

