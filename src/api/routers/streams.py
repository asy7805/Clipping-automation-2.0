"""
Stream management endpoints for monitoring and managing live streams.
"""

from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

router = APIRouter()

# Pydantic models
class StreamResponse(BaseModel):
    """Response model for stream data."""
    id: str
    twitch_stream_id: str
    channel_name: str
    title: str
    category: str
    started_at: datetime
    viewer_count: int
    is_live: bool
    status: str

class StreamCreateRequest(BaseModel):
    """Request model for creating a new stream record."""
    twitch_stream_id: str
    channel_name: str
    title: str
    category: str
    viewer_count: int = 0
    user_id: Optional[str] = None

@router.get("/streams", response_model=List[StreamResponse])
async def get_streams(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    channel_name: Optional[str] = Query(None),
    is_live: Optional[bool] = Query(None)
) -> List[StreamResponse]:
    """
    Retrieve streams with optional filtering.
    
    Args:
        limit: Maximum number of streams to return
        offset: Number of streams to skip
        channel_name: Filter by channel name
        is_live: Filter by live status
        
    Returns:
        List of streams matching the criteria
    """
    try:
        # TODO: Implement actual database query using SupabaseManager
        # This is a placeholder response
        return [
            StreamResponse(
                id="stream-1",
                twitch_stream_id="twitch-12345",
                channel_name="example_channel",
                title="Example Stream Title",
                category="Just Chatting",
                started_at=datetime.utcnow(),
                viewer_count=150,
                is_live=True,
                status="active"
            )
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve streams: {str(e)}")

@router.get("/streams/{stream_id}", response_model=StreamResponse)
async def get_stream(stream_id: str = Path(..., description="Stream ID")) -> StreamResponse:
    """
    Retrieve a specific stream by ID.
    
    Args:
        stream_id: Unique identifier for the stream
        
    Returns:
        Stream data
    """
    try:
        # TODO: Implement actual database query
        # This is a placeholder response
        return StreamResponse(
            id=stream_id,
            twitch_stream_id="twitch-12345",
            channel_name="example_channel",
            title="Example Stream Title",
            category="Just Chatting",
            started_at=datetime.utcnow(),
            viewer_count=150,
            is_live=True,
            status="active"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve stream: {str(e)}")

@router.post("/streams", response_model=StreamResponse)
async def create_stream(request: StreamCreateRequest) -> StreamResponse:
    """
    Create a new stream record.
    
    Args:
        request: Stream creation request
        
    Returns:
        Created stream data
    """
    try:
        # TODO: Save to database using SupabaseManager
        # For now, return a mock response
        return StreamResponse(
            id="new-stream-123",
            twitch_stream_id=request.twitch_stream_id,
            channel_name=request.channel_name,
            title=request.title,
            category=request.category,
            started_at=datetime.utcnow(),
            viewer_count=request.viewer_count,
            is_live=True,
            status="active"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create stream: {str(e)}")

@router.get("/streams/live")
async def get_live_streams() -> List[StreamResponse]:
    """
    Get all currently live streams.
    
    Returns:
        List of live streams
    """
    try:
        # TODO: Implement actual query for live streams
        # This is a placeholder response
        return [
            StreamResponse(
                id="live-stream-1",
                twitch_stream_id="twitch-live-123",
                channel_name="live_channel_1",
                title="Live Stream Example",
                category="Gaming",
                started_at=datetime.utcnow(),
                viewer_count=500,
                is_live=True,
                status="active"
            )
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get live streams: {str(e)}")

@router.get("/streams/{stream_id}/clips")
async def get_stream_clips(
    stream_id: str = Path(..., description="Stream ID"),
    limit: int = Query(10, ge=1, le=100)
) -> List[Dict[str, Any]]:
    """
    Get clips associated with a specific stream.
    
    Args:
        stream_id: Stream ID to get clips for
        limit: Maximum number of clips to return
        
    Returns:
        List of clips for the stream
    """
    try:
        # TODO: Implement actual query for stream clips
        # This is a placeholder response
        return [
            {
                "id": "clip-1",
                "transcript": "Example clip transcript",
                "is_clip_worthy": True,
                "confidence_score": 0.92,
                "created_at": datetime.utcnow().isoformat()
            }
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stream clips: {str(e)}")
