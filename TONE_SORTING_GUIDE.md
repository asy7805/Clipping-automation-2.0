# 🎭 Complete Tone Sorting Guide

Two ways to sort your clips by emotional tone - choose based on where your clips are stored!

## 📦 Quick Decision: Which Script?

```
┌─────────────────────────────────────────┐
│  Where are your clips?                  │
├─────────────────────────────────────────┤
│                                         │
│  📁 Local disk/folder                   │
│  → Use: sort_clips_by_tone.py          │
│                                         │
│  ☁️  Supabase Storage                   │
│  → Use: sort_clips_from_supabase.py    │
│                                         │
└─────────────────────────────────────────┘
```

## 🎯 Script Comparison

| Feature | Local Sorter | Supabase Sorter |
|---------|-------------|-----------------|
| **Command** | `python scripts/sort_clips_by_tone.py <folder>` | `python scripts/sort_clips_from_supabase.py` |
| **Source** | Local files | Supabase cloud storage |
| **Speed** | ⚡ Fast | 🐢 Slower (downloads) |
| **Network** | Not needed | Required |
| **Setup** | Just point to folder | Needs Supabase credentials |
| **Best For** | Processing local clips | Cloud-stored clips |

## 🚀 Quick Start Examples

### Example 1: Sort Local Clips

```bash
# You have clips in a folder called "my_clips"
python scripts/sort_clips_by_tone.py my_clips

# Result: sorted_clips/ folder with organized clips
```

### Example 2: Sort from Supabase Storage

```bash
# You have clips stored in Supabase
python scripts/sort_clips_from_supabase.py

# Result: sorted_clips_from_supabase/ folder with organized clips
```

### Example 3: Sort Specific Supabase Path

```bash
# Only sort clips from a specific channel/stream
python scripts/sort_clips_from_supabase.py --prefix "channel_name/stream_id"
```

## 📊 Output - Both Scripts

Both scripts organize clips into the same 7 categories:

```
📁 Output Folder/
├── 🔥 hype/           # High energy, exciting moments
├── 😂 laughter/       # Comedy, funny moments
├── 💖 emotional/      # Emotionally intense moments
├── 😮 reaction/       # Surprised/amazed reactions
├── ⚡ energetic/      # High energy bursts
├── 😌 calm/           # Low energy, calm moments
├── 😴 boring/         # Low engagement, monotone
└── 📄 sorting_report.json
```

## 🎓 Common Scenarios

### Scenario 1: "I just downloaded some clips"
```bash
# Clips are in the "buffer" folder
python scripts/sort_clips_by_tone.py buffer -o organized
```

### Scenario 2: "My clips are in Supabase from live capture"
```bash
# Sort directly from cloud storage
python scripts/sort_clips_from_supabase.py -o organized
```

### Scenario 3: "I want to test with just a few clips first"
```bash
# Local: copy a few clips to a test folder first
mkdir test_clips
cp my_clips/*.mp4 test_clips/ | head -5
python scripts/sort_clips_by_tone.py test_clips

# Supabase: use --max-clips
python scripts/sort_clips_from_supabase.py --max-clips 5
```

### Scenario 4: "I want the best clips from today's stream"
```bash
# From Supabase
python scripts/sort_clips_from_supabase.py \
  --prefix "mychannel/stream_$(date +%Y%m%d)"

# Check hype/ and laughter/ folders for best clips
ls sorted_clips_from_supabase/hype/
ls sorted_clips_from_supabase/laughter/
```

## 🔧 Installation

Both scripts need:

```bash
# Install required packages
pip install librosa soundfile numpy

# For Supabase sorter, also need:
pip install supabase
```

## ⚙️ Configuration

### Local Sorter - No Configuration Needed!

Just run it on any folder with video files.

### Supabase Sorter - Needs .env Setup

Create/edit `.env` file:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
STORAGE_BUCKET=raw
```

## 📖 Detailed Documentation

- **Local Sorter**: See `scripts/README_TONE_SORTER.md`
- **Supabase Sorter**: See `scripts/README_SUPABASE_TONE_SORTER.md`
- **Quick Start**: See `scripts/QUICK_START_TONE_SORTER.md`

## 💡 Pro Tips

1. **Always test first**: Process 5-10 clips before running on hundreds
2. **Review the report**: Check the JSON file to understand categorization
3. **Use copy mode first**: Don't use `--move` until you've verified results
4. **Check audio quality**: Better audio = better tone detection
5. **Save processing time**: Use `--max-clips` for quick tests

## 🎬 Complete Workflow Example

### Step 1: Capture Clips (if needed)
```bash
python scripts/live_ingest.py --channel channel_name
```

### Step 2: Sort Clips
```bash
# If stored locally:
python scripts/sort_clips_by_tone.py buffer

# If stored in Supabase:
python scripts/sort_clips_from_supabase.py
```

### Step 3: Review Results
```bash
# View distribution
cat sorted_clips/sorting_report.json

# or
cat sorted_clips_from_supabase/supabase_sorting_report.json
```

### Step 4: Use Best Clips
```bash
# Copy hype clips for highlights
cp sorted_clips/hype/* highlights_folder/

# Upload laughter clips for comedy compilation
# etc.
```

## 🎯 Key Takeaways

| Goal | Use This |
|------|----------|
| **Sort local files** | `sort_clips_by_tone.py` |
| **Sort from Supabase** | `sort_clips_from_supabase.py` |
| **Test with few clips** | Add `--max-clips 5` |
| **Move instead of copy** | Add `--move` |
| **Custom output folder** | Add `-o folder_name` |
| **Get detailed analysis** | Check the JSON report |

## 🆘 Troubleshooting

### Problem: "No clips found"

**Solution**: Check your path/folder
```bash
# Local: verify folder exists and has video files
ls -la your_folder/*.mp4

# Supabase: list what's in storage
python scripts/list_clips.py
```

### Problem: "Many clips in 'uncategorized'"

**Solution**: Audio quality or analysis issues
```bash
# Check the JSON report for details
cat sorted_clips/sorting_report.json | grep uncategorized

# Try with better quality clips
```

### Problem: "Supabase permission denied"

**Solution**: Need service role key
```bash
# Make sure .env has:
SUPABASE_SERVICE_KEY=your-service-role-key-here  # NOT anon key
```

## 🎨 Understanding Tone Categories

Each clip is analyzed for:

- **Volume patterns** (energy, bursts)
- **Speech rate** (fast, slow, pauses)
- **Emotional intensity** (excitement, monotone)
- **Audience reaction** (laughter, cheering)

These combine to determine the dominant tone:

- **Hype** = High energy + audience + emotion
- **Laughter** = Comedy patterns detected
- **Emotional** = High emotion without comedy
- **Reaction** = Strong audience without laughter
- **Energetic** = Energy bursts detected
- **Calm** = Low energy, not boring
- **Boring** = Low everything

---

## 🚀 Ready to Start?

Choose your script and run it!

```bash
# Local clips
python scripts/sort_clips_by_tone.py your_folder

# Supabase clips
python scripts/sort_clips_from_supabase.py
```

Then check the output folder and JSON report! 🎉




