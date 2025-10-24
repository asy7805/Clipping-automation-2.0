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

@router.get("/analytics/summary")
async def get_analytics_summary(
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze")
) -> Dict[str, Any]:
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
        
        # Use the clips API to get real data instead of reading storage directly
        try:
            # Get clips using the same logic as the clips endpoint
            import requests
            clips_response = requests.get("http://localhost:8000/api/v1/clips?limit=1000")
            clips_data = clips_response.json() if clips_response.status_code == 200 else []
            
            # Calculate date threshold
            date_threshold = datetime.utcnow() - timedelta(days=days)
            
            # Filter clips by date
            recent_clips = []
            total_size = 0
            channel_counts = {}
            scores = []
            
            for clip in clips_data:
                created_at = clip.get('created_at', '')
                
                # Parse date
                try:
                    clip_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if clip_date >= date_threshold:
                        recent_clips.append(clip)
                        total_size += clip.get('file_size', 0)
                        
                        # Count by channel
                        channel_name = clip.get('channel_name', '')
                        if channel_name:
                            if channel_name not in channel_counts:
                                channel_counts[channel_name] = 0
                            channel_counts[channel_name] += 1
                        
                        # Use actual confidence score
                        score = clip.get('confidence_score', 0.5)
                        scores.append(score)
                except Exception as e:
                    print(f"Error processing clip {clip.get('id', '')}: {e}")
                    continue
            
            # Calculate metrics
            total_clips = len(recent_clips)
            avg_score = sum(scores) / len(scores) if scores else 0
            high_score_clips = len([s for s in scores if s >= 0.7])
            storage_used_gb = total_size / (1024 ** 3)
            
            # Count today's clips
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            clips_today = len([c for c in recent_clips 
                             if datetime.fromisoformat(c.get('created_at', '').replace('Z', '+00:00')) >= today])
            
            # Build top channels
            top_channels = [
                {"channel": channel, "clips": count}
                for channel, count in sorted(channel_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            ]
            
            return {
                "active_monitors": len(channel_counts),  # Number of channels with clips
                "clips_today": clips_today,
                "clips_this_week": total_clips,
                "storage_used_gb": round(storage_used_gb, 2),
                "avg_score": round(avg_score, 2),
                "trend": 15,  # Placeholder trend
                "top_channels": top_channels,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as storage_error:
            print(f"Storage error: {storage_error}")
            # Fallback to database if storage fails
            return {
                "active_monitors": 0,
                "clips_today": 0,
                "clips_this_week": 0,
                "storage_used_gb": 0.0,
                "avg_score": 0.0,
                "trend": 0,
                "top_channels": [],
                "last_updated": datetime.utcnow().isoformat()
            }
        
    except Exception as e:
        print(f"Error getting analytics: {e}")
        return {
            "active_monitors": 0,
            "clips_today": 0,
            "clips_this_week": 0,
            "storage_used_gb": 0.0,
            "avg_score": 0.0,
            "trend": 0,
            "top_channels": [],
            "last_updated": datetime.utcnow().isoformat()
        }

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
