#!/usr/bin/env python3
"""
Tests for stream directory initialization functionality.
"""

import os
import sys
import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch

# Add project root to Python path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from scripts.init_stream_dirs import (
    generate_stream_id, 
    create_stream_json, 
    write_file_atomically,
    create_stream_directories
)


class TestStreamInit:
    """Test cases for stream initialization functionality."""
    
    def test_generate_stream_id(self):
        """Test stream ID generation."""
        channel_name = "test_channel"
        stream_id = generate_stream_id(channel_name)
        
        # Check format: twitch_{channel}_{timestamp}
        assert stream_id.startswith("twitch_test_channel_")
        assert stream_id.endswith("Z")
        
        # Check timestamp format (no colons)
        timestamp_part = stream_id.split("_")[-1]
        assert ":" not in timestamp_part
        assert len(timestamp_part) == 20  # YYYY-MM-DDTHHMMSSZ
    
    def test_generate_stream_id_different_channels(self):
        """Test stream ID generation for different channels."""
        channel1 = "Channel1"
        channel2 = "CHANNEL2"
        
        id1 = generate_stream_id(channel1)
        id2 = generate_stream_id(channel2)
        
        # Both should be lowercase
        assert "channel1" in id1
        assert "channel2" in id2
        assert "Channel1" not in id1
        assert "CHANNEL2" not in id2
    
    def test_create_stream_json(self):
        """Test stream.json creation."""
        stream_id = "twitch_test_2023-01-01T120000Z"
        channel_name = "test_channel"
        ingest_type = "live"
        chunk_seconds = 30
        overlap_seconds = 0.5
        
        stream_data = create_stream_json(
            stream_id, channel_name, ingest_type, chunk_seconds, overlap_seconds
        )
        
        # Check required fields
        assert stream_data["stream_id"] == stream_id
        assert stream_data["platform"] == "twitch"
        assert stream_data["channel_name"] == channel_name
        assert stream_data["ingest_type"] == ingest_type
        assert stream_data["chunk_seconds"] == chunk_seconds
        assert stream_data["overlap_seconds"] == overlap_seconds
        
        # Check optional fields
        assert stream_data["title"] is None
        assert stream_data["category"] is None
        assert stream_data["ended_at"] is None
        
        # Check timestamp format
        assert stream_data["started_at"].endswith("Z")
        assert "T" in stream_data["started_at"]
    
    def test_write_file_atomically(self):
        """Test atomic file writing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_file.json"
            content = '{"test": "data"}'
            
            write_file_atomically(file_path, content)
            
            # Check file exists and has correct content
            assert file_path.exists()
            with open(file_path, 'r') as f:
                assert f.read() == content
    
    def test_write_file_atomically_overwrite(self):
        """Test atomic file writing overwrites existing file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_file.json"
            
            # Write initial content
            write_file_atomically(file_path, '{"old": "data"}')
            
            # Overwrite with new content
            write_file_atomically(file_path, '{"new": "data"}')
            
            # Check file has new content
            with open(file_path, 'r') as f:
                assert f.read() == '{"new": "data"}'
    
    def test_create_stream_directories(self):
        """Test directory structure creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            stream_root = Path(temp_dir) / "test_stream"
            
            create_stream_directories(stream_root)
            
            # Check all required directories exist
            expected_dirs = [
                stream_root / "meta",
                stream_root / "raw_audio" / "chunks",
                stream_root / "source"
            ]
            
            for directory in expected_dirs:
                assert directory.exists()
                assert directory.is_dir()
    
    def test_create_stream_directories_existing(self):
        """Test directory creation fails when directory already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            stream_root = Path(temp_dir) / "test_stream"
            stream_root.mkdir()
            
            # Should raise FileExistsError
            with pytest.raises(FileExistsError):
                create_stream_directories(stream_root)


class TestStreamInitIntegration:
    """Integration tests for stream initialization."""
    
    @patch('scripts.init_stream_dirs.datetime')
    def test_main_function_flow(self, mock_datetime):
        """Test the main function flow with mocked datetime."""
        # Mock datetime to get predictable output
        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.now.return_value.strftime = mock_now.strftime
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock command line arguments
            with patch('sys.argv', [
                'init_stream_dirs.py',
                '--channel', 'test_channel',
                '--ingest-type', 'live',
                '--chunk-seconds', '30',
                '--overlap-seconds', '0.5',
                '--output-root', temp_dir
            ]):
                # Import and run main
                import scripts.init_stream_dirs
                
                # Capture stdout
                from io import StringIO
                import sys
                old_stdout = sys.stdout
                sys.stdout = StringIO()
                
                try:
                    scripts.init_stream_dirs.main()
                    output = sys.stdout.getvalue().strip()
                finally:
                    sys.stdout = old_stdout
                
                # Check output is a valid path
                output_path = Path(output)
                assert output_path.exists()
                assert output_path.is_dir()
                
                # Check directory structure
                assert (output_path / "meta").exists()
                assert (output_path / "raw_audio" / "chunks").exists()
                assert (output_path / "source").exists()
                
                # Check stream.json
                stream_json_path = output_path / "meta" / "stream.json"
                assert stream_json_path.exists()
                
                with open(stream_json_path, 'r') as f:
                    stream_data = json.load(f)
                
                assert stream_data["channel_name"] == "test_channel"
                assert stream_data["ingest_type"] == "live"
                assert stream_data["chunk_seconds"] == 30
                assert stream_data["overlap_seconds"] == 0.5
                
                # Check manifest files
                assert (output_path / "meta" / "chunk_manifest.jsonl").exists()
                assert (output_path / "meta" / "ingest.log").exists()
    
    def test_main_function_invalid_args(self):
        """Test main function with invalid arguments."""
        with patch('sys.argv', [
            'init_stream_dirs.py',
            '--channel', 'test_channel',
            '--ingest-type', 'live',
            '--chunk-seconds', '0',  # Invalid: must be > 0
            '--output-root', '/tmp'
        ]):
            import scripts.init_stream_dirs
            
            with pytest.raises(SystemExit):
                scripts.init_stream_dirs.main()
    
    def test_main_function_existing_directory(self):
        """Test main function when directory already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create existing directory
            existing_dir = Path(temp_dir) / "twitch_test_channel_2023-01-01T120000Z"
            existing_dir.mkdir()
            
            with patch('sys.argv', [
                'init_stream_dirs.py',
                '--channel', 'test_channel',
                '--ingest-type', 'live',
                '--chunk-seconds', '30',
                '--output-root', temp_dir
            ]), patch('scripts.init_stream_dirs.generate_stream_id', return_value="twitch_test_channel_2023-01-01T120000Z"):
                
                import scripts.init_stream_dirs
                
                with pytest.raises(SystemExit):
                    scripts.init_stream_dirs.main()


if __name__ == "__main__":
    pytest.main([__file__])
