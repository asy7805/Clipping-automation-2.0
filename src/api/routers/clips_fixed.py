"""
Clip management endpoints - FIXED for deeply nested storage structure
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi import Path as PathParam
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import sys
from pathlib import Path
import os

sys.path.append(str(Path(__file__).parent.parent.parent))

from predict import is_clip_worthy_by_model
from supabase_integration import SupabaseManager

router = APIRouter()

class ClipCreateRequest(BaseModel):
    transcript: str
    stream_id: Optional[str] = None
    channel_name: Optional[str] = None
    timestamp: Optional[datetime] = None
    duration: Optional[float] = None

class ClipResponse(BaseModel):
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

@router.get("/clips", response_model=List[ClipResponse])
async def get_clips(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    channel_name: Optional[str] = Query(None),
    is_clip_worthy: Optional[bool] = Query(None)
) -> List[ClipResponse]:
    try:
        from supabase import create_client
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            return []
            
        sb = create_client(supabase_url, supabase_key)
        bucket = "raw"
        
        def get_all_mp4_files(path="raw/raw", depth=0, max_depth=5):
            """Recursively find all MP4 files in storage"""
            if depth > max_depth:
                return []
            
            all_files = []
            try:
                items = sb.storage.from_(bucket).list(path, {'limit': 1000})
                
                for item in items:
                    item_name = item.get('name', '')
                    full_path = f"{path}/{item_name}"
                    
                    # If it's an MP4 file, add it
                    if item_name.endswith('.mp4'):
                        metadata = item.get('metadata', {})
                        
                        # Extract channel from path: raw/raw/CHANNEL/...
                        path_parts = path.split('/')
                        channel = path_parts[2] if len(path_parts) > 2 else "unknown"
                        
                        public_url = sb.storage.from_(bucket).get_public_url(full_path)
                        
                        all_files.append({
                            'id': full_path.replace('/', '_'),
                            'file_path': full_path,
                            'file_name': item_name,
                            'channel_name': channel,
                            'size': metadata.get('size', 0),
                            'created_at': metadata.get('lastModified', item.get('created_at', datetime.utcnow().isoformat())),
                            'public_url': public_url
                        })
                    # If it's a folder (no extension), recurse into it
                    elif '.' not in item_name and item_name != '.emptyFolderPlaceholder':
                        all_files.extend(get_all_mp4_files(full_path, depth + 1, max_depth))
                        
            except Exception as e:
                print(f"Error listing {path}: {e}")
                
            return all_files
        
        # Get all clips recursively
        storage_clips = get_all_mp4_files()
        
        # Sort by created date (newest first)
        storage_clips.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # Apply channel filter
        if channel_name:
            storage_clips = [c for c in storage_clips if channel_name.lower() in c['channel_name'].lower()]
        
        # Apply pagination
        paginated_clips = storage_clips[offset:offset + limit]
        
        # Build response
        clips = []
        for clip in paginated_clips:
            # Try to extract score from filename
            try:
                parts = clip['file_name'].replace('.mp4', '').split('_')
                score = 0.75  # default
                for part in parts:
                    if '.' in part:
                        try:
                            score = float(part)
                            break
                        except:
                            pass
            except:
                score = 0.75
                
            clips.append({
                'id': clip['id'],
                'transcript': "",
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
    try:
        manager = SupabaseManager()
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










