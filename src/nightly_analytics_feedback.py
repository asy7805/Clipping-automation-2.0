#!/usr/bin/env python3
"""
Nightly Analytics Feedback Loop

This script runs nightly to:
1. Fetch engagement data for clips from external sources (Twitch, YouTube, etc.)
2. Update the clip_analytics table with new metrics
3. Identify clips that need manual labeling based on engagement
4. Generate reports on clip performance
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import time
import random

# Add src to path
sys.path.append(str(Path(__file__).parent))

from clip_analytics import ClipAnalytics, get_clips_for_feedback, batch_update_analytics_data
from supabase_utils import get_all_clips

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/nightly_analytics.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NightlyAnalyticsFeedback:
    """Handles nightly analytics feedback loop"""
    
    def __init__(self):
        """Initialize the nightly feedback system"""
        self.analytics = ClipAnalytics()
        self.report_data = {
            "total_clips_processed": 0,
            "clips_updated": 0,
            "clips_needing_labeling": 0,
            "top_performers": [],
            "errors": []
        }
    
    def fetch_external_engagement_data(self, clip_ids: List[str]) -> List[Dict]:
        """
        Fetch engagement data from external sources (Twitch, YouTube, etc.)
        
        Args:
            clip_ids: List of clip IDs to fetch data for
            
        Returns:
            List[Dict]: List of engagement data for each clip
        """
        logger.info(f"🔍 Fetching engagement data for {len(clip_ids)} clips")
        
        engagement_data = []
        
        for clip_id in clip_ids:
            try:
                # Simulate API call delay
                time.sleep(0.1)
                
                # For now, simulate data - replace with actual API calls
                simulated_data = self.analytics.simulate_engagement_data(clip_id)
                engagement_data.append(simulated_data)
                
                logger.debug(f"✅ Fetched data for clip: {clip_id}")
                
            except Exception as e:
                logger.error(f"❌ Error fetching data for {clip_id}: {e}")
                self.report_data["errors"].append(f"Failed to fetch data for {clip_id}: {e}")
        
        logger.info(f"✅ Fetched engagement data for {len(engagement_data)} clips")
        return engagement_data
    
    def update_analytics_from_external_data(self, engagement_data: List[Dict]) -> bool:
        """
        Update clip_analytics table with external engagement data
        
        Args:
            engagement_data: List of engagement data dictionaries
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info(f"📊 Updating analytics for {len(engagement_data)} clips")
        
        try:
            success = batch_update_analytics_data(engagement_data)
            
            if success:
                self.report_data["clips_updated"] = len(engagement_data)
                logger.info(f"✅ Successfully updated analytics for {len(engagement_data)} clips")
            else:
                logger.error("❌ Failed to update analytics data")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error updating analytics: {e}")
            self.report_data["errors"].append(f"Analytics update failed: {e}")
            return False
    
    def identify_clips_for_labeling(self, min_views: int = 10, days: int = 7) -> List[Dict]:
        """
        Identify clips that need manual labeling based on engagement
        
        Args:
            min_views: Minimum views required
            days: Number of days to look back
            
        Returns:
            List[Dict]: Clips that need labeling
        """
        logger.info(f"🏷️  Identifying clips needing labeling (min_views={min_views}, days={days})")
        
        try:
            clips_needing_labeling = get_clips_for_feedback(min_views, days)
            
            self.report_data["clips_needing_labeling"] = len(clips_needing_labeling)
            
            logger.info(f"✅ Found {len(clips_needing_labeling)} clips needing labeling")
            
            # Log top clips that need labeling
            for i, clip in enumerate(clips_needing_labeling[:5]):
                logger.info(f"   {i+1}. {clip['clip_id']} - Views: {clip['views']}, Score: {clip['engagement_score']:.2f}")
            
            return clips_needing_labeling
            
        except Exception as e:
            logger.error(f"❌ Error identifying clips for labeling: {e}")
            self.report_data["errors"].append(f"Failed to identify clips for labeling: {e}")
            return []
    
    def get_top_performing_clips(self, limit: int = 10, days: int = 30) -> List[Dict]:
        """
        Get top performing clips for reporting
        
        Args:
            limit: Number of clips to return
            days: Number of days to look back
            
        Returns:
            List[Dict]: Top performing clips
        """
        logger.info(f"🏆 Getting top performing clips (limit={limit}, days={days})")
        
        try:
            top_clips = self.analytics.get_top_performing_clips(limit, days)
            self.report_data["top_performers"] = top_clips
            
            logger.info(f"✅ Found {len(top_clips)} top performing clips")
            
            # Log top performers
            for i, clip in enumerate(top_clips[:5]):
                logger.info(f"   {i+1}. {clip['clip_id']} - Score: {clip['engagement_score']:.2f}, Views: {clip['views']}")
            
            return top_clips
            
        except Exception as e:
            logger.error(f"❌ Error getting top performing clips: {e}")
            self.report_data["errors"].append(f"Failed to get top performers: {e}")
            return []
    
    def generate_nightly_report(self) -> Dict:
        """
        Generate a comprehensive nightly report
        
        Returns:
            Dict: Report data
        """
        logger.info("📋 Generating nightly report")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_clips_processed": self.report_data["total_clips_processed"],
                "clips_updated": self.report_data["clips_updated"],
                "clips_needing_labeling": self.report_data["clips_needing_labeling"],
                "top_performers_count": len(self.report_data["top_performers"]),
                "errors_count": len(self.report_data["errors"])
            },
            "top_performers": self.report_data["top_performers"][:5],
            "errors": self.report_data["errors"],
            "recommendations": self._generate_recommendations()
        }
        
        # Log report summary
        logger.info("📊 Nightly Report Summary:")
        logger.info(f"   Total clips processed: {report['summary']['total_clips_processed']}")
        logger.info(f"   Clips updated: {report['summary']['clips_updated']}")
        logger.info(f"   Clips needing labeling: {report['summary']['clips_needing_labeling']}")
        logger.info(f"   Errors: {report['summary']['errors_count']}")
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on analytics data"""
        recommendations = []
        
        if self.report_data["clips_needing_labeling"] > 0:
            recommendations.append(f"Label {self.report_data['clips_needing_labeling']} clips with sufficient engagement")
        
        if self.report_data["clips_updated"] == 0:
            recommendations.append("No clips were updated - check external data sources")
        
        if len(self.report_data["errors"]) > 0:
            recommendations.append(f"Review {len(self.report_data['errors'])} errors in the log")
        
        if len(self.report_data["top_performers"]) > 0:
            top_score = max([clip.get('engagement_score', 0) for clip in self.report_data["top_performers"]])
            if top_score > 10:
                recommendations.append("High performing clips detected - consider retraining model")
        
        return recommendations
    
    def run_nightly_feedback_loop(self) -> bool:
        """
        Run the complete nightly feedback loop
        
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info("🌙 Starting nightly analytics feedback loop")
        
        try:
            # Step 1: Get all clips that need analytics updates
            all_clips = get_all_clips()
            clip_ids = [clip['clip_id'] for clip in all_clips]
            self.report_data["total_clips_processed"] = len(clip_ids)
            
            logger.info(f"📊 Processing {len(clip_ids)} clips")
            
            # Step 2: Fetch external engagement data
            engagement_data = self.fetch_external_engagement_data(clip_ids)
            
            # Step 3: Update analytics table
            if engagement_data:
                self.update_analytics_from_external_data(engagement_data)
            
            # Step 4: Identify clips needing labeling
            clips_for_labeling = self.identify_clips_for_labeling()
            
            # Step 5: Get top performing clips
            top_clips = self.get_top_performing_clips()
            
            # Step 6: Generate report
            report = self.generate_nightly_report()
            
            # Step 7: Save report
            self._save_report(report)
            
            logger.info("✅ Nightly feedback loop completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Nightly feedback loop failed: {e}")
            self.report_data["errors"].append(f"Nightly loop failed: {e}")
            return False
    
    def _save_report(self, report: Dict):
        """Save the nightly report to a file"""
        try:
            # Ensure logs directory exists
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            
            # Save report to file
            report_file = logs_dir / f"nightly_report_{datetime.now().strftime('%Y%m%d')}.json"
            
            import json
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"📄 Report saved to {report_file}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save report: {e}")

def main():
    """Main function to run the nightly feedback loop"""
    logger.info("🚀 Starting nightly analytics feedback system")
    
    # Initialize the feedback system
    feedback_system = NightlyAnalyticsFeedback()
    
    # Run the nightly loop
    success = feedback_system.run_nightly_feedback_loop()
    
    if success:
        logger.info("🎉 Nightly feedback loop completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Nightly feedback loop failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 