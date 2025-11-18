# 🌐 Supabase Clip Tone Sorter

Download clips from Supabase Storage and automatically sort them by emotional tone.

## 🎯 Features

- **Direct Supabase Integration**: Downloads clips from your Supabase storage bucket
- **Automatic Organization**: Analyzes and sorts into 7 tone categories
- **Flexible Filtering**: Process specific paths or entire buckets
- **Detailed Reports**: JSON reports with storage paths and analysis
- **Safe Operation**: Downloads to local temp directory, doesn't modify Supabase

## 📋 Usage

### Basic Usage - Process Entire Bucket

```bash
python scripts/sort_clips_from_supabase.py
```

This will:
- Connect to your Supabase storage (using .env credentials)
- Download all clips from the "raw" bucket
- Analyze and sort them by tone
- Save organized clips to `sorted_clips_from_supabase/`

### Specify Custom Bucket

```bash
python scripts/sort_clips_from_supabase.py --bucket my_clips
```

### Process Specific Path in Bucket

```bash
# Process clips from a specific channel
python scripts/sort_clips_from_supabase.py --prefix "channel_name"

# Process clips from a specific stream
python scripts/sort_clips_from_supabase.py --prefix "channel_name/stream_123/20250120"
```

### Custom Output Directory

```bash
python scripts/sort_clips_from_supabase.py -o organized_clips
```

### Limit Number of Clips (For Testing)

```bash
# Process only first 10 clips
python scripts/sort_clips_from_supabase.py --max-clips 10
```

### Complete Example

```bash
python scripts/sort_clips_from_supabase.py \
  --bucket raw \
  --prefix "caseoh/stream_20250120" \
  --output sorted_caseoh_clips \
  --max-clips 50
```

## 🔐 Setup Requirements

### 1. Environment Variables

Make sure your `.env` file has Supabase credentials:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key  # For full storage access
STORAGE_BUCKET=raw
```

### 2. Service Role Key

This script requires the **service role key** (not the anon key) for full storage access:

- Go to your Supabase project settings
- Navigate to API settings
- Copy the `service_role` key (keep this secret!)
- Add to `.env` as `SUPABASE_SERVICE_KEY`

### 3. Required Packages

```bash
pip install supabase librosa soundfile numpy
```

## 📊 Output Structure

```
sorted_clips_from_supabase/
├── hype/           # 🔥 High energy clips
├── laughter/       # 😂 Comedy clips
├── emotional/      # 💖 Emotional clips
├── reaction/       # 😮 Reaction clips
├── energetic/      # ⚡ Energy bursts
├── calm/           # 😌 Calm moments
├── boring/         # 😴 Low engagement
├── uncategorized/  # Failed analysis
└── supabase_sorting_report.json
```

## 📈 Report Example

```json
{
  "source": "supabase",
  "bucket": "raw",
  "storage_prefix": "channel/stream_123",
  "total_clips": 25,
  "statistics": {
    "hype": 8,
    "laughter": 6,
    "emotional": 4,
    "energetic": 3,
    "boring": 2,
    "calm": 2
  },
  "clips": [
    {
      "file_name": "seg_00123.mp4",
      "storage_path": "channel/stream_123/seg_00123.mp4",
      "tone": "hype",
      "confidence": 0.87,
      "scores": {
        "hype_score": 0.87,
        "laughter_score": 0.45,
        "energy_score": 0.82
      }
    }
  ]
}
```

## 🔍 How It Works

1. **Connect to Supabase**: Uses service role key for full access
2. **List Files**: Scans storage bucket for video files
3. **Download**: Temporarily downloads each clip
4. **Analyze**: Extracts audio features and calculates tone scores
5. **Sort**: Saves clips to category folders locally
6. **Report**: Generates detailed JSON with storage paths
7. **Cleanup**: Removes temporary downloads

## 💡 Common Use Cases

### 1. Process Today's Stream Clips

```bash
# Get today's date
DATE=$(date +%Y%m%d)

python scripts/sort_clips_from_supabase.py \
  --prefix "mychannel/stream_${DATE}" \
  --output "sorted_${DATE}"
```

### 2. Test on Sample Clips

```bash
# Process just 5 clips to test
python scripts/sort_clips_from_supabase.py --max-clips 5
```

### 3. Process Multiple Channels

```bash
# Process different channels separately
python scripts/sort_clips_from_supabase.py --prefix "channel1" -o sorted_channel1
python scripts/sort_clips_from_supabase.py --prefix "channel2" -o sorted_channel2
python scripts/sort_clips_from_supabase.py --prefix "channel3" -o sorted_channel3
```

### 4. Find Best Clips from Storage

```bash
# Sort all clips, then look in hype/ and laughter/ folders
python scripts/sort_clips_from_supabase.py

# Best clips will be in:
# - sorted_clips_from_supabase/hype/
# - sorted_clips_from_supabase/laughter/
```

## 🎓 Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `-b, --bucket` | Supabase storage bucket name | `raw` |
| `-p, --prefix` | Path prefix in bucket | `""` (root) |
| `-o, --output` | Output directory | `sorted_clips_from_supabase` |
| `--max-clips` | Max clips to process | `None` (all) |
| `--no-report` | Skip report generation | `False` |

## 🔧 Troubleshooting

### "Permission denied" or "Access denied"

**Problem**: Using anon key instead of service role key
```bash
# Solution: Set the service role key in .env
SUPABASE_SERVICE_KEY=your-service-role-key-here
```

### "Bucket not found"

**Problem**: Wrong bucket name
```bash
# List available buckets
python scripts/check_storage.py

# Use correct bucket name
python scripts/sort_clips_from_supabase.py --bucket correct_name
```

### "No clips found"

**Problem**: Wrong prefix or empty bucket
```bash
# Check what's in your bucket
python scripts/list_clips.py

# Use correct prefix
python scripts/sort_clips_from_supabase.py --prefix "correct/path"
```

### Many clips in "uncategorized"

**Problem**: Poor audio quality or analysis failing
```bash
# Check JSON report for details
cat sorted_clips_from_supabase/supabase_sorting_report.json

# Try with fewer clips first
python scripts/sort_clips_from_supabase.py --max-clips 5
```

## 🚀 Workflow Examples

### Workflow 1: Daily Stream Processing

```bash
#!/bin/bash
# Process yesterday's stream
YESTERDAY=$(date -d "yesterday" +%Y%m%d)
CHANNEL="mychannel"

python scripts/sort_clips_from_supabase.py \
  --prefix "${CHANNEL}/stream_${YESTERDAY}" \
  --output "sorted_${YESTERDAY}"

# Upload best clips somewhere
# cp sorted_${YESTERDAY}/hype/* /path/to/highlights/
```

### Workflow 2: Test Then Process All

```bash
# Step 1: Test with 10 clips
python scripts/sort_clips_from_supabase.py --max-clips 10 -o test_sort

# Step 2: Review results
ls test_sort/*/

# Step 3: If good, process all
python scripts/sort_clips_from_supabase.py -o full_sort
```

### Workflow 3: Multi-Stream Analysis

```bash
# Get all streams from a channel
python scripts/sort_clips_from_supabase.py --prefix "mychannel" -o all_channel_clips

# Review distribution
cat all_channel_clips/supabase_sorting_report.json | grep -A 5 "statistics"
```

## 📊 Understanding Storage Paths

Your Supabase storage might be organized like:

```
raw/  (bucket)
├── channel1/
│   ├── stream_20250118/
│   │   ├── 20250118/
│   │   │   ├── seg_00001.mp4
│   │   │   ├── seg_00002.mp4
│   │   │   └── seg_00003.mp4
│   └── stream_20250119/
│       └── 20250119/
│           └── seg_00001.mp4
└── channel2/
    └── stream_20250120/
        └── 20250120/
            └── seg_00001.mp4
```

To process specific paths:

```bash
# All of channel1
python scripts/sort_clips_from_supabase.py --prefix "channel1"

# Specific stream
python scripts/sort_clips_from_supabase.py --prefix "channel1/stream_20250118"

# Specific day
python scripts/sort_clips_from_supabase.py --prefix "channel1/stream_20250118/20250118"
```

## 🆚 vs Local File Sorter

| Feature | Supabase Sorter | Local Sorter |
|---------|----------------|--------------|
| **Source** | Supabase Storage | Local filesystem |
| **Network** | Downloads files | No network needed |
| **Use Case** | Cloud storage | Local clips |
| **Speed** | Slower (downloads) | Faster |
| **Access** | Needs service key | Direct file access |

**When to use Supabase sorter:**
- Clips stored in Supabase cloud
- Want to process remote clips without manual download
- Need to analyze cloud-stored content

**When to use local sorter:**
- Clips already on disk
- Faster processing needed
- No network connection

## 📚 Related Scripts

- `scripts/sort_clips_by_tone.py` - Sort local clips
- `scripts/list_clips.py` - List clips in Supabase storage
- `scripts/check_storage.py` - Check Supabase storage setup
- `scripts/live_ingest.py` - Capture and upload clips to Supabase

---

Need help? Check the JSON report for details on why clips were categorized certain ways!

