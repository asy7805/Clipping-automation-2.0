"""
Clip management endpoints for creating, retrieving, and managing clips.
OPTIMIZED VERSION - Reduced Supabase API calls
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi import Path as PathParam
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import sys
from pathlib import Path
import os

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
    storage_url: Optional[str] = None
    file_size: Optional[int] = None
    
    class Config:
        extra = "allow"  # Allow additional fields

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
        from supabase import create_client
        
        # Create a fresh client with service role for storage access
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            print("Warning: Supabase credentials not found")
            return []
            
        sb = create_client(supabase_url, supabase_key)
        bucket = "raw"
        
        # OPTIMIZED: Fetch clips from Supabase Storage with minimal API calls
        def get_all_clips_from_storage():
            """Fetch all clips from storage with minimal API calls"""
            all_clips = []
            
            try:
                # List all top-level folders (channels) in root
                channels = sb.storage.from_(bucket).list('', {'limit': 100})
                
                for channel_folder in channels:
                    channel_name_item = channel_folder.get('name', '')
                    
                    # Skip if it's a file, not a folder
                    if '.' in channel_name_item:
                        continue
                    
                    # List all files in this channel's folder
                    try:
                        files = sb.storage.from_(bucket).list(channel_name_item, {'limit': 1000})
                        
                        for file_item in files:
                            file_name = file_item.get('name', '')
                            
                            # Only process MP4 files
                            if file_name.endswith('.mp4'):
                                file_path = f"{channel_name_item}/{file_name}"
                                metadata = file_item.get('metadata', {})
                                
                                # Generate public URL
                                public_url = sb.storage.from_(bucket).get_public_url(file_path)
                                
                                all_clips.append({
                                    'id': file_path.replace('/', '_'),
                                    'file_path': file_path,
                                    'file_name': file_name,
                                    'channel_name': channel_name_item,
                                    'size': metadata.get('size', 0),
                                    'created_at': metadata.get('lastModified', file_item.get('created_at', datetime.utcnow().isoformat())),
                                    'public_url': public_url
                                })
                    except Exception as e:
                        print(f"Error listing files for channel {channel_name_item}: {e}")
                        
            except Exception as e:
                print(f"Error listing channels: {e}")
                
            return all_clips
        
        # Get all clips from storage
        storage_clips = get_all_clips_from_storage()
        
        # Sort by created date (newest first)
        storage_clips.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # Apply channel filter
        if channel_name:
            storage_clips = [c for c in storage_clips if channel_name.lower() in c['channel_name'].lower()]
        
        # Apply pagination
        paginated_clips = storage_clips[offset:offset + limit]
        
        # Build response with storage URLs
        clips = []
        for clip in paginated_clips:
            # Get scores from filename if available (format: channel_YYYYMMDD_HHMMSS_score.mp4)
            try:
                parts = clip['file_name'].replace('.mp4', '').split('_')
                score = 0.75  # default
                for i, part in enumerate(parts):
                    if i > 0 and '.' in part:
                        try:
                            score = float(part)
                            break
                        except:
                            pass
            except:
                score = 0.75
                
            clips.append({
                'id': clip['id'],
                'transcript': "",  # Not stored in filename
                'is_clip_worthy': score >= 0.7,
                'confidence_score': score,
                'created_at': clip['created_at'],
                'stream_id': None,
                'channel_name': clip['channel_name'],
                'storage_url': clip['public_url'],
                'file_size': clip['size']
            })
        
        return clips
        
    except Exception as e:
        print(f"Error fetching clips: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch clips: {str(e)}")


@router.get("/clips/{clip_id}", response_model=ClipResponse)
async def get_clip(clip_id: str = PathParam(...)) -> ClipResponse:
    """
    Retrieve a specific clip by ID.
    
    Args:
        clip_id: The ID of the clip to retrieve
        
    Returns:
        Clip details
    """
    try:
        manager = SupabaseManager()
        
        # Fetch from predictions table
        result = manager.get_clip_predictions(limit=1000)
        clips = [c for c in result if c.get('id') == clip_id or str(c.get('id')) == clip_id]
        
        if not clips:
            raise HTTPException(status_code=404, detail=f"Clip {clip_id} not found")
            
        clip = clips[0]
        return ClipResponse(**clip)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch clip: {str(e)}")




