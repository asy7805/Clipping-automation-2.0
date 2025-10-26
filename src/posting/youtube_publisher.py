"""
YouTube Data API v3 integration for uploading Shorts.
Handles OAuth, token refresh, and video uploads as YouTube Shorts.
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from .base_publisher import BaseSocialPublisher

logger = logging.getLogger(__name__)


class YouTubePublisher(BaseSocialPublisher):
    """YouTube Data API v3 publisher for Shorts."""
    
    def __init__(self, access_token: str, refresh_token: Optional[str] = None):
        super().__init__(access_token, refresh_token)
        self.client_id = os.getenv('YOUTUBE_CLIENT_ID')
        self.client_secret = os.getenv('YOUTUBE_CLIENT_SECRET')
        self.youtube_service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize YouTube API service with credentials."""
        try:
            credentials = Credentials(
                token=self.access_token,
                refresh_token=self.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            
            self.youtube_service = build('youtube', 'v3', credentials=credentials)
            logger.info("YouTube service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize YouTube service: {e}")
            raise Exception(f"YouTube service initialization failed: {str(e)}")
    
    async def upload_video(self, video_path: str, **kwargs) -> Dict[str, Any]:
        """
        Upload a video as YouTube Short.
        
        Args:
            video_path: Path to the video file
            title: Video title (optional)
            description: Video description (optional)
            tags: List of tags (optional)
            privacy_status: public, private, or unlisted (default: public)
            
        Returns:
            Dict containing YouTube response with video_id and video_url
        """
        try:
            # Ensure we have a valid token
            await self.ensure_valid_token()
            
            # Prepare video metadata
            title = kwargs.get('title', 'Auto-generated clip')
            description = kwargs.get('description', '')
            tags = kwargs.get('tags', [])
            privacy_status = kwargs.get('privacy_status', 'public')
            
            # YouTube Shorts requirements
            # - Duration must be 60 seconds or less
            # - Aspect ratio should be 9:16 (vertical)
            # - Use #Shorts in title for better discoverability
            
            if not title.endswith('#Shorts'):
                title = f"{title} #Shorts"
            
            body = {
                'snippet': {
                    'title': title[:100],  # YouTube title limit
                    'description': description[:5000],  # YouTube description limit
                    'tags': tags[:15],  # YouTube tags limit
                    'categoryId': '22'  # People & Blogs category
                },
                'status': {
                    'privacyStatus': privacy_status,
                    'selfDeclaredMadeForKids': False
                }
            }
            
            # Create media upload object
            media = MediaFileUpload(
                video_path,
                chunksize=-1,
                resumable=True,
                mimetype='video/mp4'
            )
            
            logger.info(f"Uploading video to YouTube: {video_path}")
            
            # Execute upload
            insert_request = self.youtube_service.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = insert_request.next_chunk()
                if status:
                    logger.info(f"YouTube upload progress: {int(status.progress() * 100)}%")
            
            if 'id' in response:
                video_id = response['id']
                video_url = f"https://www.youtube.com/shorts/{video_id}"
                
                logger.info(f"Successfully uploaded video to YouTube: {video_id}")
                
                return {
                    'video_id': video_id,
                    'video_url': video_url,
                    'platform': 'youtube',
                    'status': 'posted',
                    'title': response['snippet']['title'],
                    'description': response['snippet']['description']
                }
            else:
                raise Exception("YouTube upload failed: No video ID in response")
                
        except HttpError as e:
            logger.error(f"YouTube API error: {e}")
            error_details = e.error_details[0] if e.error_details else {}
            error_message = error_details.get('message', str(e))
            raise Exception(f"YouTube upload failed: {error_message}")
        except Exception as e:
            logger.error(f"YouTube upload error: {e}")
            raise Exception(self.format_error_message(e))
    
    async def refresh_access_token(self) -> str:
        """Refresh YouTube access token using refresh token."""
        if not self.refresh_token:
            raise Exception("No refresh token available")
        
        try:
            credentials = Credentials(
                token=None,
                refresh_token=self.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            
            # Refresh the credentials
            credentials.refresh(None)
            
            new_access_token = credentials.token
            self.token_expires_at = credentials.expiry
            
            logger.info("Successfully refreshed YouTube access token")
            return new_access_token
            
        except Exception as e:
            logger.error(f"YouTube refresh error: {e}")
            raise Exception(f"YouTube token refresh failed: {str(e)}")
    
    def validate_credentials(self) -> bool:
        """Validate YouTube credentials by checking user info."""
        try:
            # Make a simple API call to validate token
            request = self.youtube_service.channels().list(part="snippet", mine=True)
            response = request.execute()
            return 'items' in response and len(response['items']) > 0
            
        except Exception as e:
            logger.error(f"YouTube credential validation failed: {e}")
            return False
    
    async def get_user_info(self) -> Dict[str, Any]:
        """Get YouTube user information."""
        try:
            await self.ensure_valid_token()
            
            request = self.youtube_service.channels().list(
                part="snippet,statistics",
                mine=True
            )
            response = request.execute()
            
            if not response.get('items'):
                raise Exception("No YouTube channel found")
            
            channel = response['items'][0]
            snippet = channel['snippet']
            statistics = channel.get('statistics', {})
            
            return {
                'user_id': channel['id'],
                'username': snippet.get('title', ''),
                'avatar_url': snippet.get('thumbnails', {}).get('default', {}).get('url', ''),
                'subscriber_count': int(statistics.get('subscriberCount', 0)),
                'video_count': int(statistics.get('videoCount', 0)),
                'view_count': int(statistics.get('viewCount', 0))
            }
            
        except Exception as e:
            logger.error(f"YouTube user info error: {e}")
            raise Exception(f"Failed to get YouTube user info: {str(e)}")
    
    async def get_all_channels(self) -> list[Dict[str, Any]]:
        """
        Fetch all YouTube channels associated with this Google account.
        This allows users to select which channel to connect.
        
        Returns:
            List of channel info dictionaries with id, title, and thumbnail
        """
        try:
            await self.ensure_valid_token()
            
            # Get all channels for this account
            request = self.youtube_service.channels().list(
                part='snippet,statistics',
                mine=True,
                maxResults=50  # Maximum allowed by YouTube API
            )
            response = request.execute()
            
            if not response.get('items'):
                return []
            
            channels = []
            for channel in response['items']:
                snippet = channel['snippet']
                statistics = channel.get('statistics', {})
                
                channels.append({
                    'channel_id': channel['id'],
                    'title': snippet.get('title', ''),
                    'description': snippet.get('description', ''),
                    'subscriber_count': int(statistics.get('subscriberCount', 0)),
                    'video_count': int(statistics.get('videoCount', 0)),
                    'thumbnail': snippet.get('thumbnails', {}).get('default', {}).get('url', ''),
                    'custom_url': snippet.get('customUrl', ''),
                })
            
            logger.info(f"Found {len(channels)} YouTube channel(s) for this account")
            return channels
            
        except Exception as e:
            logger.error(f"Error getting YouTube channels: {e}")
            raise Exception(f"Failed to get YouTube channels: {str(e)}")
    
    @staticmethod
    def get_oauth_url(state: str) -> str:
        """Generate YouTube OAuth URL for user authorization."""
        client_id = os.getenv('YOUTUBE_CLIENT_ID')
        # Force correct frontend URL for OAuth
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:8080')
        if '8081' in frontend_url:
            frontend_url = frontend_url.replace('8081', '8080')
        redirect_uri = f"{frontend_url}/auth/youtube/callback"
        
        scopes = [
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.readonly"
        ]
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": os.getenv('YOUTUBE_CLIENT_SECRET'),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=scopes,
            redirect_uri=redirect_uri
        )
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state
        )
        
        return auth_url
    
    @staticmethod
    async def exchange_code_for_token(code: str, state: str) -> Dict[str, Any]:
        """Exchange OAuth code for access token."""
        client_id = os.getenv('YOUTUBE_CLIENT_ID')
        client_secret = os.getenv('YOUTUBE_CLIENT_SECRET')
        # Force correct frontend URL for OAuth (must match initiation URL)
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:8080')
        if '8081' in frontend_url:
            frontend_url = frontend_url.replace('8081', '8080')
        redirect_uri = f"{frontend_url}/auth/youtube/callback"
        
        scopes = [
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.readonly"
        ]
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=scopes,
            redirect_uri=redirect_uri
        )
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        return {
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'expires_in': 3600,  # Google tokens typically expire in 1 hour
            'expires_at': credentials.expiry
        }
