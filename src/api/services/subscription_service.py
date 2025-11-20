"""
Subscription Management Service
Handles subscription tier operations: checking, upgrading, expiring subscriptions.
"""

import logging
from typing import Optional
from datetime import datetime, timezone, timedelta
from db.supabase_client import get_admin_client

logger = logging.getLogger(__name__)


def _is_admin_user(user_id: str) -> bool:
    """
    Check if a user is an admin (helper function).
    
    Args:
        user_id: User UUID
        
    Returns:
        True if user is admin, False otherwise
    """
    try:
        from .credit_service import is_admin_user
        return is_admin_user(user_id)
    except Exception as e:
        logger.warning(f"Admin check failed for user {user_id[:8]}... (non-fatal): {e}")
        return False


def get_user_subscription_tier(user_id: str) -> str:
    """
    Get current subscription tier for a user.
    Admin users always return 'pro'.
    
    Args:
        user_id: User UUID
        
    Returns:
        Subscription tier: 'free_trial', 'pro', 'pay_as_you_go', or 'expired'
        Always returns 'pro' for admin users
    """
    # Admin users always have Pro tier
    if _is_admin_user(user_id):
        return 'pro'
    
    try:
        sb = get_admin_client()
        result = sb.table('user_profiles').select('subscription_tier').eq('id', user_id).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0].get('subscription_tier', 'free_trial')
        
        # User profile doesn't exist, default to free_trial
        return 'free_trial'
    except Exception as e:
        logger.error(f"Error getting subscription tier for user {user_id}: {e}")
        return 'free_trial'


def is_pro_user(user_id: str) -> bool:
    """
    Check if user has Pro subscription.
    Admin users always return True.
    
    Args:
        user_id: User UUID
        
    Returns:
        True if Pro tier or admin, False otherwise
    """
    # Admin users always have Pro access
    if _is_admin_user(user_id):
        return True
    
    tier = get_user_subscription_tier(user_id)
    return tier == 'pro'


def is_trial_user(user_id: str) -> bool:
    """
    Check if user is on free trial.
    Admin users always return False (they have Pro tier).
    
    Args:
        user_id: User UUID
        
    Returns:
        True if free trial tier, False otherwise (always False for admins)
    """
    # Admin users are not trial users
    if _is_admin_user(user_id):
        return False
    
    tier = get_user_subscription_tier(user_id)
    return tier == 'free_trial'


def has_trial_been_used(user_id: str) -> bool:
    """
    Check if trial credits have already been granted.
    
    Args:
        user_id: User UUID
        
    Returns:
        True if trial already used, False otherwise
    """
    try:
        sb = get_admin_client()
        result = sb.table('user_profiles').select('trial_used').eq('id', user_id).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0].get('trial_used', False)
        
        # Profile doesn't exist, trial not used yet
        return False
    except Exception as e:
        logger.error(f"Error checking trial status for user {user_id}: {e}")
        return False


def expire_subscription(user_id: str) -> None:
    """
    Expire user subscription (set to 'expired', credits to 0).
    No free credits granted on expiration.
    
    Args:
        user_id: User UUID
    """
    try:
        sb = get_admin_client()
        
        update_result = sb.table('user_profiles').update({
            'subscription_tier': 'expired',
            'credits_remaining': 0,
            'subscription_expires_at': None
        }).eq('id', user_id).execute()
        
        if update_result.data:
            logger.info(f"Expired subscription for user {user_id}")
        else:
            logger.warning(f"Failed to expire subscription for user {user_id} (profile may not exist)")
            
    except Exception as e:
        logger.error(f"Error expiring subscription for user {user_id}: {e}")


def upgrade_to_pro(user_id: str, expires_at: Optional[datetime] = None) -> bool:
    """
    Upgrade user to Pro tier and grant 150 credits.
    
    Args:
        user_id: User UUID
        expires_at: Optional expiration date (defaults to 30 days from now)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        from .credit_service import reset_pro_credits
        
        sb = get_admin_client()
        
        # Default to 30 days from now if not provided
        if expires_at is None:
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        
        # Update subscription tier and expiration
        update_result = sb.table('user_profiles').update({
            'subscription_tier': 'pro',
            'subscription_started_at': datetime.now(timezone.utc).isoformat(),
            'subscription_expires_at': expires_at.isoformat(),
            'cancelled_at': None  # Clear cancellation if resubscribing
        }).eq('id', user_id).execute()
        
        if not update_result.data:
            # Try creating profile if it doesn't exist
            update_result = sb.table('user_profiles').insert({
                'id': user_id,
                'subscription_tier': 'pro',
                'subscription_started_at': datetime.now(timezone.utc).isoformat(),
                'subscription_expires_at': expires_at.isoformat()
            }).execute()
            
            if not update_result.data:
                logger.error(f"Failed to upgrade user {user_id} to Pro")
                return False
        
        # Grant Pro credits (150, no rollover)
        reset_pro_credits(user_id)
        
        logger.info(f"Upgraded user {user_id} to Pro tier, expires at {expires_at}")
        return True
        
    except Exception as e:
        logger.error(f"Error upgrading user {user_id} to Pro: {e}")
        return False


def upgrade_to_pay_as_you_go(user_id: str) -> bool:
    """
    Set user subscription tier to pay-as-you-go.
    
    Args:
        user_id: User UUID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        sb = get_admin_client()
        
        update_result = sb.table('user_profiles').update({
            'subscription_tier': 'pay_as_you_go',
            'subscription_started_at': datetime.now(timezone.utc).isoformat(),
            'subscription_expires_at': None  # Pay-as-you-go doesn't expire
        }).eq('id', user_id).execute()
        
        if not update_result.data:
            # Try creating profile if it doesn't exist
            update_result = sb.table('user_profiles').insert({
                'id': user_id,
                'subscription_tier': 'pay_as_you_go',
                'subscription_started_at': datetime.now(timezone.utc).isoformat()
            }).execute()
            
            if not update_result.data:
                logger.error(f"Failed to set pay-as-you-go tier for user {user_id}")
                return False
        
        logger.info(f"Set user {user_id} to pay-as-you-go tier")
        return True
        
    except Exception as e:
        logger.error(f"Error setting pay-as-you-go tier for user {user_id}: {e}")
        return False


def cancel_pro_subscription(user_id: str) -> bool:
    """
    Cancel Pro subscription (remains active until expiration date).
    
    Args:
        user_id: User UUID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        sb = get_admin_client()
        
        # Get current expiration date
        result = sb.table('user_profiles').select('subscription_expires_at').eq('id', user_id).execute()
        
        if not result.data:
            logger.warning(f"User profile not found for {user_id}")
            return False
        
        expires_at = result.data[0].get('subscription_expires_at')
        
        # Mark as cancelled but keep subscription active until expiration
        update_result = sb.table('user_profiles').update({
            'cancelled_at': datetime.now(timezone.utc).isoformat()
        }).eq('id', user_id).execute()
        
        if update_result.data:
            logger.info(f"Cancelled Pro subscription for user {user_id} (active until {expires_at})")
            return True
        else:
            logger.error(f"Failed to cancel subscription for user {user_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error cancelling subscription for user {user_id}: {e}")
        return False


def get_subscription_info(user_id: str) -> dict:
    """
    Get complete subscription information for a user.
    Admin users always return Pro tier with unlimited credits.
    
    Args:
        user_id: User UUID
        
    Returns:
        Dictionary with subscription details
        Admin users get 'pro' tier and 999999 credits
    """
    # Admin users always have Pro tier and unlimited credits
    if _is_admin_user(user_id):
        return {
            'tier': 'pro',
            'credits_remaining': 999999,  # Unlimited credits for admins
            'trial_used': True,  # Admins don't need trial
            'subscription_started_at': None,
            'subscription_expires_at': None,
            'cancelled_at': None,
            'is_cancelled': False
        }
    
    try:
        from .credit_service import get_user_credits
        sb = get_admin_client()
        result = sb.table('user_profiles').select('*').eq('id', user_id).execute()
        
        if result.data and len(result.data) > 0:
            profile = result.data[0]
            credits = get_user_credits(user_id)  # This already handles admin check
            return {
                'tier': profile.get('subscription_tier', 'free_trial'),
                'credits_remaining': credits,
                'trial_used': profile.get('trial_used', False),
                'subscription_started_at': profile.get('subscription_started_at'),
                'subscription_expires_at': profile.get('subscription_expires_at'),
                'cancelled_at': profile.get('cancelled_at'),
                'is_cancelled': profile.get('cancelled_at') is not None
            }
        
        # Return default values if profile doesn't exist
        return {
            'tier': 'free_trial',
            'credits_remaining': 0,
            'trial_used': False,
            'subscription_started_at': None,
            'subscription_expires_at': None,
            'cancelled_at': None,
            'is_cancelled': False
        }
    except Exception as e:
        logger.error(f"Error getting subscription info for user {user_id}: {e}")
        return {
            'tier': 'free_trial',
            'credits_remaining': 0,
            'trial_used': False,
            'subscription_started_at': None,
            'subscription_expires_at': None,
            'cancelled_at': None,
            'is_cancelled': False
        }

