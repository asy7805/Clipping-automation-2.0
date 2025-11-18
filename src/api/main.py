#!/usr/bin/env python3
"""
FastAPI Server for AscensionClips
Provides REST API endpoints for clip management, analytics, and automation.
"""

import os
import sys
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import logging

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv(Path(__file__).parent.parent / '.env')

# Import API routers
from .routers import clips, analytics, streams, health, monitors, social, admin, captions
from .services.monitor_watchdog import MonitorWatchdog
from twitch_engagement_fetcher import TwitchEngagementFetcher

logger = logging.getLogger(__name__)

# Global watchdog instance
watchdog_instance = None
watchdog_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    global watchdog_instance, watchdog_task
    
    # Startup
    print("🚀 Starting AscensionClips API...")
    print(f"📡 Supabase URL: {os.getenv('SUPABASE_URL', 'Not configured')}")
    print(f"🤖 OpenAI API: {'✅ Configured' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")
    print(f"📺 Twitch API: {'✅ Configured' if os.getenv('TWITCH_CLIENT_ID') else '❌ Missing'}")
    print(f"🎬 Captions AI: {'✅ Configured' if os.getenv('CAPTIONS_AI_API_KEY') else '❌ Missing'}")
    
    # Start monitor watchdog
    print("🐕 Starting Monitor Watchdog...")
    twitch_api = TwitchEngagementFetcher()
    watchdog_instance = MonitorWatchdog(monitors.active_monitors, twitch_api)
    watchdog_task = asyncio.create_task(watchdog_instance.run_watchdog_loop())
    print("✅ Monitor Watchdog started (auto-restart enabled)")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down AscensionClips API...")
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
    title="AscensionClips API",
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
    expose_headers=["*"]
)

# Exception handlers for auth errors
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with proper formatting."""
    if exc.status_code in [401, 403]:
        logger.warning(f"Auth error {exc.status_code}: {exc.detail} for {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "type": "http_exception"},
        headers=exc.headers
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.error(f"Unexpected error for {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "type": "server_error"}
    )

# Include API routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(clips.router, prefix="/api/v1", tags=["clips"])
app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])
app.include_router(streams.router, prefix="/api/v1", tags=["streams"])
app.include_router(monitors.router, prefix="/api/v1", tags=["monitors"])
app.include_router(social.router, prefix="/api/v1", tags=["social"])
app.include_router(admin.router, prefix="/api/v1", tags=["admin"])
app.include_router(captions.router, prefix="/api/v1", tags=["captions"])

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "AscensionClips API",
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
