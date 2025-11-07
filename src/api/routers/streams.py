"""
Stream management endpoints.
For MVP: Returns derived data from monitors table (no dedicated streams table).
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi import Path as PathParam
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from db.supabase_client import get_client
from ..dependencies import get_current_user_id

router = APIRouter()

# Pydantic models
class StreamResponse(BaseModel):
    """Response model for stream data."""
    id: str
    channel_name: str
    started_at: datetime
    is_live: bool
    status: str

@router.get("/streams", response_model=List[StreamResponse])
async def get_streams(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    channel_name: Optional[str] = Query(None),
    is_live: Optional[bool] = Query(None),
    user_id: str = Depends(get_current_user_id)
) -> List[StreamResponse]:
    """
    Retrieve user's stream sessions (derived from monitors).
    Requires authentication.
    """
    try:
        sb = get_client()
        
        # Query monitors table as proxy for streams
        query = sb.table("monitors")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("started_at", desc=True)
        
        # Apply filters
        if channel_name:
            query = query.eq("channel_name", channel_name)
        if is_live is not None:
            status_filter = "running" if is_live else "stopped"
            query = query.eq("status", status_filter)
        
        # Get monitors
        result = query.limit(limit).offset(offset).execute()
        monitors = result.data if result.data else []
        
        # Convert monitors to stream responses
        streams = []
        for monitor in monitors:
            streams.append(StreamResponse(
                id=str(monitor.get("id", "unknown")),
                channel_name=monitor.get("channel_name", ""),
                started_at=monitor.get("started_at", datetime.utcnow()),
                is_live=monitor.get("status") == "running",
                status=monitor.get("status", "stopped")
            ))
        
        return streams
        
    except Exception as e:
        print(f"Error fetching streams: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve streams: {str(e)}")

@router.get("/streams/{stream_id}", response_model=StreamResponse)
async def get_stream(
    stream_id: str = PathParam(..., description="Stream ID"),
    user_id: str = Depends(get_current_user_id)
) -> StreamResponse:
    """
    Retrieve a specific stream by ID.
    Requires authentication.
    """
    try:
        sb = get_client()
        
        # Get monitor/stream by ID
        result = sb.table("monitors")\
            .select("*")\
            .eq("id", stream_id)\
            .eq("user_id", user_id)\
            .execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Stream {stream_id} not found")
        
        monitor = result.data[0]
        
        return StreamResponse(
            id=str(monitor["id"]),
            channel_name=monitor["channel_name"],
            started_at=monitor["started_at"],
            is_live=monitor["status"] == "running",
            status=monitor["status"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve stream: {str(e)}")

@router.get("/streams/{stream_id}/clips")
async def get_stream_clips(
    stream_id: str = PathParam(..., description="Stream ID"),
    limit: int = Query(10, ge=1, le=100),
    user_id: str = Depends(get_current_user_id)
) -> List[Dict[str, Any]]:
    """
    Get clips associated with a specific stream.
    Requires authentication.
    """
    try:
        sb = get_client()
        
        # Get monitor info to find channel name
        monitor_result = sb.table("monitors")\
            .select("channel_name")\
            .eq("id", stream_id)\
            .eq("user_id", user_id)\
            .execute()
        
        if not monitor_result.data or len(monitor_result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Stream {stream_id} not found")
        
        channel_name = monitor_result.data[0]["channel_name"]
        
        # Get clips for this channel
        clips_result = sb.table("clips_metadata")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("channel_name", channel_name)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        
        clips = []
        for clip in clips_result.data or []:
            clips.append({
                "id": str(clip["id"]),
                "transcript": clip.get("transcript", ""),
                "is_clip_worthy": True,
                "confidence_score": clip.get("confidence_score", 0),
                "created_at": clip.get("created_at"),
                "storage_url": clip.get("storage_url"),
                "score_breakdown": clip.get("score_breakdown")
            })
        
        return clips
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stream clips: {str(e)}")
