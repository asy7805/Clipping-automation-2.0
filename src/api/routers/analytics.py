"""
Analytics endpoints for clip performance and insights.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

router = APIRouter()

# Pydantic models
class AnalyticsSummary(BaseModel):
    """Analytics summary response model."""
    total_clips: int
    clip_worthy_count: int
    clip_worthy_percentage: float
    top_channels: List[Dict[str, Any]]
    recent_activity: Dict[str, Any]

class PerformanceMetrics(BaseModel):
    """Performance metrics response model."""
    avg_confidence_score: float
    model_accuracy: Optional[float] = None
    processing_time_avg: Optional[float] = None
    total_predictions: int

@router.get("/analytics/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze")
) -> AnalyticsSummary:
    """
    Get analytics summary for the specified time period.
    
    Args:
        days: Number of days to include in the analysis
        
    Returns:
        Analytics summary with key metrics
    """
    try:
        from db.supabase_client import get_client
        
        sb = get_client()
        
        # Calculate date threshold
        date_threshold = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        # Get all predictions
        try:
            all_predictions = sb.table("clip_predictions").select("*").gte("created_at", date_threshold).execute()
            predictions = all_predictions.data if all_predictions.data else []
        except:
            predictions = []
        
        # Calculate metrics
        total_clips = len(predictions)
        clip_worthy_count = sum(1 for p in predictions if p.get("clipworthy", False))
        clip_worthy_percentage = (clip_worthy_count / total_clips * 100) if total_clips > 0 else 0
        
        # Count clips by channel (extract from clip_id)
        channel_counts = {}
        for pred in predictions:
            clip_id = pred.get("clip_id", "")
            # Try to extract channel name from clip_id pattern
            for channel in ["nater4l", "jordanbentley", "stableronaldo", "asspizza730", "shroud", "jasontheween"]:
                if channel in clip_id.lower():
                    if channel not in channel_counts:
                        channel_counts[channel] = {"total": 0, "worthy": 0}
                    channel_counts[channel]["total"] += 1
                    if pred.get("clipworthy", False):
                        channel_counts[channel]["worthy"] += 1
                    break
        
        # Build top channels list
        top_channels = [
            {
                "channel": channel,
                "clips": stats["total"],
                "worthy_clips": stats["worthy"]
            }
            for channel, stats in sorted(channel_counts.items(), key=lambda x: x[1]["total"], reverse=True)[:3]
        ]
        
        # Count today's clips
        try:
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            today_predictions = sb.table("clip_predictions").select("*").gte("created_at", today).execute()
            clips_today = len(today_predictions.data) if today_predictions.data else 0
        except:
            clips_today = 0
        
        return AnalyticsSummary(
            total_clips=total_clips,
            clip_worthy_count=clip_worthy_count,
            clip_worthy_percentage=round(clip_worthy_percentage, 2),
            top_channels=top_channels,
            recent_activity={
                "clips_today": clips_today,
                "clips_this_week": total_clips,
                "last_updated": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        print(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")

@router.get("/analytics/performance", response_model=PerformanceMetrics)
async def get_performance_metrics() -> PerformanceMetrics:
    """
    Get model performance metrics.
    
    Returns:
        Performance metrics for the ML model
    """
    try:
        from db.supabase_client import get_client
        
        sb = get_client()
        
        # Get all predictions
        try:
            all_predictions = sb.table("clip_predictions").select("score").execute()
            predictions = all_predictions.data if all_predictions.data else []
        except:
            predictions = []
        
        # Calculate average confidence score
        total_predictions = len(predictions)
        if total_predictions > 0:
            avg_score = sum(p.get("score", 0) for p in predictions) / total_predictions
        else:
            avg_score = 0.0
        
        return PerformanceMetrics(
            avg_confidence_score=round(avg_score, 3),
            model_accuracy=None,  # Would need ground truth labels
            processing_time_avg=None,  # Would need timing logs
            total_predictions=total_predictions
        )
        
    except Exception as e:
        print(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")

@router.get("/analytics/channels")
async def get_channel_analytics(
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(7, ge=1, le=365)
) -> List[Dict[str, Any]]:
    """
    Get analytics for top performing channels.
    
    Args:
        limit: Maximum number of channels to return
        days: Number of days to analyze
        
    Returns:
        List of channel analytics
    """
    try:
        # TODO: Implement actual channel analytics
        # This is a placeholder response
        return [
            {
                "channel_name": "example_channel_1",
                "total_clips": 25,
                "worthy_clips": 8,
                "worthy_percentage": 32.0,
                "avg_confidence": 0.89,
                "last_activity": datetime.utcnow().isoformat()
            },
            {
                "channel_name": "example_channel_2", 
                "total_clips": 20,
                "worthy_clips": 6,
                "worthy_percentage": 30.0,
                "avg_confidence": 0.85,
                "last_activity": (datetime.utcnow() - timedelta(hours=2)).isoformat()
            }
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get channel analytics: {str(e)}")

@router.get("/analytics/trends")
async def get_analytics_trends(
    days: int = Query(30, ge=1, le=365)
) -> Dict[str, Any]:
    """
    Get trending analytics data over time.
    
    Args:
        days: Number of days to analyze for trends
        
    Returns:
        Trending analytics data
    """
    try:
        # TODO: Implement actual trend analysis
        # This is a placeholder response
        return {
            "period_days": days,
            "trends": {
                "clips_per_day": [5, 8, 12, 15, 18, 20, 22],
                "worthy_percentage": [25, 28, 30, 32, 35, 33, 30],
                "avg_confidence": [0.82, 0.84, 0.86, 0.87, 0.88, 0.87, 0.86]
            },
            "insights": [
                "Clip detection rate has increased by 15% this week",
                "Average confidence scores are trending upward",
                "Top performing time slots: 7-9 PM, 2-4 PM"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trends: {str(e)}")
