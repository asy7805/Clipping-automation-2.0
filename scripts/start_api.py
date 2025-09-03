#!/usr/bin/env python3
"""
Start the Clipping Automation API server.
"""

import os
import sys
import uvicorn
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

def main():
    """Start the API server with proper configuration."""
    
    # Check required environment variables
    required_vars = ["SUPABASE_URL", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("💡 Please configure your .env file with the required API keys")
        sys.exit(1)
    
    print("🚀 Starting Clipping Automation API...")
    print(f"📡 Supabase URL: {os.getenv('SUPABASE_URL')}")
    print(f"🤖 OpenAI API: {'✅ Configured' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")
    print(f"📺 Twitch API: {'✅ Configured' if os.getenv('TWITCH_CLIENT_ID') else '❌ Missing'}")
    print("🌐 API Documentation: http://localhost:8000/docs")
    print("=" * 60)
    
    # Start the server
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        reload_dirs=["src/api"]
    )

if __name__ == "__main__":
    main()
