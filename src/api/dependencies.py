"""
FastAPI Dependencies for Authentication
Provides dependency functions for protecting routes
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict
import logging

from .middleware.auth import extract_user_id, get_user_info

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)

async def get_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[str]:
    """
    Extract JWT token from Authorization header.
    
    Returns:
        Token string if present, None if not
    """
    if not credentials:
        return None
    return credentials.credentials

async def get_current_user_id(token: Optional[str] = Depends(get_token)) -> str:
    """
    Get current user ID from JWT token.
    Use this dependency on protected routes that need user_id.
    
    Example:
        @router.get("/clips")
        async def get_clips(user_id: str = Depends(get_current_user_id)):
            clips = db.query("SELECT * FROM clips WHERE user_id = ?", [user_id])
            return clips
    
    Raises:
        HTTPException(401): If token is missing or invalid
        
    Returns:
        User ID string
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = extract_user_id(token)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id

async def get_current_user(token: Optional[str] = Depends(get_token)) -> Dict:
    """
    Get full current user information from JWT token.
    Use this dependency when you need more than just the user_id.
    
    Example:
        @router.get("/profile")
        async def get_profile(user: Dict = Depends(get_current_user)):
            email = user['email']
            return {"email": email, "id": user['id']}
    
    Raises:
        HTTPException(401): If token is missing or invalid
        
    Returns:
        Dict with user info (id, email, role, etc.)
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_info = get_user_info(token)
    
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_info

async def get_optional_user_id(token: Optional[str] = Depends(get_token)) -> Optional[str]:
    """
    Get user ID from token if present, None if not.
    Use this for routes that work with or without authentication.
    
    Example:
        @router.get("/public-clips")
        async def get_clips(user_id: Optional[str] = Depends(get_optional_user_id)):
            if user_id:
                # Show user's private clips
                clips = db.query("SELECT * FROM clips WHERE user_id = ?", [user_id])
            else:
                # Show public clips only
                clips = db.query("SELECT * FROM clips WHERE is_public = true")
            return clips
    
    Returns:
        User ID string if authenticated, None if not
    """
    if not token:
        return None
    
    return extract_user_id(token)
