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
        
        # Get clips today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        clips_today_result = sb.table('clips_metadata')\
            .select('id', count='exact')\
            .gte('created_at', today_start)\
            .execute()
        clips_today = clips_today_result.count if clips_today_result.count is not None else 0
        
        # Get clips this week
        week_start = (datetime.utcnow() - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        clips_week_result = sb.table('clips_metadata')\
            .select('id', count='exact')\
            .gte('created_at', week_start)\
            .execute()
        clips_this_week = clips_week_result.count if clips_week_result.count is not None else 0
        
        # Calculate average clips per user
        avg_clips_per_user = round(total_clips / total_users, 2) if total_users > 0 else 0
        
        # Calculate average score
        avg_score_result = sb.table('clips_metadata')\
            .select('confidence_score')\
            .execute()
        if avg_score_result.data and len(avg_score_result.data) > 0:
            scores = [float(c.get('confidence_score', 0)) for c in avg_score_result.data if c.get('confidence_score') is not None]
            avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
        else:
            avg_score = 0.0
        
        # Convert storage bytes to GB
        storage_used_gb = round((total_storage or 0) / (1024 ** 3), 2)
        
        # Get historical data for the last 30 days (optimized - fetch all data once)
        user_growth_data = []
        monitor_activity_data = []
        
        # Fetch all clips and monitors data once
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
        
        all_clips = sb.table('clips_metadata')\
            .select('user_id,created_at')\
            .gte('created_at', thirty_days_ago)\
            .execute()
        
        all_monitors = sb.table('monitors')\
            .select('user_id,started_at,status')\
            .gte('started_at', thirty_days_ago)\
            .execute()
        
        # Process data for each day
        for i in range(30, -1, -1):  # Last 30 days including today
            date = (datetime.utcnow() - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            date_end = (date + timedelta(days=1)).isoformat()
            date_str = date.strftime("%Y-%m-%d")
            
            # Count cumulative users up to this date
            all_user_ids = set()
            if all_clips.data:
                for clip in all_clips.data:
                    clip_date = clip.get('created_at', '')
                    if clip_date and clip_date <= date_end:
                        user_id = clip.get('user_id')
                        if user_id:
                            all_user_ids.add(user_id)
            
            if all_monitors.data:
                for monitor in all_monitors.data:
                    monitor_date = monitor.get('started_at', '')
                    if monitor_date and monitor_date <= date_end:
                        user_id = monitor.get('user_id')
                        if user_id:
                            all_user_ids.add(user_id)
            
            user_count = len(all_user_ids)
            
            # Count active monitors on this date
            active_monitor_count = 0
            if all_monitors.data:
                for monitor in all_monitors.data:
                    monitor_date = monitor.get('started_at', '')
                    monitor_status = monitor.get('status', '')
                    # Check if monitor was started before or on this date and is running
                    if monitor_date and monitor_date <= date_end and monitor_status == 'running':
                        active_monitor_count += 1
            
            user_growth_data.append({
                "date": date_str,
                "users": user_count
            })
            
            monitor_activity_data.append({
                "date": date_str,
                "active": active_monitor_count
            })
        
        return {
            "total_users": total_users or 0,
            "total_clips": total_clips,
            "total_monitors": total_monitors,
            "active_monitors": active_monitors,
            "storage_used_bytes": total_storage or 0,
            "storage_used_gb": storage_used_gb,
            "new_users_this_week": new_users_week or 0,
            "clips_today": clips_today,
            "clips_this_week": clips_this_week,
            "avg_clips_per_user": avg_clips_per_user,
            "avg_score": avg_score,
            "user_growth": user_growth_data,
            "monitor_activity": monitor_activity_data,
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
        
        # Get users from auth.users table (via admin client)
        # Note: We'll query auth.users directly, but if that's not accessible, we'll use a workaround
        try:
            # Try to get users with stats via RPC if it exists
            users_result = sb.rpc('get_users_with_stats', {'limit_val': limit, 'offset_val': offset}).execute()
            users_list = users_result.data or []
            # Normalize user data to ensure 'id' field exists
            for user in users_list:
                if 'id' not in user or not user.get('id'):
                    # Try to get id from other possible field names
                    user['id'] = user.get('user_id') or user.get('uid') or user.get('id')
                    if not user.get('id'):
                        logger.warning(f"User object missing id field: {user}")
        except Exception as rpc_error:
            logger.warning(f"RPC get_users_with_stats failed, falling back to manual query: {rpc_error}")
            # Fallback: Get users from auth.users (if accessible) or from a users table
            # For now, we'll query clips_metadata to get unique user_ids and build user list
            clips_result = sb.table('clips_metadata')\
                .select('user_id')\
                .order('created_at', desc=True)\
                .execute()
            
            # Get unique user IDs
            unique_user_ids = list(set([c.get('user_id') for c in (clips_result.data or []) if c.get('user_id')]))
            
            # Also get user IDs from monitors
            monitors_result = sb.table('monitors')\
                .select('user_id')\
                .execute()
            monitor_user_ids = list(set([m.get('user_id') for m in (monitors_result.data or []) if m.get('user_id')]))
            unique_user_ids.extend(monitor_user_ids)
            unique_user_ids = list(set(unique_user_ids))
            
            # Build user list with stats
            users_list = []
            for uid in unique_user_ids[offset:offset + limit]:
                # Count clips for this user
                clip_count_result = sb.table('clips_metadata')\
                    .select('id', count='exact')\
                    .eq('user_id', uid)\
                    .execute()
                clip_count = clip_count_result.count if clip_count_result.count is not None else 0
                
                # Count monitors for this user
                monitor_count_result = sb.table('monitors')\
                    .select('id', count='exact')\
                    .eq('user_id', uid)\
                    .execute()
                monitor_count = monitor_count_result.count if monitor_count_result.count is not None else 0
                
                users_list.append({
                    'id': uid,
                    'email': uid[:8] + '...',  # Placeholder since we can't access auth.users email directly
                    'monitor_count': monitor_count,
                    'clip_count': clip_count,
                    'created_at': None,  # Would need auth.users access
                    'last_sign_in_at': None  # Would need auth.users access
                })
        
        return {
            "users": users_list,
            "limit": limit,
            "offset": offset,
            "total": len(users_list)
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
        # Validate target_user_id
        if not target_user_id or target_user_id == 'undefined' or target_user_id.strip() == '':
            raise HTTPException(status_code=400, detail="Invalid user ID provided")
        
        # Use admin client to bypass RLS for admin operations
        sb = get_admin_client()
        
        # Check if user already has admin access
        existing_admin = sb.table('admin_users')\
            .select('*')\
            .eq('user_id', target_user_id)\
            .execute()
        
        if existing_admin.data and len(existing_admin.data) > 0:
            return {
                "success": True,
                "message": f"User {target_user_id} already has admin access"
            }
        
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
    except HTTPException:
        raise
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
        # Validate target_user_id
        if not target_user_id or target_user_id == 'undefined' or target_user_id.strip() == '':
            raise HTTPException(status_code=400, detail="Invalid user ID provided")
        
        # Use admin client to bypass RLS for admin operations
        sb = get_admin_client()
        
        # Don't allow self-revocation
        if target_user_id == user_id:
            raise HTTPException(status_code=400, detail="Cannot revoke your own admin access")
        
        # Check if user has admin access
        existing_admin = sb.table('admin_users')\
            .select('*')\
            .eq('user_id', target_user_id)\
            .execute()
        
        if not existing_admin.data or len(existing_admin.data) == 0:
            return {
                "success": True,
                "message": f"User {target_user_id} does not have admin access"
            }
        
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


