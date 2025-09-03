"""
Clip management endpoints for creating, retrieving, and managing clips.
"""

from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from predict import is_clip_worthy_by_model
from supabase_integration import SupabaseManager

router = APIRouter()

# Pydantic models for request/response
class ClipCreateRequest(BaseModel):
    """Request model for creating a new clip."""
    transcript: str
    stream_id: Optional[str] = None
    channel_name: Optional[str] = None
    timestamp: Optional[datetime] = None
    duration: Optional[float] = None

class ClipResponse(BaseModel):
    """Response model for clip data."""
    id: str
    transcript: str
    is_clip_worthy: bool
    confidence_score: Optional[float] = None
    created_at: datetime
    stream_id: Optional[str] = None
    channel_name: Optional[str] = None

class ClipPredictionRequest(BaseModel):
    """Request model for clip prediction."""
    transcript: str
    model_version: Optional[str] = None

class ClipPredictionResponse(BaseModel):
    """Response model for clip prediction."""
    is_clip_worthy: bool
    confidence_score: Optional[float] = None
    model_version: Optional[str] = None
    reasoning: Optional[str] = None

@router.post("/clips/predict", response_model=ClipPredictionResponse)
async def predict_clip_worthiness(request: ClipPredictionRequest) -> ClipPredictionResponse:
    """
    Predict if a transcript is clip-worthy using the ML model.
    
    Args:
        request: Clip prediction request with transcript
        
    Returns:
        Prediction result with confidence score
    """
    try:
        # Use existing prediction function
        is_worthy = is_clip_worthy_by_model(
            request.transcript, 
            model_version=request.model_version
        )
        
        return ClipPredictionResponse(
            is_clip_worthy=is_worthy,
            confidence_score=0.85,  # TODO: Get actual confidence from model
            model_version=request.model_version or "latest",
            reasoning="ML model prediction based on transcript analysis"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@router.get("/clips", response_model=List[ClipResponse])
async def get_clips(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    channel_name: Optional[str] = Query(None),
    is_clip_worthy: Optional[bool] = Query(None)
) -> List[ClipResponse]:
    """
    Retrieve clips with optional filtering.
    
    Args:
        limit: Maximum number of clips to return
        offset: Number of clips to skip
        channel_name: Filter by channel name
        is_clip_worthy: Filter by clip-worthiness
        
    Returns:
        List of clips matching the criteria
    """
    try:
        # TODO: Implement actual database query
        # This is a placeholder response
        return [
            ClipResponse(
                id="example-clip-1",
                transcript="This is an example transcript",
                is_clip_worthy=True,
                confidence_score=0.92,
                created_at=datetime.utcnow(),
                stream_id="example-stream-1",
                channel_name="example_channel"
            )
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve clips: {str(e)}")

@router.get("/clips/{clip_id}", response_model=ClipResponse)
async def get_clip(clip_id: str = Path(..., description="Clip ID")) -> ClipResponse:
    """
    Retrieve a specific clip by ID.
    
    Args:
        clip_id: Unique identifier for the clip
        
    Returns:
        Clip data
    """
    try:
        # TODO: Implement actual database query
        # This is a placeholder response
        return ClipResponse(
            id=clip_id,
            transcript="This is an example transcript for the requested clip",
            is_clip_worthy=True,
            confidence_score=0.88,
            created_at=datetime.utcnow(),
            stream_id="example-stream-1",
            channel_name="example_channel"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve clip: {str(e)}")

@router.post("/clips", response_model=ClipResponse)
async def create_clip(request: ClipCreateRequest) -> ClipResponse:
    """
    Create a new clip record.
    
    Args:
        request: Clip creation request
        
    Returns:
        Created clip data
    """
    try:
        # Predict clip-worthiness
        is_worthy = is_clip_worthy_by_model(request.transcript)
        
        # TODO: Save to database using SupabaseManager
        # For now, return a mock response
        return ClipResponse(
            id="new-clip-123",
            transcript=request.transcript,
            is_clip_worthy=is_worthy,
            confidence_score=0.90,
            created_at=datetime.utcnow(),
            stream_id=request.stream_id,
            channel_name=request.channel_name
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create clip: {str(e)}")
