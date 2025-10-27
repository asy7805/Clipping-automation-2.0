# 🚀 Quick Start: Clip Tone Sorter

## ✅ What You Need

1. A folder with video clips (MP4, MOV, AVI, etc.)
2. Python environment with required packages installed

## 📦 Installation

Make sure you have the required audio analysis dependencies:

```bash
pip install librosa soundfile numpy
```

## 🎯 Basic Usage Examples

### Example 1: Sort Downloaded Twitch Clips

If you've downloaded clips using the live ingestion system:

```bash
# Check if buffer directory exists and has clips
ls buffer/

# Sort clips from buffer directory
python scripts/sort_clips_by_tone.py buffer -o sorted_clips
```

### Example 2: Sort from Custom Directory

```bash
# Create a test directory with your clips
mkdir my_clips
# ... copy some video files into my_clips ...

# Sort the clips
python scripts/sort_clips_by_tone.py my_clips -o organized_clips
```

### Example 3: Move Instead of Copy (Clean Up Original Folder)

```bash
python scripts/sort_clips_by_tone.py buffer --move -o sorted_clips
```

## 📁 Where Are My Clips?

Your clips might be in one of these locations:

- `buffer/` - Downloaded Twitch clips from live ingestion
- `data/raw_clips/good/` - Manually organized clips
- Custom location you specified

## 🎬 Test with Sample Clips

### Option 1: Use Existing Clips from Buffer

```bash
# Check what's in buffer
ls buffer/*.mp4

# If you have clips, run the sorter
python scripts/sort_clips_by_tone.py buffer
```

### Option 2: Download Sample Clips First

```bash
# First, make sure you have some clips downloaded
# Run the live ingestion to get clips (if configured)
python scripts/live_ingest.py

# Then sort them
python scripts/sort_clips_by_tone.py buffer -o sorted_clips
```

## 📊 Understanding the Results

After running, you'll see:

```
sorted_clips/
├── hype/               # 🔥 Exciting, high-energy moments
├── laughter/           # 😂 Funny, comedy clips
├── emotional/          # 💖 Emotionally intense clips
├── reaction/           # 😮 Surprised reactions
├── energetic/          # ⚡ Energy bursts
├── calm/               # 😌 Low energy, calm
├── boring/             # 😴 Low engagement
└── clip_sorting_report.json
```

## 🔍 Check the Report

```bash
# View the summary
cat sorted_clips/clip_sorting_report.json

# Or use Python to pretty print
python -m json.tool sorted_clips/clip_sorting_report.json
```

## 💡 Tips for Best Results

1. **Audio Quality Matters**: Better audio = better tone detection
2. **Clip Length**: Works best with 5-60 second clips
3. **Review Results**: Check the JSON report to understand categorization
4. **Start Small**: Test with 10-20 clips first before processing hundreds

## 🎓 Common Workflows

### Workflow 1: Download and Sort Pipeline

```bash
# Step 1: Download clips (if configured)
python scripts/live_ingest.py

# Step 2: Sort clips by tone
python scripts/sort_clips_by_tone.py buffer -o sorted_clips

# Step 3: Review results
cat sorted_clips/clip_sorting_report.json
```

### Workflow 2: Re-organize Existing Clips

```bash
# Sort without moving originals (safe)
python scripts/sort_clips_by_tone.py data/raw_clips/good -o organized

# Review what you got
ls -la organized/*/

# If happy with results, can run with --move next time
```

### Workflow 3: Batch Processing

```bash
# Process multiple directories
python scripts/sort_clips_by_tone.py folder1 -o sorted1
python scripts/sort_clips_by_tone.py folder2 -o sorted2
python scripts/sort_clips_by_tone.py folder3 -o sorted3
```

## 🐛 Troubleshooting

### "No video files found"

**Problem**: Script can't find clips in the directory
```bash
# Check what's in the directory
ls -la your_directory/

# Make sure files have video extensions (.mp4, .mov, etc.)
```

### "Module not found" Errors

**Problem**: Missing dependencies
```bash
# Install audio analysis packages
pip install librosa soundfile numpy scipy

# Or install all requirements
pip install -r requirements.txt
```

### Many Clips in "Uncategorized"

**Problem**: Audio analysis failing or unclear tone
```bash
# Check the JSON report for details
cat sorted_clips/clip_sorting_report.json

# Look for error messages in console output
```

## 📧 Example: Full Demo

```bash
# 1. Create test directory
mkdir test_clips
cd test_clips

# 2. Copy some existing clips (replace with your paths)
cp /path/to/some/clips/*.mp4 .

# 3. Go back to project root
cd ..

# 4. Run the sorter
python scripts/sort_clips_by_tone.py test_clips -o test_sorted

# 5. Check results
ls test_sorted/*/
cat test_sorted/clip_sorting_report.json

# 6. View detailed stats
python -m json.tool test_sorted/clip_sorting_report.json | less
```

## 🎯 Next Steps

Once you've sorted your clips:

1. **Review each category** to see if tone detection is accurate
2. **Use the JSON report** to fine-tune thresholds if needed
3. **Integrate into your workflow** for automatic clip organization
4. **Create highlights** from the best categories (hype, laughter, emotional)

## 📚 More Help

- See `README_TONE_SORTER.md` for detailed documentation
- Check the JSON report for insights into tone detection
- Adjust thresholds in the script if categorization needs tuning

---

Happy sorting! 🎉



