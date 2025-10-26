"""
Social Media API Router.
Handles OAuth flows, account management, and posting to social platforms.
"""

import os
import secrets
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from ...db.supabase_client import get_client
from ...posting.tiktok_publisher import TikTokPublisher
from ...posting.youtube_publisher import YouTubePublisher
from ...posting.tasks import post_to_social_media

# Load environment variables
load_dotenv(Path(__file__).parent.parent.parent.parent / '.env')

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/social", tags=["social"])


# Pydantic Models
class SocialAccountCreate(BaseModel):
    platform: str = Field(..., description="Social media platform (tiktok, youtube)")
    code: str = Field(..., description="OAuth authorization code")
    state: str = Field(..., description="OAuth state parameter")
    channel_id: Optional[str] = Field(None, description="Specific YouTube channel ID to connect (optional)")


class SocialAccountResponse(BaseModel):
    id: str
    platform: str
    account_id: str
    account_name: str
    is_active: bool
    created_at: str
    updated_at: str


class PostScheduleRequest(BaseModel):
    clip_id: str = Field(..., description="ID of the clip to post")
    account_ids: List[str] = Field(..., description="List of social account IDs to post to")
    scheduled_at: Optional[str] = Field(None, description="ISO datetime for scheduled posting (null for immediate)")
    caption: Optional[str] = Field(None, description="Post caption")


class PostingQueueItem(BaseModel):
    id: str
    clip_id: str
    status: str
    scheduled_at: Optional[str]
    posted_at: Optional[str]
    post_url: Optional[str]
    caption: Optional[str]
    error_message: Optional[str]
    retry_count: int
    created_at: str
    social_account: Optional[Dict[str, Any]] = None


# OAuth State Management (in production, use Redis or database)
oauth_states = {}

# Clear expired states on startup
def cleanup_expired_states():
    """Remove expired OAuth states"""
    now = datetime.utcnow()
    expired_states = [
        state for state, data in oauth_states.items() 
        if now > data['expires_at']
    ]
    for state in expired_states:
        del oauth_states[state]

# Clean up on module load
cleanup_expired_states()

# Add a simple file-based state persistence to survive server restarts
import json
import os
from pathlib import Path

OAUTH_STATES_FILE = Path("/Users/aidanyap/Clipping-automation-2.0/oauth_states.json")

def save_oauth_states():
    """Save OAuth states to file"""
    try:
        with open(OAUTH_STATES_FILE, 'w') as f:
            # Convert datetime objects to strings for JSON serialization
            serializable_states = {}
            for state, data in oauth_states.items():
                serializable_states[state] = {
                    'platform': data['platform'],
                    'created_at': data['created_at'].isoformat(),
                    'expires_at': data['expires_at'].isoformat(),
                    'code_verifier': data.get('code_verifier')
                }
            json.dump(serializable_states, f)
    except Exception as e:
        logger.error(f"Failed to save OAuth states: {e}")

def load_oauth_states():
    """Load OAuth states from file"""
    global oauth_states
    try:
        if OAUTH_STATES_FILE.exists():
            with open(OAUTH_STATES_FILE, 'r') as f:
                serializable_states = json.load(f)
                for state, data in serializable_states.items():
                    # Convert back to datetime objects
                    oauth_states[state] = {
                        'platform': data['platform'],
                        'created_at': datetime.fromisoformat(data['created_at']),
                        'expires_at': datetime.fromisoformat(data['expires_at']),
                        'code_verifier': data.get('code_verifier')
                    }
    except Exception as e:
        logger.error(f"Failed to load OAuth states: {e}")

# Load states on startup
load_oauth_states()


@router.get("/debug/tiktok-config")
async def debug_tiktok_config():
    """Debug endpoint to check TikTok configuration."""
    return {
        "client_key": os.getenv('TIKTOK_CLIENT_KEY'),
        "client_secret": "***" if os.getenv('TIKTOK_CLIENT_SECRET') else None,
        "frontend_url": os.getenv('FRONTEND_URL'),
        "redirect_uri": f"{os.getenv('FRONTEND_URL', 'http://localhost:8080')}/auth/tiktok/callback"
    }

@router.get("/debug/oauth-states")
async def debug_oauth_states():
    """Debug endpoint to check current OAuth states."""
    return {
        "active_states": len(oauth_states),
        "states": {
            state: {
                "platform": data['platform'],
                "created_at": data['created_at'].isoformat(),
                "expires_at": data['expires_at'].isoformat(),
                "expired": datetime.utcnow() > data['expires_at']
            }
            for state, data in oauth_states.items()
        }
    }

@router.get("/debug/youtube-config")
async def debug_youtube_config():
    """Debug endpoint to check YouTube configuration."""
    return {
        "client_id": os.getenv('YOUTUBE_CLIENT_ID'),
        "client_secret": "***" if os.getenv('YOUTUBE_CLIENT_SECRET') else None,
        "frontend_url": os.getenv('FRONTEND_URL'),
        "redirect_uri": f"{os.getenv('FRONTEND_URL', 'http://localhost:8080')}/auth/youtube/callback"
    }

@router.delete("/debug/clear-states")
async def clear_oauth_states():
    """Debug endpoint to clear all OAuth states."""
    global oauth_states
    oauth_states.clear()
    return {"message": "OAuth states cleared", "count": 0}


@router.post("/auth/{platform}/initiate")
async def initiate_oauth(platform: str):
    """
    Generate OAuth URL for platform authorization.
    
    Args:
        platform: Social media platform (tiktok, youtube)
    """
    try:
        if platform not in ['tiktok', 'youtube']:
            raise HTTPException(status_code=400, detail="Unsupported platform")
        
        # Generate secure state parameter
        state = secrets.token_urlsafe(32)
        oauth_states[state] = {
            'platform': platform,
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(minutes=10)
        }
        
        # Save states to file
        save_oauth_states()
        
        # Generate OAuth URL
        if platform == 'tiktok':
            oauth_url, code_verifier = TikTokPublisher.get_oauth_url(state)
            # Store code_verifier for token exchange
            oauth_states[state]['code_verifier'] = code_verifier
        elif platform == 'youtube':
            oauth_url = YouTubePublisher.get_oauth_url(state)
        
        return {
            "oauth_url": oauth_url,
            "state": state,
            "platform": platform
        }
        
    except Exception as e:
        logger.error(f"OAuth initiation failed for {platform}: {e}")
        raise HTTPException(status_code=500, detail=f"OAuth initiation failed: {str(e)}")


@router.get("/youtube/channels")
async def get_youtube_channels(access_token: str, refresh_token: Optional[str] = None):
    """
    Fetch all YouTube channels for a Google account.
    This allows users to select which channel to connect.
    
    Args:
        access_token: YouTube OAuth access token
        refresh_token: YouTube OAuth refresh token (optional)
    
    Returns:
        List of available YouTube channels
    """
    try:
        publisher = YouTubePublisher(access_token=access_token, refresh_token=refresh_token)
        channels = await publisher.get_all_channels()
        
        return {
            "channels": channels,
            "count": len(channels)
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch YouTube channels: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch YouTube channels: {str(e)}")


@router.get("/notifications")
async def get_notifications():
    """
    Get recent posting notifications for the user.
    Returns notifications for posts that have completed (success or failure).
    """
    try:
        supabase = get_client()
        
        # For now, use a default user ID (in production, get from JWT token)
        user_id = "00000000-0000-0000-0000-000000000001"
        
        # Get recent completed posts (last 24 hours)
        from datetime import datetime, timedelta
        since = (datetime.now() - timedelta(hours=24)).isoformat()
        
        result = supabase.table('posting_queue').select(
            'id, clip_id, status, posted_at, post_url, caption, error_message, created_at, social_accounts!inner(platform, account_name)'
        ).eq('user_id', user_id).gte('updated_at', since).in_('status', ['posted', 'failed']).order('updated_at', desc=True).limit(20).execute()
        
        notifications = []
        for item in result.data:
            account = item.get('social_accounts', {})
            notifications.append({
                'id': item['id'],
                'clip_id': item['clip_id'],
                'status': item['status'],
                'platform': account.get('platform', 'unknown'),
                'account_name': account.get('account_name', 'Unknown'),
                'post_url': item.get('post_url'),
                'caption': item.get('caption'),
                'error_message': item.get('error_message'),
                'posted_at': item.get('posted_at'),
                'created_at': item['created_at']
            })
        
        return {
            "notifications": notifications,
            "count": len(notifications)
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch notifications: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch notifications: {str(e)}")


@router.post("/auth/{platform}/callback")
async def oauth_callback(platform: str, request: SocialAccountCreate):
    """
    Handle OAuth callback and store tokens.
    
    Args:
        platform: Social media platform
        request: OAuth callback data
    """
    try:
        # Validate state parameter
        if request.state not in oauth_states:
            logger.error(f"Invalid state parameter: {request.state}. Available states: {list(oauth_states.keys())}")
            raise HTTPException(status_code=400, detail="Invalid state parameter - state not found")
        
        state_data = oauth_states[request.state]
        if state_data['platform'] != platform:
            logger.error(f"State platform mismatch: expected {platform}, got {state_data['platform']}")
            raise HTTPException(status_code=400, detail="State platform mismatch")
        
        if datetime.utcnow() > state_data['expires_at']:
            del oauth_states[request.state]
            logger.error(f"State expired: {request.state}")
            raise HTTPException(status_code=400, detail="State expired - please try again")
        
        # Clean up the state immediately to prevent reuse
        del oauth_states[request.state]
        save_oauth_states()
        
        # Exchange code for tokens
        if platform == 'tiktok':
            code_verifier = state_data.get('code_verifier')
            if not code_verifier:
                raise HTTPException(status_code=400, detail="Missing code verifier for TikTok PKCE")
            token_data = await TikTokPublisher.exchange_code_for_token(request.code, request.state, code_verifier)
        elif platform == 'youtube':
            token_data = await YouTubePublisher.exchange_code_for_token(request.code, request.state)
        else:
            raise HTTPException(status_code=400, detail="Unsupported platform")
        
        # Get user info
        if platform == 'tiktok':
            publisher = TikTokPublisher(token_data['access_token'], token_data.get('refresh_token'))
            user_info = await publisher.get_user_info()
        else:
            publisher = YouTubePublisher(token_data['access_token'], token_data.get('refresh_token'))
            
            # If specific channel_id provided, use that; otherwise get default
            if request.channel_id:
                # Fetch all channels and find the specified one
                all_channels = await publisher.get_all_channels()
                selected_channel = next((ch for ch in all_channels if ch['channel_id'] == request.channel_id), None)
                
                if not selected_channel:
                    raise HTTPException(status_code=400, detail=f"Channel {request.channel_id} not found for this account")
                
                user_info = {
                    'user_id': selected_channel['channel_id'],
                    'username': selected_channel['title']
                }
            else:
                user_info = await publisher.get_user_info()
        
        # Store in database (in production, use proper user authentication)
        supabase = get_client()
        
        # For now, use a default user ID (in production, get from JWT token)
        user_id = "00000000-0000-0000-0000-000000000001"  # TODO: Get from authenticated user
        
        account_data = {
            'user_id': user_id,
            'platform': platform,
            'account_id': user_info['user_id'],
            'account_name': user_info['username'],
            'access_token': token_data['access_token'],
            'refresh_token': token_data.get('refresh_token'),
            'token_expires_at': token_data.get('expires_at').isoformat() if token_data.get('expires_at') else None,
            'is_active': True
        }
        
        # Check if account already exists
        existing = supabase.table('social_accounts').select('*').eq('user_id', user_id).eq('platform', platform).eq('account_id', user_info['user_id']).execute()
        
        if existing.data:
            # Update existing account
            result = supabase.table('social_accounts').update(account_data).eq('id', existing.data[0]['id']).execute()
        else:
            # Create new account
            result = supabase.table('social_accounts').insert(account_data).execute()
        
        return {
            "message": f"Successfully connected {platform} account",
            "account": {
                "id": result.data[0]['id'],
                "platform": platform,
                "account_name": user_info['username'],
                "is_active": True
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback failed for {platform}: {e}")
        raise HTTPException(status_code=500, detail=f"OAuth callback failed: {str(e)}")


@router.get("/accounts")
async def get_social_accounts():
    """Get all linked social accounts for user."""
    try:
        supabase = get_client()
        user_id = "00000000-0000-0000-0000-000000000001"  # TODO: Get from authenticated user
        
        response = supabase.table('social_accounts').select('*').eq('user_id', user_id).eq('is_active', True).execute()
        
        accounts = []
        for account in response.data:
            accounts.append(SocialAccountResponse(
                id=account['id'],
                platform=account['platform'],
                account_id=account['account_id'],
                account_name=account['account_name'],
                is_active=account['is_active'],
                created_at=account['created_at'],
                updated_at=account['updated_at']
            ))
        
        return {"accounts": accounts}
        
    except Exception as e:
        logger.error(f"Failed to get social accounts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get social accounts: {str(e)}")


@router.delete("/accounts/{account_id}")
async def unlink_account(account_id: str):
    """Unlink a social account."""
    try:
        supabase = get_client()
        user_id = "00000000-0000-0000-0000-000000000001"  # TODO: Get from authenticated user
        
        # Verify account belongs to user
        account_response = supabase.table('social_accounts').select('*').eq('id', account_id).eq('user_id', user_id).execute()
        
        if not account_response.data:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Deactivate account (soft delete)
        supabase.table('social_accounts').update({'is_active': False}).eq('id', account_id).execute()
        
        return {"message": "Account unlinked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unlink account: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to unlink account: {str(e)}")


@router.post("/post")
async def schedule_post(request: PostScheduleRequest):
    """
    Schedule or post immediately to social media.
    
    Args:
        request: Post scheduling data
    """
    try:
        supabase = get_client()
        user_id = "00000000-0000-0000-0000-000000000001"  # TODO: Get from authenticated user
        
        # Validate accounts belong to user
        accounts_response = supabase.table('social_accounts').select('*').in_('id', request.account_ids).eq('user_id', user_id).eq('is_active', True).execute()
        
        if len(accounts_response.data) != len(request.account_ids):
            raise HTTPException(status_code=400, detail="One or more accounts not found or inactive")
        
        # Get the storage URL for the clip
        # We need to look up the actual storage URL from the clips API
        # Let's query the clips API to get the storage URL
        
        # For now, let's use a simple approach: construct the storage URL
        # The clip_id is the id field from the clips API, but we need the storage_url
        # We'll construct the storage URL based on the pattern we observed
        
        # Create queue items for each account
        queue_items = []
        for account in accounts_response.data:
            # For now, we'll store the clip_id as is and handle the URL construction in the task
            queue_data = {
                'clip_id': request.clip_id,  # This is the id field, not the storage URL
                'user_id': user_id,
                'social_account_id': account['id'],
                'status': 'pending',
                'scheduled_at': request.scheduled_at,
                'caption': request.caption,
                'retry_count': 0
            }
            
            result = supabase.table('posting_queue').insert(queue_data).execute()
            queue_items.append(result.data[0])
            
            # If immediate post, trigger task
            if not request.scheduled_at:
                try:
                    logger.info(f"Queuing task for queue item: {result.data[0]['id']}")
                    task_result = post_to_social_media.delay(result.data[0]['id'])
                    logger.info(f"Task queued with ID: {task_result.id}")
                except Exception as e:
                    logger.error(f"Failed to queue task: {e}")
                    raise
        
        return {
            "message": f"Post scheduled for {len(queue_items)} account(s)",
            "queue_items": queue_items,
            "immediate": not request.scheduled_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to schedule post: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to schedule post: {str(e)}")


@router.get("/queue")
async def get_posting_queue(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip")
):
    """Get posting queue with filters."""
    try:
        supabase = get_client()
        user_id = "00000000-0000-0000-0000-000000000001"  # TODO: Get from authenticated user
        
        query = supabase.table('posting_queue').select('*, social_accounts(*)').eq('user_id', user_id)
        
        if status:
            query = query.eq('status', status)
        
        query = query.order('created_at', desc=True).range(offset, offset + limit - 1)
        response = query.execute()
        
        queue_items = []
        for item in response.data:
            queue_items.append(PostingQueueItem(
                id=item['id'],
                clip_id=item['clip_id'],
                status=item['status'],
                scheduled_at=item['scheduled_at'],
                posted_at=item['posted_at'],
                post_url=item['post_url'],
                caption=item['caption'],
                error_message=item['error_message'],
                retry_count=item['retry_count'],
                created_at=item['created_at'],
                social_account=item.get('social_accounts')
            ))
        
        return {
            "queue_items": queue_items,
            "total": len(queue_items),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Failed to get posting queue: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get posting queue: {str(e)}")


@router.post("/queue/{queue_id}/retry")
async def retry_queue_item(queue_id: str):
    """Retry a failed queue item."""
    try:
        supabase = get_client()
        user_id = "00000000-0000-0000-0000-000000000001"  # TODO: Get from authenticated user
        
        # Verify queue item belongs to user
        queue_response = supabase.table('posting_queue').select('*').eq('id', queue_id).eq('user_id', user_id).execute()
        
        if not queue_response.data:
            raise HTTPException(status_code=404, detail="Queue item not found")
        
        queue_item = queue_response.data[0]
        
        if queue_item['status'] not in ['failed', 'cancelled']:
            raise HTTPException(status_code=400, detail="Can only retry failed or cancelled items")
        
        # Reset status and trigger retry
        supabase.table('posting_queue').update({
            'status': 'pending',
            'error_message': None,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', queue_id).execute()
        
        post_to_social_media.delay(queue_id)
        
        return {"message": "Queue item queued for retry"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry queue item: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retry queue item: {str(e)}")


@router.delete("/queue/{queue_id}")
async def cancel_queue_item(queue_id: str):
    """Cancel a pending queue item."""
    try:
        supabase = get_client()
        user_id = "00000000-0000-0000-0000-000000000001"  # TODO: Get from authenticated user
        
        # Verify queue item belongs to user
        queue_response = supabase.table('posting_queue').select('*').eq('id', queue_id).eq('user_id', user_id).execute()
        
        if not queue_response.data:
            raise HTTPException(status_code=404, detail="Queue item not found")
        
        queue_item = queue_response.data[0]
        
        if queue_item['status'] not in ['pending', 'processing']:
            raise HTTPException(status_code=400, detail="Can only cancel pending or processing items")
        
        # Cancel the item
        supabase.table('posting_queue').update({
            'status': 'cancelled',
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', queue_id).execute()
        
        return {"message": "Queue item cancelled"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel queue item: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel queue item: {str(e)}")
