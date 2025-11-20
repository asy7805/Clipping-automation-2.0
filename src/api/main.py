#!/usr/bin/env python3
"""
FastAPI Server for Clipping Automation 2.0
Provides REST API endpoints for clip management, analytics, and automation.
"""

import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Import LLM Observe for monitoring
try:
    import llmobserve
    LLMOBSERVE_AVAILABLE = True
except ImportError:
    LLMOBSERVE_AVAILABLE = False
    print("⚠️ llmobserve package not available - LLM monitoring disabled")

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

# Import API routers
from .routers import clips, analytics, streams, health, captions, monitors, admin, social
try:
    from .routers import subscription
    print("✅ Subscription router imported successfully")
except Exception as e:
    print(f"❌ Failed to import subscription router: {e}")
    import traceback
    traceback.print_exc()
    subscription = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    print("🚀 Starting Clipping Automation API...")
    print(f"📡 Supabase URL: {os.getenv('SUPABASE_URL', 'Not configured')}")
    print(f"🤖 OpenAI API: {'✅ Configured' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")
    print(f"📺 Twitch API: {'✅ Configured' if os.getenv('TWITCH_CLIENT_ID') else '❌ Missing'}")
    print(f"🎬 Captions AI: {'✅ Configured' if os.getenv('CAPTIONS_AI_API_KEY') else '❌ Missing'}")
    
    # Initialize LLM Observe monitoring
    if LLMOBSERVE_AVAILABLE:
        llmobserve_api_key = os.getenv("LLMOBSERVE_API_KEY", "llmo_sk_068ee9bbc99e20dc940db32bc6a69e4bc943bcdd01405887")
        if llmobserve_api_key:
            try:
                llmobserve.observe(
                    collector_url="https://app.llmobserve.com",
                    api_key=llmobserve_api_key
                )
                print("✅ LLM Observe monitoring initialized")
            except Exception as e:
                print(f"⚠️ Failed to initialize LLM Observe: {e}")
        else:
            print("⚠️ LLM Observe API key not configured")
    else:
        print("⚠️ LLM Observe not available - skipping initialization")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down Clipping Automation API...")

# Create FastAPI app
app = FastAPI(
    title="Clipping Automation 2.0 API",
    description="REST API for automated clip collection, processing, and analytics",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS origins from environment variable
# Format: "https://domain1.com,https://domain2.com" or "*" for all
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
if allowed_origins_env:
    allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
else:
    # Default to allow all origins (for development)
    allowed_origins = ["*"]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(clips.router, prefix="/api/v1", tags=["clips"])
app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])
app.include_router(streams.router, prefix="/api/v1", tags=["streams"])
app.include_router(captions.router, prefix="/api/v1", tags=["captions"])
app.include_router(monitors.router, prefix="/api/v1", tags=["monitors"])
app.include_router(admin.router, prefix="/api/v1", tags=["admin"])
app.include_router(social.router, prefix="/api/v1", tags=["social"])
if subscription:
    try:
        app.include_router(subscription.router, prefix="/api/v1", tags=["subscription"])
        print("✅ Subscription router registered successfully")
    except Exception as e:
        print(f"❌ Failed to register subscription router: {e}")
        import traceback
        traceback.print_exc()
else:
    print("⚠️ Subscription router not available - skipping registration")

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
