"""
Admin Authorization Middleware
Checks if a user has admin privileges
"""
from fastapi import HTTPException, Depends
from typing import Dict
from ..dependencies import get_current_user_id
from db.supabase_client import get_admin_client
import logging

logger = logging.getLogger(__name__)

def is_admin(user_id: str) -> bool:
    """
    Check if user is an admin.
    Uses admin client with service role key to bypass RLS.
    
    Args:
        user_id: User ID to check
        
    Returns:
        True if user is admin, False otherwise
    """
    try:
        # Use admin client (service role key) to bypass RLS
        sb = get_admin_client()
        result = sb.table("admin_users")\
            .select("user_id")\
            .eq("user_id", user_id)\
            .execute()
        
        is_admin_result = len(result.data) > 0
        logger.debug(f"Admin check for user {user_id[:8]}...: {is_admin_result}")
        return is_admin_result
    except Exception as e:
        logger.error(f"Error checking admin status for user {user_id[:8]}...: {e}")
        # Return False on error - don't break the flow
        return False

async def require_admin(current_user_id: str = Depends(get_current_user_id)) -> str:
    """
    Dependency that requires user to be an admin.
    Raises 403 if user is not admin.
    
    Use on admin-only routes:
        @router.get("/admin/users")
        async def list_users(user_id: str = Depends(require_admin)):
            # Only admins can reach here
            return get_all_users()
    
    Args:
        current_user_id: Current authenticated user ID (from JWT)
        
    Raises:
        HTTPException(403): If user is not an admin
        
    Returns:
        User ID if user is admin
    """
    if not is_admin(current_user_id):
        logger.warning(f"User {current_user_id} attempted to access admin endpoint")
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    return current_user_id

async def get_user_role(current_user_id: str = Depends(get_current_user_id)) -> Dict[str, any]:
    """
    Get user info with admin status.
    Use when you need to conditionally show admin features.
    
    Example:
        @router.get("/dashboard")
        async def get_dashboard(user_role: Dict = Depends(get_user_role)):
            data = get_user_data(user_role['user_id'])
            if user_role['is_admin']:
                data['admin_stats'] = get_admin_stats()
            return data
    
    Returns:
        Dict with user_id and is_admin flag
    """
    try:
        admin_status = is_admin(current_user_id)
        return {
            "user_id": current_user_id,
            "is_admin": admin_status
        }
    except Exception as e:
        logger.error(f"Error getting user role for {current_user_id[:8]}...: {e}")
        # Return safe default on error
        return {
            "user_id": current_user_id,
            "is_admin": False
        }

