"""
Subscription management endpoints.
Handles subscription status, trial granting, and credit transactions.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime

from db.supabase_client import get_client, get_admin_client
from ..middleware.auth import get_current_user, User
from ..middleware.admin import require_admin
from ..services.credit_service import get_user_credits, grant_trial_credits
from ..services.subscription_service import (
    get_user_subscription_tier,
    has_trial_been_used,
    is_pro_user,
    is_trial_user,
    get_subscription_info
)

logger = logging.getLogger(__name__)
router = APIRouter()


class SubscriptionStatusResponse(BaseModel):
    tier: str
    credits_remaining: int
    trial_used: bool
    subscription_started_at: Optional[str]
    subscription_expires_at: Optional[str]
    cancelled_at: Optional[str]
    is_cancelled: bool


class CreditTransactionResponse(BaseModel):
    id: str
    amount: int
    transaction_type: str
    description: Optional[str]
    clip_id: Optional[str]
    created_at: str


@router.get("/subscription/status")
async def get_subscription_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get current subscription status and credits for authenticated user.
    """
    try:
        return get_subscription_info(current_user.id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting subscription status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get subscription status: {str(e)}")


@router.post("/subscription/grant-trial")
async def grant_trial(
    user_id: Optional[str] = None,
    admin_user_id: str = Depends(require_admin)
) -> dict:
    """
    Manually grant trial credits to a user (admin only).
    Used for testing or manual trial grants.
    """
    try:
        target_user_id = user_id or admin_user_id
        
        if grant_trial_credits(target_user_id):
            credits = get_user_credits(target_user_id)
            return {
                "message": f"Trial credits granted to user {target_user_id}",
                "user_id": target_user_id,
                "credits": credits or 0
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Trial already granted or failed to grant trial credits"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error granting trial: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to grant trial: {str(e)}")


@router.get("/subscription/transactions")
async def get_credit_transactions(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
):
    """
    Get credit transaction history for authenticated user.
    """
    try:
        sb = get_client()
        result = sb.table('credit_transactions')\
            .select('*')\
            .eq('user_id', current_user.id)\
            .order('created_at', desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        transactions = []
        for tx in (result.data or []):
            transactions.append(CreditTransactionResponse(
                id=tx['id'],
                amount=tx['amount'],
                transaction_type=tx['transaction_type'],
                description=tx.get('description'),
                clip_id=tx.get('clip_id'),
                created_at=tx['created_at']
            ))
        
        return transactions
    except Exception as e:
        logger.error(f"Error getting transactions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get transactions: {str(e)}")


@router.get("/subscription/check-trial")
async def check_trial_status(
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Check if user has used their trial.
    """
    try:
        trial_used = has_trial_been_used(current_user.id)
        credits = get_user_credits(current_user.id)
        tier = get_user_subscription_tier(current_user.id)
        
        return {
            "trial_used": trial_used,
            "credits_remaining": credits or 0,
            "tier": tier,
            "can_grant_trial": not trial_used and tier == 'free_trial'
        }
    except Exception as e:
        logger.error(f"Error checking trial status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check trial status: {str(e)}")


@router.post("/subscription/claim-trial")
async def claim_trial(
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Claim trial credits (one-time, automatic on first call).
    Can be called after user signup or on first app use.
    """
    try:
        # Check if trial already used
        if has_trial_been_used(current_user.id):
            credits = get_user_credits(current_user.id)
            tier = get_user_subscription_tier(current_user.id)
            return {
                "message": "Trial already claimed",
                "credits_remaining": credits or 0,
                "tier": tier,
                "trial_used": True
            }
        
        # Grant trial credits
        if grant_trial_credits(current_user.id):
            credits = get_user_credits(current_user.id)
            return {
                "message": "Trial credits granted successfully",
                "credits_remaining": credits or 0,
                "tier": "free_trial",
                "trial_used": True
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to grant trial credits"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error claiming trial: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to claim trial: {str(e)}")

