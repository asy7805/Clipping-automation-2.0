#!/usr/bin/env python3
"""
Twitch Engagement Data Fetcher

This module fetches engagement metrics (views, likes, comments) from Twitch API
for clips to enable proper auto-labeling based on engagement scores.
"""

import os
import requests
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TwitchEngagementFetcher:
    """Class to fetch engagement data from Twitch API"""
    
    def __init__(self):
        """Initialize the Twitch engagement fetcher"""
        self.client_id = os.getenv('TWITCH_CLIENT_ID')
        self.client_secret = os.getenv('TWITCH_CLIENT_SECRET')
        self.access_token = None
        self.token_expires_at = None
        
    def _get_access_token(self) -> Optional[str]:
        """
        Get Twitch API access token.
        
        Returns:
            str: Access token or None if failed
        """
        if not self.client_id or not self.client_secret:
            logger.error("❌ Missing Twitch API credentials")
            return None
            
        # Check if we have a valid token
        if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at:
            return self.access_token
            
        try:
            # Get new token
            url = "https://id.twitch.tv/oauth2/token"
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'client_credentials'
            }
            
            response = requests.post(url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.token_expires_at = datetime.now() + timedelta(seconds=token_data['expires_in'] - 60)  # 1 min buffer
            
            logger.info("✅ Twitch API access token obtained")
            return self.access_token
            
        except Exception as e:
            logger.error(f"❌ Failed to get Twitch access token: {e}")
            return None
    
    def get_clip_engagement(self, clip_id: str) -> Optional[Dict]:
        """
        Get engagement data for a specific clip.
        
        Args:
            clip_id: The Twitch clip ID
            
        Returns:
            Dict: Engagement data or None if failed
        """
        access_token = self._get_access_token()
        if not access_token:
            return None
            
        try:
            url = f"https://api.twitch.tv/helix/clips"
            headers = {
                'Client-ID': self.client_id,
                'Authorization': f'Bearer {access_token}'
            }
            params = {
                'id': clip_id
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('data'):
                logger.warning(f"⚠️ No data found for clip {clip_id}")
                return None
                
            clip_data = data['data'][0]
            
            # Extract engagement metrics
            engagement_data = {
                'clip_id': clip_id,
                'views': clip_data.get('view_count', 0),
                'likes': 0,  # Twitch API doesn't provide likes for clips
                'comments': 0,  # Twitch API doesn't provide comments for clips
                'watch_time': 0.0,  # Would need to calculate from duration
                'duration': clip_data.get('duration', 0),
                'created_at': clip_data.get('created_at'),
                'broadcaster_name': clip_data.get('broadcaster_name', 'Unknown'),
                'title': clip_data.get('title', ''),
                'url': clip_data.get('url', '')
            }
            
            logger.info(f"✅ Fetched engagement data for clip {clip_id}: {engagement_data['views']} views")
            return engagement_data
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch engagement data for clip {clip_id}: {e}")
            return None
    
    def get_stream_info(self, channel_name: str) -> Optional[Dict]:
        """
        Get live stream information for a channel.
        
        Args:
            channel_name: Twitch channel username
            
        Returns:
            Dict with stream info if live, None if offline or error
        """
        access_token = self._get_access_token()
        if not access_token:
            return None
            
        try:
            # Get user ID first
            user_url = "https://api.twitch.tv/helix/users"
            headers = {
                'Client-ID': self.client_id,
                'Authorization': f'Bearer {access_token}'
            }
            params = {'login': channel_name.lower()}
            
            user_response = requests.get(user_url, headers=headers, params=params)
            user_response.raise_for_status()
            user_data = user_response.json()
            
            if not user_data.get('data'):
                logger.warning(f"⚠️ User {channel_name} not found")
                return None
            
            user_id = user_data['data'][0]['id']
            
            # Get stream info
            stream_url = "https://api.twitch.tv/helix/streams"
            stream_params = {'user_id': user_id}
            
            stream_response = requests.get(stream_url, headers=headers, params=stream_params)
            stream_response.raise_for_status()
            stream_data = stream_response.json()
            
            if stream_data.get('data') and len(stream_data['data']) > 0:
                # Stream is live
                stream = stream_data['data'][0]
                return {
                    'is_live': True,
                    'viewer_count': stream.get('viewer_count', 0),
                    'title': stream.get('title', ''),
                    'game_name': stream.get('game_name', 'Unknown'),
                    'game_id': stream.get('game_id', ''),
                    'thumbnail_url': stream.get('thumbnail_url', '').replace('{width}', '320').replace('{height}', '180'),
                    'started_at': stream.get('started_at', ''),
                    'user_id': user_id,
                    'user_name': stream.get('user_name', channel_name),
                    'language': stream.get('language', 'en')
                }
            else:
                # Stream is offline
                return {
                    'is_live': False,
                    'user_id': user_id,
                    'user_name': user_data['data'][0]['display_name']
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to fetch stream info for {channel_name}: {e}")
            return None
    
    def get_user_info(self, channel_name: str) -> Optional[Dict]:
        """
        Get user profile information.
        
        Args:
            channel_name: Twitch channel username
            
        Returns:
            Dict with user profile info or None if error
        """
        access_token = self._get_access_token()
        if not access_token:
            return None
            
        try:
            url = "https://api.twitch.tv/helix/users"
            headers = {
                'Client-ID': self.client_id,
                'Authorization': f'Bearer {access_token}'
            }
            params = {'login': channel_name.lower()}
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('data'):
                logger.warning(f"⚠️ User {channel_name} not found")
                return None
            
            user = data['data'][0]
            
            return {
                'user_id': user.get('id'),
                'display_name': user.get('display_name'),
                'login': user.get('login'),
                'profile_image_url': user.get('profile_image_url'),
                'offline_image_url': user.get('offline_image_url'),
                'broadcaster_type': user.get('broadcaster_type', ''),
                'description': user.get('description', ''),
                'created_at': user.get('created_at', '')
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch user info for {channel_name}: {e}")
            return None
    
    def get_clips_engagement_batch(self, clip_ids: List[str]) -> Dict[str, Dict]:
        """
        Get engagement data for multiple clips in batch.
        
        Args:
            clip_ids: List of Twitch clip IDs
            
        Returns:
            Dict: Mapping of clip_id to engagement data
        """
        access_token = self._get_access_token()
        if not access_token:
            return {}
            
        try:
            url = f"https://api.twitch.tv/helix/clips"
            headers = {
                'Client-ID': self.client_id,
                'Authorization': f'Bearer {access_token}'
            }
            
            # Process in batches of 100 (Twitch API limit)
            batch_size = 100
            all_engagement_data = {}
            
            for i in range(0, len(clip_ids), batch_size):
                batch = clip_ids[i:i + batch_size]
                
                params = {
                    'id': batch
                }
                
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                for clip_data in data.get('data', []):
                    clip_id = clip_data['id']
                    engagement_data = {
                        'clip_id': clip_id,
                        'views': clip_data.get('view_count', 0),
                        'likes': 0,  # Not available in Twitch API
                        'comments': 0,  # Not available in Twitch API
                        'watch_time': 0.0,
                        'duration': clip_data.get('duration', 0),
                        'created_at': clip_data.get('created_at'),
                        'broadcaster_name': clip_data.get('broadcaster_name', 'Unknown'),
                        'title': clip_data.get('title', ''),
                        'url': clip_data.get('url', '')
                    }
                    all_engagement_data[clip_id] = engagement_data
                
                logger.info(f"✅ Fetched engagement data for batch {i//batch_size + 1}: {len(data.get('data', []))} clips")
            
            return all_engagement_data
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch batch engagement data: {e}")
            return {}
    
    def calculate_engagement_score(self, engagement_data: Dict) -> float:
        """
        Calculate engagement score based on metrics.
        
        Args:
            engagement_data: Dictionary containing engagement metrics
            
        Returns:
            float: Engagement score (0-1)
        """
        views = engagement_data.get('views', 0)
        duration = engagement_data.get('duration', 0)
        
        # Simple engagement score based on views and duration
        # You can adjust this formula based on your needs
        
        if views == 0:
            return 0.0
            
        # Normalize views (cap at 10000 for scoring)
        view_score = min(views / 10000, 1.0)
        
        # Normalize duration (cap at 60 seconds for scoring)
        duration_score = min(duration / 60, 1.0)
        
        # Weighted average (views more important than duration)
        engagement_score = (view_score * 0.8) + (duration_score * 0.2)
        
        return round(engagement_score, 3)
    
    def assign_auto_label(self, engagement_score: float) -> str:
        """
        Assign auto label based on engagement score.
        
        Args:
            engagement_score: Calculated engagement score (0-1)
            
        Returns:
            str: Auto label ("0", "0.5", "1")
        """
        if engagement_score >= 0.7:
            return "1"  # High quality
        elif engagement_score >= 0.3:
            return "0.5"  # Needs review
        else:
            return "0"  # Low quality

# Global instance
engagement_fetcher = TwitchEngagementFetcher()

def get_clip_engagement(clip_id: str) -> Optional[Dict]:
    """Get engagement data for a single clip"""
    return engagement_fetcher.get_clip_engagement(clip_id)

def get_clips_engagement_batch(clip_ids: List[str]) -> Dict[str, Dict]:
    """Get engagement data for multiple clips"""
    return engagement_fetcher.get_clips_engagement_batch(clip_ids)

def calculate_engagement_score(engagement_data: Dict) -> float:
    """Calculate engagement score from engagement data"""
    return engagement_fetcher.calculate_engagement_score(engagement_data)

def assign_auto_label(engagement_score: float) -> str:
    """Assign auto label from engagement score"""
    return engagement_fetcher.assign_auto_label(engagement_score) 