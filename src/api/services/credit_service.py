"""
Credit Management Service
Handles credit operations: checking, deducting, granting, and transaction logging.
"""

import logging
from typing import Optional
from datetime import datetime, timezone, timedelta
from db.supabase_client import get_admin_client

logger = logging.getLogger(__name__)

# Constants
TRIAL_CREDITS = 20
PRO_MONTHLY_CREDITS = 150


def is_admin_user(user_id: str) -> bool:
    """
    Check if a user is an admin.
    
    Args:
        user_id: User UUID
        
    Returns:
        True if user is admin, False otherwise
    """
    try:
        sb = get_admin_client()
        admin_result = sb.table("admin_users").select("user_id").eq("user_id", user_id).execute()
        return len(admin_result.data) > 0
    except Exception as e:
        logger.warning(f"Admin check failed for user {user_id[:8]}... (non-fatal): {e}")
        return False


def get_user_credits(user_id: str) -> int:
    """
    Get current credit balance for a user.
    Admin users always return a very large number (effectively infinite).
    
    Args:
        user_id: User UUID
        
    Returns:
        Current credit balance (0 if user not found or error)
        Returns 999999 for admin users (infinite credits)
    """
    # Admin users have infinite credits
    if is_admin_user(user_id):
        return 999999
    
    try:
        sb = get_admin_client()
        result = sb.table('user_profiles').select('credits_remaining').eq('id', user_id).execute()
        
        if result.data and len(result.data) > 0:
            return int(result.data[0].get('credits_remaining', 0))
        
        # User profile doesn't exist, return 0
        return 0
    except Exception as e:
        logger.error(f"Error getting credits for user {user_id}: {e}")
        return 0


def check_has_credits(user_id: str, required: int = 1) -> bool:
    """
    Check if user has enough credits.
    Admin users always have enough credits (infinite).
    
    Args:
        user_id: User UUID
        required: Number of credits required
        
    Returns:
        True if user has enough credits, False otherwise
        Always True for admin users
    """
    # Admin users always have infinite credits
    if is_admin_user(user_id):
        return True
    
    credits = get_user_credits(user_id)
    return credits >= required


def deduct_credits(user_id: str, amount: int, transaction_type: str, clip_id: Optional[str] = None, description: Optional[str] = None) -> bool:
    """
    Deduct credits from user account and log transaction.
    Admin users bypass credit deduction (infinite credits).
    
    Args:
        user_id: User UUID
        amount: Amount to deduct (positive number)
        transaction_type: Type of transaction ('clip_created', etc.)
        clip_id: Optional clip ID associated with transaction
        description: Optional description
        
    Returns:
        True if successful, False if insufficient credits or error
        Always True for admin users (no deduction, but transaction logged)
    """
    # Admin users bypass credit deduction
    if is_admin_user(user_id):
        logger.info(f"Admin user {user_id} bypassed credit deduction for {transaction_type}")
        # Still log the transaction for audit purposes
        try:
            sb = get_admin_client()
            transaction_data = {
                'user_id': user_id,
                'amount': -amount,  # Negative for deduction
                'transaction_type': transaction_type,
                'clip_id': clip_id,
                'description': (description or f"{transaction_type}: deducted {amount} credits") + " [ADMIN BYPASS]"
            }
            sb.table('credit_transactions').insert(transaction_data).execute()
        except Exception as e:
            logger.warning(f"Failed to log admin transaction for user {user_id}: {e}")
        return True
    
    try:
        sb = get_admin_client()
        
        # Get current credits
        current_credits = get_user_credits(user_id)
        
        if current_credits < amount:
            logger.warning(f"Insufficient credits for user {user_id}: {current_credits} < {amount}")
            return False
        
        # Update credits in user_profiles table
        new_credits = current_credits - amount
        update_result = sb.table('user_profiles').update({
            'credits_remaining': new_credits
        }).eq('id', user_id).execute()
        
        if not update_result.data:
            logger.error(f"Failed to update credits for user {user_id}")
            return False
        
        # Log transaction
        transaction_data = {
            'user_id': user_id,
            'amount': -amount,  # Negative for deduction
            'transaction_type': transaction_type,
            'clip_id': clip_id,
            'description': description or f"{transaction_type}: deducted {amount} credits"
        }
        
        transaction_result = sb.table('credit_transactions').insert(transaction_data).execute()
        
        if transaction_result.data:
            logger.info(f"Deducted {amount} credits from user {user_id}. New balance: {new_credits}")
            return True
        else:
            logger.error(f"Failed to log transaction for user {user_id}")
            # Rollback credit update (best effort)
            sb.table('user_profiles').update({
                'credits_remaining': current_credits
            }).eq('id', user_id).execute()
            return False
            
    except Exception as e:
        logger.error(f"Error deducting credits for user {user_id}: {e}")
        return False


def grant_trial_credits(user_id: str) -> bool:
    """
    Grant 20 trial credits to a new user (one-time).
    
    Args:
        user_id: User UUID
        
    Returns:
        True if successful, False if trial already used or error
    """
    try:
        sb = get_admin_client()
        
        # Check if trial already used
        profile_result = sb.table('user_profiles').select('trial_used, credits_remaining, subscription_tier').eq('id', user_id).execute()
        
        if profile_result.data and len(profile_result.data) > 0:
            profile = profile_result.data[0]
            if profile.get('trial_used', False):
                logger.info(f"Trial already granted for user {user_id}")
                return False
            
            # Update existing profile
            now_utc = datetime.now(timezone.utc)
            update_result = sb.table('user_profiles').update({
                'credits_remaining': TRIAL_CREDITS,
                'trial_used': True,
                'subscription_tier': 'free_trial',
                'subscription_started_at': now_utc.isoformat().replace('+00:00', 'Z')
            }).eq('id', user_id).execute()
        else:
            # Create new profile - user doesn't exist in user_profiles table yet
            now_utc = datetime.now(timezone.utc)
            try:
                update_result = sb.table('user_profiles').insert({
                    'id': user_id,
                    'credits_remaining': TRIAL_CREDITS,
                    'trial_used': True,
                    'subscription_tier': 'free_trial',
                    'subscription_started_at': now_utc.isoformat().replace('+00:00', 'Z')
                }).execute()
            except Exception as insert_error:
                logger.error(f"Failed to insert user profile for {user_id}: {insert_error}")
                return False
        
        if not update_result.data:
            logger.error(f"Failed to grant trial credits for user {user_id}: Update/insert returned no data. Response: {update_result}")
            return False
        
        # Log transaction
        try:
            transaction_data = {
                'user_id': user_id,
                'amount': TRIAL_CREDITS,
                'transaction_type': 'trial_granted',
                'description': f'Trial credits granted: {TRIAL_CREDITS} credits'
            }
            
            transaction_result = sb.table('credit_transactions').insert(transaction_data).execute()
            if not transaction_result.data:
                logger.warning(f"Failed to log transaction for user {user_id}, but credits were granted")
        except Exception as tx_error:
            logger.warning(f"Failed to log transaction for user {user_id}: {tx_error}, but credits were granted")
        
        logger.info(f"Granted {TRIAL_CREDITS} trial credits to user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error granting trial credits for user {user_id}: {e}", exc_info=True)
        return False


def reset_pro_credits(user_id: str) -> bool:
    """
    Reset Pro user credits to 150 on monthly renewal (no rollover).
    
    Args:
        user_id: User UUID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        sb = get_admin_client()
        
        # Get current credits (for transaction log)
        current_credits = get_user_credits(user_id)
        
        # Calculate next month expiration (30 days from now)
        next_expiration = datetime.now(timezone.utc) + timedelta(days=30)
        
        # Reset to PRO_MONTHLY_CREDITS (no rollover - previous credits lost)
        update_result = sb.table('user_profiles').update({
            'credits_remaining': PRO_MONTHLY_CREDITS,
            'subscription_expires_at': next_expiration.isoformat().replace('+00:00', 'Z')
        }).eq('id', user_id).execute()
        
        if not update_result.data:
            logger.error(f"Failed to reset Pro credits for user {user_id}")
            return False
        
        # Log transaction
        transaction_data = {
            'user_id': user_id,
            'amount': PRO_MONTHLY_CREDITS,
            'transaction_type': 'pro_monthly_reset',
            'description': f'Pro monthly reset: {PRO_MONTHLY_CREDITS} credits (previous {current_credits} credits lost - no rollover)'
        }
        
        sb.table('credit_transactions').insert(transaction_data).execute()
        
        logger.info(f"Reset Pro credits for user {user_id} to {PRO_MONTHLY_CREDITS} (previous {current_credits} credits lost)")
        return True
        
    except Exception as e:
        logger.error(f"Error resetting Pro credits for user {user_id}: {e}")
        return False


def add_pay_as_you_go_credits(user_id: str, amount: int) -> bool:
    """
    Add purchased credits to pay-as-you-go user account.
    
    Args:
        user_id: User UUID
        amount: Number of credits to add
        
    Returns:
        True if successful, False otherwise
    """
    try:
        sb = get_admin_client()
        
        # Get current credits
        current_credits = get_user_credits(user_id)
        new_credits = current_credits + amount
        
        # Update credits in user_profiles table
        update_result = sb.table('user_profiles').update({
            'credits_remaining': new_credits,
            'subscription_tier': 'pay_as_you_go'
        }).eq('id', user_id).execute()
        
        if not update_result.data:
            # Try creating profile if it doesn't exist
            update_result = sb.table('user_profiles').insert({
                'id': user_id,
                'credits_remaining': amount,
                'subscription_tier': 'pay_as_you_go'
            }).execute()
            
            if not update_result.data:
                logger.error(f"Failed to add pay-as-you-go credits for user {user_id}")
                return False
            new_credits = amount
        
        # Log transaction
        transaction_data = {
            'user_id': user_id,
            'amount': amount,
            'transaction_type': 'purchase',
            'description': f'Purchased {amount} credits (pay-as-you-go)'
        }
        
        sb.table('credit_transactions').insert(transaction_data).execute()
        
        logger.info(f"Added {amount} credits to user {user_id}. New balance: {new_credits}")
        return True
        
    except Exception as e:
        logger.error(f"Error adding pay-as-you-go credits for user {user_id}: {e}")
        return False

