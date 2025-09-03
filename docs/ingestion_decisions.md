# Ingestion Decisions and Architecture

## Overview
This document outlines the decisions made for the ingestion system architecture, including file formats, directory structure, and configuration standards.

## Key Decisions

### Platform
- **Platform**: Twitch (primary streaming platform)
- **Integration**: Uses Twitch API for stream metadata and access

### Audio Configuration
- **Format**: WAV PCM s16
- **Channels**: Mono (1 channel)
- **Sample Rate**: 16000 Hz
- **Rationale**: Optimized for speech recognition and processing efficiency

### Chunking Strategy
- **Live Streams**: 30-second chunks with 0.5-second overlap
- **VOD Content**: 60-second chunks with no overlap
- **Overlap**: Only used for live streams to ensure continuous coverage

### Filesystem Layout
```
/streams/{stream_id}/
├── meta/
│   ├── stream.json          # Stream metadata and configuration
│   ├── chunk_manifest.jsonl # Chunk tracking and timestamps
│   └── ingest.log          # Processing logs (placeholder)
├── raw_audio/
│   └── chunks/             # Audio chunk files
└── source/                 # Original source files
```

### Time Standard
- **Timezone**: UTC only
- **Format**: ISO 8601 with Z suffix (e.g., "2025-08-19T00:00:00Z")
- **Clock Sync**: Required for accurate timestamping

### Manifest Schema

#### stream.json Schema
```json
{
  "stream_id": "twitch_channel_2025-08-19T001500Z",
  "platform": "twitch",
  "channel_name": "example_channel",
  "title": null,
  "category": null,
  "started_at": "2025-08-19T00:15:00Z",
  "ended_at": null,
  "ingest_type": "vod",
  "chunk_seconds": 60,
  "overlap_seconds": 0.0
}
```

#### chunk_manifest.jsonl Schema
Each line is a JSON object with the following structure:
```json
{
  "stream_id": "twitch_channel_2025-08-19T001500Z",
  "chunk_idx": 1,
  "chunk_file": "000001.wav",
  "segment_seconds": 60,
  "utc_start": "2025-08-19T00:00:00Z",
  "utc_end": "2025-08-19T00:01:00Z",
  "source": "vod",
  "vod_id": "<VOD_ID or null>"
}
```

## Usage Examples

### Initializing a VOD Stream
```bash
# Initialize a VOD stream with 60-second chunks
python3 scripts/init_stream_dirs.py \
  --channel ninja \
  --ingest-type vod \
  --chunk-seconds 60

# Output: /streams/twitch_ninja_2025-08-19T001500Z
```

### Initializing a Live Stream
```bash
# Initialize a live stream with 30-second chunks and 0.5-second overlap
python3 scripts/init_stream_dirs.py \
  --channel pokimane \
  --ingest-type live \
  --chunk-seconds 30 \
  --overlap-seconds 0.5

# Output: /streams/twitch_pokimane_2025-08-19T001500Z
```

### Using Make Target
```bash
# Using the make target for convenience
make init-stream CHANNEL=example_channel TYPE=vod CHUNK=60
```

## Chunk Size Guidelines

### Live Streams (30 seconds)
- **Advantages**: Lower latency, faster processing
- **Use Case**: Real-time analysis and immediate clip generation
- **Overlap**: 0.5 seconds to ensure no gaps in coverage

### VOD Content (60 seconds)
- **Advantages**: Better context, more efficient processing
- **Use Case**: Post-stream analysis and comprehensive content review
- **Overlap**: None needed for pre-recorded content

## UTC Time Usage

All timestamps are stored in UTC to ensure:
- Consistent timezone handling across different regions
- Accurate chronological ordering of chunks
- Reliable synchronization between multiple ingest processes

The stream_id includes a UTC timestamp to ensure uniqueness and provide chronological ordering of streams from the same channel.

## Configuration

The system uses `config/ingest.yaml` for default configuration values. Key settings include:
- Audio format specifications
- Chunking parameters
- Storage retention policies
- Twitch API configuration

Environment variables in `.env` provide API credentials and runtime configuration.
