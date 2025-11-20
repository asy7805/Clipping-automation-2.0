#!/usr/bin/env python3
"""
Pro subscription renewal processing job.
Handles Pro subscription renewals and credit resets (no rollover).

Run this daily via cron or scheduled task.
Example cron: 0 1 * * * /path/to/python /path/to/process_pro_renewals.py

Note: Actual payment processing is handled via Stripe webhooks.
This job processes renewals after payment succeeds.
"""

import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.db.supabase_client import get_admin_client
from src.api.services.subscription_service import expire_subscription, get_subscription_info
from src.api.services.credit_service import reset_pro_credits

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_pro_renewals():
    """
    Process Pro subscription renewals and expirations.
    """
    try:
        os.environ["USE_SERVICE_ROLE"] = "true"
        sb = get_admin_client()
        
        now = datetime.now(timezone.utc)
        
        # Get Pro users whose subscriptions expire soon (within 1 day) or have expired
        pro_users = sb.table('user_profiles')\
            .select('id, subscription_expires_at, cancelled_at')\
            .eq('subscription_tier', 'pro')\
            .not_.is_('subscription_expires_at', 'null')\
            .lte('subscription_expires_at', (now + timedelta(days=1)).isoformat())\
            .execute()
        
        if not pro_users.data:
            logger.info("No Pro subscriptions expiring soon")
            return
        
        logger.info(f"Found {len(pro_users.data)} Pro subscriptions to process")
        
        renewed_count = 0
        expired_count = 0
        
        for user_profile in pro_users.data:
            user_id = user_profile['id']
            expires_at_str = user_profile.get('subscription_expires_at')
            cancelled_at = user_profile.get('cancelled_at')
            
            try:
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                
                # Check if subscription has expired
                if expires_at < now:
                    # Subscription expired
                    if cancelled_at:
                        # User cancelled - expire subscription (no free credits)
                        logger.info(f"Expiring cancelled Pro subscription for user {user_id}")
                        expire_subscription(user_id)
                        expired_count += 1
                    else:
                        # Payment failed or subscription ended - expire (no free credits)
                        logger.info(f"Expiring Pro subscription for user {user_id} (expired at {expires_at})")
                        expire_subscription(user_id)
                        expired_count += 1
                else:
                    # Subscription renewing soon (within 1 day)
                    # In production, this would be triggered by Stripe webhook after payment succeeds
                    # For now, we'll log that renewal is needed
                    logger.info(f"Pro subscription for user {user_id} expires soon at {expires_at}")
                    logger.info("Note: Renewal should be handled by Stripe webhook (invoice.payment_succeeded)")
                    # Don't auto-renew here - wait for Stripe webhook
                    
            except Exception as e:
                logger.error(f"Error processing Pro subscription for user {user_id}: {e}")
        
        logger.info(f"Renewal processing complete: {expired_count} expired")
        
    except Exception as e:
        logger.error(f"Error during Pro renewal processing: {e}", exc_info=True)
        raise


def handle_stripe_renewal(user_id: str):
    """
    Handle Pro subscription renewal after successful Stripe payment.
    This function should be called from Stripe webhook handler.
    
    Args:
        user_id: User UUID whose subscription is renewing
    """
    try:
        logger.info(f"Processing Stripe renewal for user {user_id}")
        
        # Reset credits to 150 (no rollover)
        if reset_pro_credits(user_id):
            # Update expiration date to 30 days from now
            os.environ["USE_SERVICE_ROLE"] = "true"
            sb = get_admin_client()
            
            new_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
            sb.table('user_profiles').update({
                'subscription_expires_at': new_expires_at.isoformat(),
                'cancelled_at': None  # Clear cancellation if resubscribing
            }).eq('id', user_id).execute()
            
            logger.info(f"Successfully renewed Pro subscription for user {user_id}, expires at {new_expires_at}")
            return True
        else:
            logger.error(f"Failed to reset credits for user {user_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error handling Stripe renewal for user {user_id}: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    logger.info("Starting Pro subscription renewal processing job...")
    process_pro_renewals()
    logger.info("Renewal processing job completed")

