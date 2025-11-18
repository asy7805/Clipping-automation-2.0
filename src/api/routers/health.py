"""
Health check endpoints for API monitoring.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import os
from datetime import datetime

router = APIRouter()

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    
    Returns:
        Dict containing health status and timestamp
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "ascension-clips-api"
    }

@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check including external service status.
    
    Returns:
        Dict containing detailed health information
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "ascension-clips-api",
        "checks": {
            "environment": {
                "status": "ok",
                "supabase_configured": bool(os.getenv("SUPABASE_URL")),
                "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
                "twitch_configured": bool(os.getenv("TWITCH_CLIENT_ID"))
            }
        }
    }
    
    # Check if any critical services are missing
    critical_services = [
        os.getenv("SUPABASE_URL"),
        os.getenv("OPENAI_API_KEY"),
        os.getenv("TWITCH_CLIENT_ID")
    ]
    
    if not all(critical_services):
        health_status["status"] = "degraded"
        health_status["checks"]["environment"]["status"] = "warning"
    
    return health_status
