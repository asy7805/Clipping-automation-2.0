"""
Clip management endpoints - Now uses clips_metadata database table
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi import Path as PathParam
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from predict import is_clip_worthy_by_model
from db.supabase_client import get_client
from ..dependencies import get_current_user_id
from ..middleware.auth import get_current_user, User

router = APIRouter()

print("🎬 Clips router loaded - Using clips_metadata database table")

class ClipCreateRequest(BaseModel):
    transcript: str
    stream_id: Optional[str] = None
    channel_name: Optional[str] = None
    timestamp: Optional[datetime] = None
    duration: Optional[float] = None

class ScoreBreakdown(BaseModel):
    energy: float
    pitch: float
    emotion: float
    keyword: float
    final_score: float

class ClipResponse(BaseModel):
    id: str
    transcript: Optional[str] = None
    is_clip_worthy: bool
    confidence_score: Optional[float] = None
    created_at: datetime
    stream_id: Optional[str] = None
    channel_name: Optional[str] = None
    storage_url: Optional[str] = None
    file_size: Optional[int] = None
    score_breakdown: Optional[dict] = None
    
    class Config:
        extra = "allow"

class ClipPredictionRequest(BaseModel):
    transcript: str
    model_version: Optional[str] = None

class ClipPredictionResponse(BaseModel):
    is_clip_worthy: bool
    confidence_score: Optional[float] = None
    model_version: Optional[str] = None
    reasoning: Optional[str] = None

@router.post("/clips/predict", response_model=ClipPredictionResponse)
async def predict_clip_worthiness(request: ClipPredictionRequest) -> ClipPredictionResponse:
    """
    Predict if a transcript is clip-worthy using ML model.
    No authentication required (utility endpoint).
    """
    try:
        is_worthy = is_clip_worthy_by_model(
            request.transcript, 
            model_version=request.model_version
        )
        
        return ClipPredictionResponse(
            is_clip_worthy=is_worthy,
            confidence_score=0.85,
            model_version=request.model_version or "latest",
            reasoning="ML model prediction based on transcript analysis"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@router.get("/clips")
async def get_clips(
    limit: int = Query(20, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    channel_name: Optional[str] = Query(None),
    is_clip_worthy: Optional[bool] = Query(None),
    min_score: Optional[float] = Query(None, ge=0, le=5),
    max_score: Optional[float] = Query(None, ge=0, le=5),
    sort_by: Optional[str] = Query("newest", regex="^(newest|oldest|highest|lowest)$"),
    search_query: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """
    Get clips from database.
    Requires authentication.
    - Regular users only see their own clips
    - Admin users see ALL clips from all users
    """
    try:
        user_id = current_user.id
        is_admin = current_user.is_admin
        
        print(f"🎯 GET /clips called for user: {user_id[:8]}... (admin: {is_admin})")
        
        sb = get_client()
        
        # Build query - admins see all clips, regular users see only their own
        if is_admin:
            query = sb.table('clips_metadata').select('*')
            count_query = sb.table('clips_metadata').select('id', count='exact')
        else:
            query = sb.table('clips_metadata').select('*').eq('user_id', user_id)
            count_query = sb.table('clips_metadata').select('id', count='exact').eq('user_id', user_id)
        
        # Apply filters
        if channel_name:
            query = query.ilike('channel_name', f'%{channel_name}%')
            count_query = count_query.ilike('channel_name', f'%{channel_name}%')
        
        if min_score is not None:
            query = query.gte('confidence_score', min_score)
            count_query = count_query.gte('confidence_score', min_score)
        
        if max_score is not None:
            query = query.lte('confidence_score', max_score)
            count_query = count_query.lte('confidence_score', max_score)
        
        if search_query:
            # Search in channel name or transcript
            search_filter = f'channel_name.ilike.%{search_query}%,transcript.ilike.%{search_query}%'
            query = query.or_(search_filter)
            count_query = count_query.or_(search_filter)
        
        # Apply sorting
        if sort_by == "newest":
            query = query.order('created_at', desc=True)
        elif sort_by == "oldest":
            query = query.order('created_at', desc=False)
        elif sort_by == "highest":
            query = query.order('confidence_score', desc=True)
        elif sort_by == "lowest":
            query = query.order('confidence_score', desc=False)
        
        # Get total count before pagination
        count_result = count_query.execute()
        
        total_count = count_result.count if count_result.count is not None else 0
        
        # Apply pagination
        result = query.range(offset, offset + limit - 1).execute()
        
        clips = []
        for clip in result.data or []:
            clip_data = {
                'id': str(clip['id']),
                'transcript': clip.get('transcript', ''),
                'is_clip_worthy': True,  # All clips in DB are considered worthy
                'confidence_score': clip.get('confidence_score', 0),
                'created_at': clip.get('created_at'),
                'stream_id': clip.get('stream_id'),
                'channel_name': clip.get('channel_name'),
                'storage_url': clip.get('storage_url'),
                'file_size': clip.get('file_size'),
                'score_breakdown': clip.get('score_breakdown')
            }
            clips.append(clip_data)
        
        print(f"✅ Returning {len(clips)} clips out of {total_count} total")
        
        return {
            "clips": clips,
            "pagination": {
                "total": total_count,
                "page": (offset // limit) + 1,
                "limit": limit,
                "offset": offset,
                "has_next": offset + limit < total_count,
                "has_prev": offset > 0,
                "total_pages": (total_count + limit - 1) // limit
            }
        }
        
    except Exception as e:
        print(f"❌ Error fetching clips: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch clips: {str(e)}")

@router.get("/clips/{clip_id}", response_model=ClipResponse)
async def get_clip(
    clip_id: str = PathParam(...),
    user_id: str = Depends(get_current_user_id)
) -> ClipResponse:
    """
    Get a specific clip by ID.
    Requires authentication - users can only access their own clips.
    """
    try:
        sb = get_client()
        
        # Query with user filter for security
        result = sb.table('clips_metadata')\
            .select('*')\
            .eq('id', clip_id)\
            .eq('user_id', user_id)\
            .execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Clip {clip_id} not found")
        
        clip = result.data[0]
        
        return ClipResponse(
            id=str(clip['id']),
            transcript=clip.get('transcript', ''),
            is_clip_worthy=True,
            confidence_score=clip.get('confidence_score'),
            created_at=clip.get('created_at'),
            stream_id=clip.get('stream_id'),
            channel_name=clip.get('channel_name'),
            storage_url=clip.get('storage_url'),
            file_size=clip.get('file_size'),
            score_breakdown=clip.get('score_breakdown')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch clip: {str(e)}")

@router.delete("/clips/{clip_id}")
async def delete_clip(
    clip_id: str = PathParam(...),
    user_id: str = Depends(get_current_user_id)
):
    """
    Delete a clip.
    Requires authentication - users can only delete their own clips.
    """
    try:
        sb = get_client()
        
        # Verify clip exists and belongs to user
        clip_result = sb.table('clips_metadata')\
            .select('*')\
            .eq('id', clip_id)\
            .eq('user_id', user_id)\
            .execute()
        
        if not clip_result.data or len(clip_result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Clip {clip_id} not found")
        
        clip = clip_result.data[0]
        
        # Delete from database
        sb.table('clips_metadata')\
            .delete()\
            .eq('id', clip_id)\
            .execute()
        
        # Optionally delete from storage
        storage_path = clip.get('storage_path')
        if storage_path:
            try:
                sb.storage.from_('raw').remove([storage_path])
                print(f"🗑️  Deleted clip from storage: {storage_path}")
            except Exception as e:
                print(f"⚠️  Failed to delete from storage: {e}")
        
        return {
            "success": True,
            "message": f"Clip {clip_id} deleted",
            "deleted_clip": {
                "id": clip_id,
                "channel_name": clip.get('channel_name'),
                "created_at": clip.get('created_at')
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete clip: {str(e)}")

@router.get("/clips/test-score-raw")
async def test_score_raw():
    """Test endpoint to verify score breakdown structure. No auth required."""
    from datetime import datetime
    return {
        "id": "test_clip",
        "transcript": "This is a test",
        "is_clip_worthy": True,
        "confidence_score": 0.758,
        "created_at": datetime.now().isoformat(),
        "channel_name": "test_channel",
        "score_breakdown": {
            "energy": 0.8,
            "pitch": 0.6,
            "emotion": 0.9,
            "keyword": 0.15,
            "final_score": 0.758
        }
    }
