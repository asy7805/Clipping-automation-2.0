#!/usr/bin/env python3
"""
Tests for Twitch engagement fetcher functionality.
"""

import os
import sys
import pytest
from unittest.mock import patch, Mock
from pathlib import Path

# Add src to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

# Mock environment variables before importing
with patch.dict(os.environ, {
    'TWITCH_CLIENT_ID': 'test_twitch_client_id',
    'TWITCH_CLIENT_SECRET': 'test_twitch_client_secret'
}):
    from twitch_engagement_fetcher import TwitchEngagementFetcher, get_clip_engagement, calculate_engagement_score, assign_auto_label


class TestTwitchEngagementFetcher:
    """Test cases for TwitchEngagementFetcher class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.fetcher = TwitchEngagementFetcher()
        self.fetcher.client_id = "test_client_id"
        self.fetcher.client_secret = "test_client_secret"
    
    @patch('twitch_engagement_fetcher.requests.post')
    def test_get_access_token_success(self, mock_post):
        """Test successful access token retrieval."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'test_token',
            'expires_in': 3600
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        token = self.fetcher._get_access_token()
        
        assert token == 'test_token'
        assert self.fetcher.access_token == 'test_token'
        mock_post.assert_called_once()
    
    @patch('twitch_engagement_fetcher.requests.post')
    def test_get_access_token_failure(self, mock_post):
        """Test access token retrieval failure."""
        # Mock failed response
        mock_post.side_effect = Exception("API Error")
        
        token = self.fetcher._get_access_token()
        
        assert token is None
    
    @patch('twitch_engagement_fetcher.requests.get')
    def test_get_clip_engagement_success(self, mock_get):
        """Test successful clip engagement data retrieval."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': [{
                'id': 'test_clip_id',
                'view_count': 1000,
                'duration': 30.5,
                'created_at': '2023-01-01T00:00:00Z',
                'broadcaster_name': 'test_streamer',
                'title': 'Test Clip',
                'url': 'https://clips.twitch.tv/test'
            }]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Mock access token
        self.fetcher.access_token = 'test_token'
        
        result = self.fetcher.get_clip_engagement('test_clip_id')
        
        assert result is not None
        assert result['clip_id'] == 'test_clip_id'
        assert result['views'] == 1000
        assert result['duration'] == 30.5
        assert result['broadcaster_name'] == 'test_streamer'
    
    @patch('twitch_engagement_fetcher.requests.get')
    def test_get_clip_engagement_no_data(self, mock_get):
        """Test clip engagement retrieval when no data found."""
        # Mock empty response
        mock_response = Mock()
        mock_response.json.return_value = {'data': []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Mock access token
        self.fetcher.access_token = 'test_token'
        
        result = self.fetcher.get_clip_engagement('nonexistent_clip')
        
        assert result is None
    
    def test_calculate_engagement_score(self):
        """Test engagement score calculation."""
        # Test high engagement
        high_engagement = {'views': 5000, 'duration': 45}
        score = self.fetcher.calculate_engagement_score(high_engagement)
        assert score > 0.5
        
        # Test low engagement
        low_engagement = {'views': 10, 'duration': 5}
        score = self.fetcher.calculate_engagement_score(low_engagement)
        assert score < 0.5
        
        # Test zero views
        zero_engagement = {'views': 0, 'duration': 30}
        score = self.fetcher.calculate_engagement_score(zero_engagement)
        assert score == 0.0
    
    def test_assign_auto_label(self):
        """Test auto label assignment based on engagement score."""
        # High engagement
        assert self.fetcher.assign_auto_label(0.8) == "1"
        
        # Medium engagement
        assert self.fetcher.assign_auto_label(0.5) == "0.5"
        
        # Low engagement
        assert self.fetcher.assign_auto_label(0.2) == "0"


class TestHelperFunctions:
    """Test cases for helper functions."""
    
    @patch('twitch_engagement_fetcher.engagement_fetcher.get_clip_engagement')
    def test_get_clip_engagement_function(self, mock_get):
        """Test the get_clip_engagement helper function."""
        mock_get.return_value = {'clip_id': 'test', 'views': 100}
        
        result = get_clip_engagement('test_clip')
        
        assert result == {'clip_id': 'test', 'views': 100}
        mock_get.assert_called_once_with('test_clip')
    
    def test_calculate_engagement_score_function(self):
        """Test the calculate_engagement_score helper function."""
        engagement_data = {'views': 2000, 'duration': 30}
        
        score = calculate_engagement_score(engagement_data)
        
        assert isinstance(score, float)
        assert 0 <= score <= 1
    
    def test_assign_auto_label_function(self):
        """Test the assign_auto_label helper function."""
        # Test different score ranges
        assert assign_auto_label(0.8) == "1"
        assert assign_auto_label(0.5) == "0.5"
        assert assign_auto_label(0.2) == "0"


if __name__ == "__main__":
    pytest.main([__file__])
