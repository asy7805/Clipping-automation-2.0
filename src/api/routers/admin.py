"""
Admin API Router
Admin-only endpoints for system management
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from ..middleware.admin import require_admin, get_user_role
from ..dependencies import get_current_user_id
from db.supabase_client import get_client, get_admin_client
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/admin/check")
async def check_admin_status(user_role: Dict = Depends(get_user_role)) -> Dict:
    """
    Quick endpoint to check if user is admin.
    Returns immediately without heavy computations.
    Uses get_user_role for consistent admin checking.
    """
    try:
        return {
            "user_id": user_role['user_id'],
            "is_admin": user_role['is_admin']
        }
    except Exception as e:
        logger.error(f"Error in admin check endpoint: {e}")
        # Return safe default on error
        return {
            "user_id": user_role.get('user_id', 'unknown'),
            "is_admin": False
        }

@router.get("/admin/stats")
async def get_system_stats(user_id: str = Depends(require_admin)) -> Dict:
    """
    Get system-wide statistics.
    Admin only.
    """
    try:
        # Use admin client to bypass RLS for admin operations
        sb = get_admin_client()
        
        # Get total counts using admin helper functions
        total_users = sb.rpc('get_user_count').execute().data
        total_storage = sb.rpc('sum_storage_size').execute().data
        
        # Get other stats
        total_clips_result = sb.table('clips_metadata').select('id', count='exact').execute()
        total_clips = total_clips_result.count if total_clips_result.count is not None else 0
        
        total_monitors_result = sb.table('monitors').select('id', count='exact').execute()
        total_monitors = total_monitors_result.count if total_monitors_result.count is not None else 0
        
        # Get new users in last 7 days
        week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        new_users_week = sb.rpc('count_new_users', {'since': week_ago}).execute().data
        
        # Get active monitors count
        active_monitors_result = sb.table('monitors')\
            .select('id', count='exact')\
            .eq('status', 'running')\
            .execute()
        active_monitors = active_monitors_result.count if active_monitors_result.count is not None else 0
        
        return {
            "total_users": total_users or 0,
            "total_clips": total_clips,
            "total_monitors": total_monitors,
            "active_monitors": active_monitors,
            "storage_used_bytes": total_storage or 0,
            "new_users_this_week": new_users_week or 0,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching system stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/users")
async def list_all_users(
    limit: int = 50,
    offset: int = 0,
    user_id: str = Depends(require_admin)
) -> Dict:
    """
    List all users with their stats.
    Admin only.
    """
    try:
        # Use admin client to bypass RLS for admin operations
        sb = get_admin_client()
        
        # Use admin helper function to get users with stats
        users = sb.rpc('get_users_with_stats', {'limit_val': limit, 'offset_val': offset}).execute()
        
        return {
            "users": users.data or [],
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/users/{target_user_id}")
async def get_user_details(
    target_user_id: str,
    user_id: str = Depends(require_admin)
) -> Dict:
    """
    Get detailed information about a specific user.
    Admin only.
    """
    try:
        # Use admin client to bypass RLS for admin operations
        sb = get_admin_client()
        
        # Use admin helper function
        user_info = sb.rpc('get_user_info', {'target_user_id': target_user_id}).execute()
        
        if not user_info.data or len(user_info.data) == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get recent clips for this user
        recent_clips = sb.table('clips_metadata')\
            .select('*')\
            .eq('user_id', target_user_id)\
            .order('created_at', desc=True)\
            .limit(10)\
            .execute()
        
        # Get monitors for this user
        monitors = sb.table('monitors')\
            .select('*')\
            .eq('user_id', target_user_id)\
            .execute()
        
        return {
            "user": user_info.data[0],
            "recent_clips": recent_clips.data or [],
            "monitors": monitors.data or []
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/clips")
async def list_all_clips(
    limit: int = 50,
    offset: int = 0,
    channel: Optional[str] = None,
    user_id: str = Depends(require_admin)
) -> Dict:
    """
    List all clips across all users.
    Admin only.
    """
    try:
        # Use admin client to bypass RLS for admin operations
        sb = get_admin_client()
        
        query = sb.table('clips_metadata')\
            .select('*')\
            .order('created_at', desc=True)
        
        if channel:
            query = query.eq('channel_name', channel)
        
        result = query.range(offset, offset + limit - 1).execute()
        
        return {
            "clips": result.data or [],
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error fetching all clips: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/admin/clips/{clip_id}")
async def delete_clip(
    clip_id: str,
    user_id: str = Depends(require_admin)
) -> Dict:
    """
    Delete a clip (for moderation).
    Admin only.
    """
    try:
        # Use admin client to bypass RLS for admin operations
        sb = get_admin_client()
        
        # Get clip info first
        clip = sb.table('clips_metadata')\
            .select('*')\
            .eq('id', clip_id)\
            .execute()
        
        if not clip.data or len(clip.data) == 0:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        clip_data = clip.data[0]
        
        # Delete from database
        sb.table('clips_metadata')\
            .delete()\
            .eq('id', clip_id)\
            .execute()
        
        # Note: Consider also deleting from storage
        # storage_path = clip_data.get('storage_path')
        # if storage_path:
        #     sb.storage.from_('raw').remove([storage_path])
        
        logger.info(f"Admin {user_id} deleted clip {clip_id}")
        
        return {
            "success": True,
            "message": f"Clip {clip_id} deleted",
            "clip": clip_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting clip: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/monitors")
async def list_all_monitors(user_id: str = Depends(require_admin)) -> Dict:
    """
    List all monitors across all users.
    Admin only.
    """
    try:
        # Use admin client to bypass RLS for admin operations
        sb = get_admin_client()
        
        monitors = sb.table('monitors')\
            .select('*')\
            .order('started_at', desc=True)\
            .execute()
        
        return {
            "monitors": monitors.data or [],
            "total": len(monitors.data) if monitors.data else 0
        }
    except Exception as e:
        logger.error(f"Error fetching all monitors: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/admins/{target_user_id}")
async def grant_admin(
    target_user_id: str,
    notes: Optional[str] = None,
    user_id: str = Depends(require_admin)
) -> Dict:
    """
    Grant admin access to a user.
    Admin only.
    """
    try:
        # Use admin client to bypass RLS for admin operations
        sb = get_admin_client()
        
        # Note: auth.users is a system table, may not be directly accessible
        # We'll proceed with granting admin access - if user doesn't exist, 
        # the foreign key constraint will fail anyway
        
        # Insert admin record
        admin_record = {
            'user_id': target_user_id,
            'granted_by': user_id,
            'notes': notes or f"Granted by admin {user_id}"
        }
        
        sb.table('admin_users')\
            .insert(admin_record)\
            .execute()
        
        logger.info(f"Admin {user_id} granted admin access to {target_user_id}")
        
        return {
            "success": True,
            "message": f"Admin access granted to user {target_user_id}"
        }
    except Exception as e:
        logger.error(f"Error granting admin: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/admin/admins/{target_user_id}")
async def revoke_admin(
    target_user_id: str,
    user_id: str = Depends(require_admin)
) -> Dict:
    """
    Revoke admin access from a user.
    Admin only.
    """
    try:
        # Use admin client to bypass RLS for admin operations
        sb = get_admin_client()
        
        # Don't allow self-revocation
        if target_user_id == user_id:
            raise HTTPException(status_code=400, detail="Cannot revoke your own admin access")
        
        # Delete admin record
        sb.table('admin_users')\
            .delete()\
            .eq('user_id', target_user_id)\
            .execute()
        
        logger.info(f"Admin {user_id} revoked admin access from {target_user_id}")
        
        return {
            "success": True,
            "message": f"Admin access revoked from user {target_user_id}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking admin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


