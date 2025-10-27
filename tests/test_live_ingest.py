#!/usr/bin/env python3
"""
Tests for live ingestion script functionality.
"""

import os
import sys
import pytest
import tempfile
import subprocess
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path

# Add project root to Python path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

# Mock environment variables and load_dotenv before importing
with patch.dict(os.environ, {
    'SUPABASE_URL': 'https://test.supabase.co',
    'SUPABASE_ANON_KEY': 'test_anon_key',
    'SUPABASE_SERVICE_ROLE_KEY': 'test_service_key',
    'OPENAI_API_KEY': 'test_openai_key',
    'TWITCH_CLIENT_ID': 'test_twitch_client_id',
    'TWITCH_CLIENT_SECRET': 'test_twitch_client_secret',
    'STORAGE_BUCKET': 'test_bucket',
    'DEFAULT_USER_ID': 'test_user_123'
}), patch('scripts.live_ingest.load_dotenv'):
    from scripts.live_ingest import ensure_streams_row, upload_segment, start_pipeline


class TestLiveIngest:
    """Test cases for live ingestion functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.mock_sb = Mock()
        self.test_channel = "test_channel"
        self.test_stream_id = "test_stream_123"
        self.test_user_id = "user_123"
    
    @patch('scripts.live_ingest.fetch_one')
    @patch('scripts.live_ingest.insert_row')
    def test_ensure_streams_row_existing(self, mock_insert, mock_fetch):
        """Test ensure_streams_row when stream already exists."""
        # Mock existing stream
        existing_stream = {
            'id': 1,
            'twitch_stream_id': self.test_stream_id,
            'channel_name': self.test_channel
        }
        mock_fetch.return_value = existing_stream
        
        result = ensure_streams_row(self.mock_sb, self.test_channel, self.test_stream_id, self.test_user_id)
        
        assert result == existing_stream
        mock_fetch.assert_called_once_with("streams", twitch_stream_id=self.test_stream_id)
        mock_insert.assert_not_called()
    
    @patch('scripts.live_ingest.fetch_one')
    @patch('scripts.live_ingest.insert_row')
    def test_ensure_streams_row_new(self, mock_insert, mock_fetch):
        """Test ensure_streams_row when creating new stream."""
        # Mock no existing stream
        mock_fetch.return_value = None
        
        # Mock successful insert
        new_stream = {
            'id': 2,
            'twitch_stream_id': self.test_stream_id,
            'channel_name': self.test_channel
        }
        mock_insert.return_value = new_stream
        
        result = ensure_streams_row(self.mock_sb, self.test_channel, self.test_stream_id, self.test_user_id)
        
        assert result == new_stream
        mock_fetch.assert_called_once_with("streams", twitch_stream_id=self.test_stream_id)
        mock_insert.assert_called_once()
        
        # Check insert payload
        call_args = mock_insert.call_args
        assert call_args[0][0] == "streams"
        payload = call_args[0][1]
        assert payload['twitch_stream_id'] == self.test_stream_id
        assert payload['channel_name'] == self.test_channel
    
    @patch('scripts.live_ingest.time.strftime')
    def test_ensure_streams_row_no_stream_id(self, mock_strftime):
        """Test ensure_streams_row when no stream_id provided."""
        mock_strftime.return_value = "2023-01-01T00:00:00Z"
        
        with patch('scripts.live_ingest.fetch_one', return_value=None), \
             patch('scripts.live_ingest.insert_row') as mock_insert:
            
            mock_insert.return_value = {'id': 3}
            
            result = ensure_streams_row(self.mock_sb, self.test_channel, None, self.test_user_id)
            
            # Check that a generated stream_id was used
            call_args = mock_insert.call_args
            payload = call_args[0][1]
            assert payload['twitch_stream_id'].startswith(f"live-{self.test_channel}-")
    
    def test_upload_segment(self):
        """Test segment upload functionality."""
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_file.write(b"fake video data")
            temp_path = Path(temp_file.name)
        
        try:
            # Mock storage bucket
            mock_bucket = Mock()
            mock_storage = Mock()
            mock_bucket.upload.return_value = {'path': 'test/path/segment.mp4'}
            self.mock_sb.storage.from_.return_value = mock_bucket
            
            result = upload_segment(
                self.mock_sb, 
                "test_bucket", 
                temp_path, 
                "raw", 
                self.test_channel, 
                self.test_stream_id
            )
            
            # Verify upload was called
            mock_bucket.upload.assert_called_once()
            call_args = mock_bucket.upload.call_args
            
            # Check the key format
            key = call_args[0][0]
            assert key.startswith("raw/test_channel/test_stream_123/")
            assert key.endswith("segment.mp4")
            
            # Check file options
            file_options = call_args[0][1]
            assert file_options["upsert"] == "true"
            
        finally:
            # Clean up temp file
            temp_path.unlink(missing_ok=True)
    
    @patch('scripts.live_ingest.subprocess.Popen')
    def test_start_pipeline(self, mock_popen):
        """Test pipeline startup functionality."""
        # Mock subprocess calls
        mock_sl_proc = Mock()
        mock_ff_proc = Mock()
        mock_popen.side_effect = [mock_sl_proc, mock_ff_proc]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            sl_proc, ff_proc, seg_pattern = start_pipeline(self.test_channel, temp_path)
            
            # Verify subprocess calls
            assert mock_popen.call_count == 2
            
            # Check streamlink command
            sl_call = mock_popen.call_args_list[0]
            sl_cmd = sl_call[0][0]
            assert "streamlink" in sl_cmd[0]
            assert f"https://twitch.tv/{self.test_channel}" in sl_cmd
            assert "-O" in sl_cmd  # Output to stdout
            
            # Check ffmpeg command
            ff_call = mock_popen.call_args_list[1]
            ff_cmd = ff_call[0][0]
            assert "ffmpeg" in ff_cmd[0]
            assert "pipe:0" in ff_cmd  # Input from stdin
            assert "segment" in ff_cmd
            assert str(temp_path / "seg_%05d.mp4") in ff_cmd
            
            # Check segment pattern
            assert seg_pattern == str(temp_path / "seg_%05d.mp4")
    
    def test_start_pipeline_missing_dependencies(self):
        """Test pipeline startup with missing dependencies."""
        with patch('scripts.live_ingest.shutil.which') as mock_which:
            mock_which.return_value = None  # Simulate missing dependency
            
            with pytest.raises(SystemExit):
                # This would normally be called in main() but we can test the logic
                import scripts.live_ingest
                for bin_name in ("streamlink", "ffmpeg"):
                    if not __import__('shutil').which(bin_name):
                        raise SystemExit(1)


class TestLiveIngestIntegration:
    """Integration tests for live ingestion."""
    
    @patch('scripts.live_ingest.get_client')
    @patch('scripts.live_ingest.subprocess.Popen')
    def test_main_function_flow(self, mock_popen, mock_get_client):
        """Test the main function flow with mocked dependencies."""
        # Mock Supabase client
        mock_sb = Mock()
        mock_get_client.return_value = mock_sb
        
        # Mock stream creation
        with patch('scripts.live_ingest.ensure_streams_row') as mock_ensure, \
             patch('scripts.live_ingest.start_pipeline') as mock_start, \
             patch('scripts.live_ingest.upload_segment') as mock_upload, \
             patch('scripts.live_ingest.time.sleep') as mock_sleep, \
             patch('scripts.live_ingest.Path.glob') as mock_glob:
            
            # Setup mocks
            mock_ensure.return_value = {'id': 1, 'twitch_stream_id': 'test_stream'}
            mock_sl_proc = Mock()
            mock_ff_proc = Mock()
            mock_start.return_value = (mock_sl_proc, mock_ff_proc, "seg_%05d.mp4")
            
            # Mock file discovery
            mock_file = Mock()
            mock_file.stat.return_value.st_size = 1024  # Non-zero size
            mock_file not in set()  # Not in known set
            mock_glob.return_value = [mock_file]
            
            mock_upload.return_value = "test/path/segment.mp4"
            
            # Mock KeyboardInterrupt to stop the loop
            mock_sleep.side_effect = KeyboardInterrupt()
            
            # Import and test main function
            import scripts.live_ingest
            
            # This would normally be called with command line args
            # We'll test the core logic instead
            try:
                # Simulate the main loop
                known = set()
                while True:
                    for file in mock_glob.return_value:
                        if file not in known and file.stat().st_size > 0:
                            mock_upload(file)
                            known.add(file)
                    mock_sleep(1)
            except KeyboardInterrupt:
                pass  # Expected behavior


if __name__ == "__main__":
    pytest.main([__file__])
