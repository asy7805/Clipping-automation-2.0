"""
Base class for social media publishers.
Provides common interface for TikTok, YouTube, and other platforms.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BaseSocialPublisher(ABC):
    """Abstract base class for social media publishers."""
    
    def __init__(self, access_token: str, refresh_token: Optional[str] = None):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expires_at: Optional[datetime] = None
    
    @abstractmethod
    async def upload_video(self, video_path: str, **kwargs) -> Dict[str, Any]:
        """
        Upload a video to the social media platform.
        
        Args:
            video_path: Path to the video file
            **kwargs: Platform-specific parameters (caption, privacy, etc.)
            
        Returns:
            Dict containing platform-specific response data
        """
        pass
    
    @abstractmethod
    async def refresh_access_token(self) -> str:
        """
        Refresh the access token using the refresh token.
        
        Returns:
            New access token
        """
        pass
    
    @abstractmethod
    def validate_credentials(self) -> bool:
        """
        Validate that the current credentials are valid.
        
        Returns:
            True if credentials are valid, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_user_info(self) -> Dict[str, Any]:
        """
        Get user information from the platform.
        
        Returns:
            Dict containing user information
        """
        pass
    
    def is_token_expired(self) -> bool:
        """Check if the access token is expired."""
        if not self.token_expires_at:
            return False
        return datetime.utcnow() >= self.token_expires_at
    
    async def ensure_valid_token(self) -> str:
        """
        Ensure the access token is valid, refreshing if necessary.
        
        Returns:
            Valid access token
        """
        if self.is_token_expired() and self.refresh_token:
            logger.info("Access token expired, refreshing...")
            self.access_token = await self.refresh_access_token()
        return self.access_token
    
    def get_platform_name(self) -> str:
        """Get the platform name (tiktok, youtube, etc.)."""
        return self.__class__.__name__.lower().replace('publisher', '')
    
    def format_error_message(self, error: Exception) -> str:
        """Format error message for logging and user display."""
        return f"{self.get_platform_name().title()} upload failed: {str(error)}"
