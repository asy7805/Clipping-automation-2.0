"""
JWT Authentication Middleware for Supabase
Verifies JWT tokens and extracts user information
"""
import os
import jwt
from jwt import PyJWKClient
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict
import logging
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from db.supabase_client import get_client

logger = logging.getLogger(__name__)

# Supabase JWT settings
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

# Extract project ID from Supabase URL
# Format: https://PROJECT_ID.supabase.co
try:
    PROJECT_ID = SUPABASE_URL.split("//")[1].split(".")[0] if SUPABASE_URL else ""
except:
    PROJECT_ID = ""

# JWKS URL for verifying Supabase JWT signatures
JWKS_URL = f"{SUPABASE_URL}/auth/v1/jwks" if SUPABASE_URL else ""

def verify_jwt_token(token: str) -> Optional[Dict]:
    """
    Verify Supabase JWT token and return payload.
    
    Args:
        token: JWT token string
        
    Returns:
        Dict with user info if valid, None if invalid
    """
    if not token:
        return None
    
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        # Method 1: Verify using JWT secret (faster, for development)
        if SUPABASE_JWT_SECRET:
            try:
                payload = jwt.decode(
                    token,
                    SUPABASE_JWT_SECRET,
                    algorithms=["HS256"],
                    audience="authenticated",
                    options={"verify_aud": True, "verify_exp": True}
                )
                return payload
            except jwt.ExpiredSignatureError:
                logger.warning("JWT token has expired")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            except jwt.InvalidTokenError as e:
                logger.warning(f"Invalid JWT token: {e}")
                return None
        
        # Method 2: Verify using JWKS (production, fetches public keys)
        if JWKS_URL:
            try:
                jwks_client = PyJWKClient(JWKS_URL)
                signing_key = jwks_client.get_signing_key_from_jwt(token)
                
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256"],
                    audience="authenticated",
                    options={"verify_aud": True, "verify_exp": True}
                )
                return payload
            except jwt.ExpiredSignatureError:
                logger.warning("JWT token has expired")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            except Exception as e:
                logger.warning(f"JWKS verification failed: {e}")
                return None
        
        logger.error("No JWT verification method available (missing SUPABASE_JWT_SECRET and JWKS_URL)")
        return None
        
    except Exception as e:
        logger.error(f"Unexpected error verifying JWT: {e}")
        return None

def extract_user_id(token: str) -> Optional[str]:
    """
    Extract user_id from JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        User ID string if valid, None if invalid
    """
    payload = verify_jwt_token(token)
    
    if not payload:
        return None
    
    # Supabase stores user ID in 'sub' claim
    user_id = payload.get('sub')
    
    if not user_id:
        logger.warning("JWT payload missing 'sub' claim")
        return None
    
    return user_id

def get_user_info(token: str) -> Optional[Dict]:
    """
    Extract full user information from JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Dict with user info (id, email, role, etc.) if valid, None if invalid
    """
    payload = verify_jwt_token(token)
    
    if not payload:
        return None
    
    return {
        'id': payload.get('sub'),
        'email': payload.get('email'),
        'role': payload.get('role', 'authenticated'),
        'aud': payload.get('aud'),
        'exp': payload.get('exp'),
        'iat': payload.get('iat'),
        'app_metadata': payload.get('app_metadata', {}),
        'user_metadata': payload.get('user_metadata', {})
    }

# FastAPI dependencies
oauth2_scheme = HTTPBearer()

class User(BaseModel):
    """User model with admin flag"""
    id: str
    email: str
    is_admin: bool = False

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)) -> User:
    """
    FastAPI dependency to get current authenticated user from JWT token.
    Also checks if user is admin.
    """
    token = credentials.credentials
    payload = verify_jwt_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get('sub')
    user_email = payload.get('email')
    
    if not user_id or not user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is admin
    try:
        sb = get_client()
        admin_result = sb.table("admin_users").select("user_id").eq("user_id", user_id).execute()
        is_admin_user = len(admin_result.data) > 0
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        is_admin_user = False
    
    return User(id=user_id, email=user_email, is_admin=is_admin_user)
