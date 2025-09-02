#!/usr/bin/env python3
"""
Initialize stream directories for ingestion.
Creates the directory layout for a new stream_id and writes empty manifest files.
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any


def generate_stream_id(channel_name: str) -> str:
    """Generate stream_id as: twitch_{channel}_{UTC_ISO_NO_COLONS}"""
    # Normalize channel to lowercase
    channel_lower = channel_name.lower()
    
    # Get current UTC time in ISO format without colons
    utc_now = datetime.now(timezone.utc)
    timestamp = utc_now.strftime("%Y-%m-%dT%H%M%SZ")
    
    return f"twitch_{channel_lower}_{timestamp}"


def create_stream_json(stream_id: str, channel_name: str, ingest_type: str, 
                      chunk_seconds: int, overlap_seconds: float) -> Dict[str, Any]:
    """Create the stream.json content with the exact schema."""
    return {
        "stream_id": stream_id,
        "platform": "twitch",
        "channel_name": channel_name,
        "title": None,
        "category": None,
        "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ended_at": None,
        "ingest_type": ingest_type,
        "chunk_seconds": chunk_seconds,
        "overlap_seconds": overlap_seconds
    }


def write_file_atomically(file_path: Path, content: str) -> None:
    """Write file atomically by writing to temp file then renaming."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, dir=file_path.parent) as temp_file:
        temp_file.write(content)
        temp_file_path = Path(temp_file.name)
    
    # Atomic rename
    temp_file_path.rename(file_path)


def create_stream_directories(stream_root: Path) -> None:
    """Create the directory tree structure."""
    directories = [
        stream_root / "meta",
        stream_root / "raw_audio" / "chunks",
        stream_root / "source"
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=False)


def main():
    parser = argparse.ArgumentParser(description="Initialize stream directories for ingestion")
    parser.add_argument("--channel", required=True, help="Channel name")
    parser.add_argument("--ingest-type", required=True, choices=["live", "vod"], 
                       help="Ingest type: live or vod")
    parser.add_argument("--chunk-seconds", type=int, required=True, 
                       help="Chunk duration in seconds")
    parser.add_argument("--overlap-seconds", type=float, default=0.0, 
                       help="Overlap between chunks in seconds (default: 0.0)")
    parser.add_argument("--output-root", default="/streams", 
                       help="Output root directory (default: /streams)")
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.chunk_seconds <= 0:
        print("Error: chunk_seconds must be greater than 0", file=sys.stderr)
        sys.exit(1)
    
    # Generate stream_id
    stream_id = generate_stream_id(args.channel)
    stream_root = Path(args.output_root) / stream_id
    
    # Check if path already exists
    if stream_root.exists():
        print(f"Error: Stream directory already exists: {stream_root}", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Create directory structure
        create_stream_directories(stream_root)
        
        # Create stream.json
        stream_data = create_stream_json(
            stream_id, args.channel, args.ingest_type, 
            args.chunk_seconds, args.overlap_seconds
        )
        stream_json_path = stream_root / "meta" / "stream.json"
        write_file_atomically(stream_json_path, json.dumps(stream_data, indent=2))
        
        # Create empty chunk_manifest.jsonl
        chunk_manifest_path = stream_root / "meta" / "chunk_manifest.jsonl"
        chunk_manifest_path.touch()
        
        # Create empty ingest.log
        ingest_log_path = stream_root / "meta" / "ingest.log"
        ingest_log_path.touch()
        
        # Print the absolute path to stream root
        print(str(stream_root.absolute()))
        
    except FileExistsError as e:
        print(f"Error: Directory already exists: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error creating stream directories: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
