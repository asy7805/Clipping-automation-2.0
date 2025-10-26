"""
TikTok Content Posting API integration.
Handles OAuth, token refresh, and video uploads.
"""

import os
import requests
import logging
import secrets
import hashlib
import base64
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from .base_publisher import BaseSocialPublisher

logger = logging.getLogger(__name__)


def generate_pkce_pair():
    """Generate PKCE code verifier and challenge."""
    # Generate code verifier (43-128 characters, URL-safe)
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    
    # Generate code challenge (SHA256 hash of verifier)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')
    
    return code_verifier, code_challenge


class TikTokPublisher(BaseSocialPublisher):
    """TikTok Content Posting API publisher."""
    
    def __init__(self, access_token: str, refresh_token: Optional[str] = None):
        super().__init__(access_token, refresh_token)
        self.client_key = os.getenv('TIKTOK_CLIENT_KEY')
        self.client_secret = os.getenv('TIKTOK_CLIENT_SECRET')
        self.base_url = "https://open-api.tiktok.com"
        
    async def upload_video(self, video_path: str, **kwargs) -> Dict[str, Any]:
        """
        Upload a video to TikTok.
        
        NOTE: This method requires 'video.publish' scope which needs app review.
        Currently disabled for MVP testing with basic scopes only.
        
        Args:
            video_path: Path to the video file
            caption: Video caption (optional)
            privacy_level: PUBLIC, PRIVATE, or FRIENDS (default: PUBLIC)
            
        Returns:
            Dict containing TikTok response with video_id and video_url
        """
        try:
            # Check if we have video publishing scope
            # This is a temporary check for MVP testing with basic scopes
            raise Exception("Video upload requires 'video.publish' scope which needs TikTok app review. Currently testing with basic scopes only.")
            
            # Ensure we have a valid token
            await self.ensure_valid_token()
            
            # Prepare upload request
            caption = kwargs.get('caption', '')
            privacy_level = kwargs.get('privacy_level', 'PUBLIC')
            
            # Step 1: Initialize upload
            init_url = f"{self.base_url}/v2/post/publish/video/init/"
            init_payload = {
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": os.path.getsize(video_path),
                    "chunk_size": 10000000,  # 10MB chunks
                    "total_chunk_count": 1
                },
                "post_info": {
                    "title": caption[:150] if caption else "Auto-generated clip",
                    "privacy_level": privacy_level,
                    "disable_duet": False,
                    "disable_comment": False,
                    "disable_stitch": False,
                    "video_cover_timestamp_ms": 1000
                }
            }
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"Initializing TikTok upload for {video_path}")
            init_response = requests.post(init_url, json=init_payload, headers=headers)
            init_response.raise_for_status()
            init_data = init_response.json()
            
            if init_data.get('error'):
                raise Exception(f"TikTok init error: {init_data['error']['message']}")
            
            publish_id = init_data['data']['publish_id']
            upload_url = init_data['data']['upload_url']
            
            # Step 2: Upload video file
            logger.info(f"Uploading video file to TikTok")
            with open(video_path, 'rb') as video_file:
                upload_response = requests.put(upload_url, data=video_file)
                upload_response.raise_for_status()
            
            # Step 3: Publish the video
            publish_url = f"{self.base_url}/v2/post/publish/"
            publish_payload = {
                "post_info": {
                    "title": caption[:150] if caption else "Auto-generated clip",
                    "privacy_level": privacy_level,
                    "disable_duet": False,
                    "disable_comment": False,
                    "disable_stitch": False,
                    "video_cover_timestamp_ms": 1000
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "publish_id": publish_id
                }
            }
            
            publish_response = requests.post(publish_url, json=publish_payload, headers=headers)
            publish_response.raise_for_status()
            publish_data = publish_response.json()
            
            if publish_data.get('error'):
                raise Exception(f"TikTok publish error: {publish_data['error']['message']}")
            
            video_id = publish_data['data']['id']
            video_url = f"https://www.tiktok.com/@username/video/{video_id}"
            
            logger.info(f"Successfully uploaded video to TikTok: {video_id}")
            
            return {
                'video_id': video_id,
                'video_url': video_url,
                'platform': 'tiktok',
                'status': 'posted'
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"TikTok API request failed: {e}")
            raise Exception(f"TikTok upload failed: {str(e)}")
        except Exception as e:
            logger.error(f"TikTok upload error: {e}")
            raise Exception(self.format_error_message(e))
    
    async def refresh_access_token(self) -> str:
        """Refresh TikTok access token using refresh token."""
        if not self.refresh_token:
            raise Exception("No refresh token available")
        
        try:
            refresh_url = f"{self.base_url}/oauth/refresh_token/"
            refresh_payload = {
                "client_key": self.client_key,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token
            }
            
            response = requests.post(refresh_url, json=refresh_payload)
            response.raise_for_status()
            data = response.json()
            
            if data.get('error'):
                raise Exception(f"TikTok refresh error: {data['error']['message']}")
            
            new_access_token = data['data']['access_token']
            expires_in = data['data']['expires_in']
            
            # Update token expiration
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            logger.info("Successfully refreshed TikTok access token")
            return new_access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"TikTok refresh request failed: {e}")
            raise Exception(f"TikTok token refresh failed: {str(e)}")
        except Exception as e:
            logger.error(f"TikTok refresh error: {e}")
            raise Exception(f"TikTok token refresh failed: {str(e)}")
    
    def validate_credentials(self) -> bool:
        """Validate TikTok credentials by checking user info."""
        try:
            # Make a simple API call to validate token
            url = f"{self.base_url}/v2/user/info/"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            response = requests.get(url, headers=headers)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"TikTok credential validation failed: {e}")
            return False
    
    async def get_user_info(self) -> Dict[str, Any]:
        """Get TikTok user information."""
        try:
            await self.ensure_valid_token()
            
            url = f"{self.base_url}/v2/user/info/"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if data.get('error'):
                raise Exception(f"TikTok user info error: {data['error']['message']}")
            
            user_data = data['data']['user']
            return {
                'user_id': user_data['open_id'],
                'username': user_data.get('display_name', ''),
                'avatar_url': user_data.get('avatar_url', ''),
                'follower_count': user_data.get('follower_count', 0),
                'following_count': user_data.get('following_count', 0)
            }
            
        except Exception as e:
            logger.error(f"TikTok user info error: {e}")
            raise Exception(f"Failed to get TikTok user info: {str(e)}")
    
    @staticmethod
    def get_oauth_url(state: str) -> tuple[str, str]:
        """Generate TikTok OAuth URL for user authorization with PKCE."""
        client_key = os.getenv('TIKTOK_CLIENT_KEY') or 'awxtb142eazp4stz'
        # Force correct frontend URL for OAuth
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:8080')
        if '8081' in frontend_url:
            frontend_url = frontend_url.replace('8081', '8080')
        redirect_uri = f"{frontend_url}/auth/tiktok/callback"
        
        # Generate PKCE pair
        code_verifier, code_challenge = generate_pkce_pair()
        
        # Temporarily using only basic scope - video.publish requires TikTok app review
        scopes = ["user.info.basic"]
        
        params = {
            "client_key": client_key,
            "scope": ",".join(scopes),
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        oauth_url = f"https://www.tiktok.com/v2/auth/authorize/?{query_string}"
        
        return oauth_url, code_verifier
    
    @staticmethod
    async def exchange_code_for_token(code: str, state: str, code_verifier: str) -> Dict[str, Any]:
        """Exchange OAuth code for access token with PKCE."""
        client_key = os.getenv('TIKTOK_CLIENT_KEY')
        client_secret = os.getenv('TIKTOK_CLIENT_SECRET')
        redirect_uri = f"{os.getenv('FRONTEND_URL', 'http://localhost:8080')}/auth/tiktok/callback"
        
        token_url = "https://open-api.tiktok.com/oauth/access_token/"
        token_payload = {
            "client_key": client_key,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier
        }
        
        response = requests.post(token_url, json=token_payload)
        response.raise_for_status()
        data = response.json()
        
        if data.get('error'):
            raise Exception(f"TikTok token exchange error: {data['error']['message']}")
        
        token_data = data['data']
        expires_in = token_data['expires_in']
        
        return {
            'access_token': token_data['access_token'],
            'refresh_token': token_data.get('refresh_token'),
            'expires_in': expires_in,
            'expires_at': datetime.utcnow() + timedelta(seconds=expires_in)
        }
