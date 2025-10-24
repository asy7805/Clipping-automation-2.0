#!/usr/bin/env python3
"""
FastAPI Server for Clipping Automation 2.0
Provides REST API endpoints for clip management, analytics, and automation.
"""

import os
import sys
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

# Import API routers
from .routers import clips, analytics, streams, health, monitors
from .services.monitor_watchdog import MonitorWatchdog
from twitch_engagement_fetcher import TwitchEngagementFetcher

# Global watchdog instance
watchdog_instance = None
watchdog_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    global watchdog_instance, watchdog_task
    
    # Startup
    print("🚀 Starting Clipping Automation API...")
    print(f"📡 Supabase URL: {os.getenv('SUPABASE_URL', 'Not configured')}")
    print(f"🤖 OpenAI API: {'✅ Configured' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")
    print(f"📺 Twitch API: {'✅ Configured' if os.getenv('TWITCH_CLIENT_ID') else '❌ Missing'}")
    
    # Start monitor watchdog
    print("🐕 Starting Monitor Watchdog...")
    twitch_api = TwitchEngagementFetcher()
    watchdog_instance = MonitorWatchdog(monitors.active_monitors, twitch_api)
    watchdog_task = asyncio.create_task(watchdog_instance.run_watchdog_loop())
    print("✅ Monitor Watchdog started (auto-restart enabled)")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down Clipping Automation API...")
    if watchdog_instance:
        watchdog_instance.stop()
    if watchdog_task:
        watchdog_task.cancel()
        try:
            await watchdog_task
        except asyncio.CancelledError:
            pass
    print("✅ Shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Clipping Automation 2.0 API",
    description="REST API for automated clip collection, processing, and analytics",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(clips.router, prefix="/api/v1", tags=["clips"])
app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])
app.include_router(streams.router, prefix="/api/v1", tags=["streams"])
app.include_router(monitors.router, prefix="/api/v1", tags=["monitors"])

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Clipping Automation 2.0 API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
