# 🎭 Clip Tone Sorter

Automatically analyzes and sorts video clips into folders based on their emotional tone using advanced audio analysis.

## 🎯 Features

- **Automatic Tone Detection**: Analyzes audio features to determine clip tone
- **7 Tone Categories**: 
  - 🔥 **Hype** - High energy, exciting moments
  - 😂 **Laughter** - Comedy, funny moments
  - 💖 **Emotional** - Emotionally intense moments
  - 😮 **Reaction** - Surprised/amazed reactions
  - ⚡ **Energetic** - High energy bursts
  - 😌 **Calm** - Low energy, calm moments
  - 😴 **Boring** - Low engagement, monotone
- **Smart Organization**: Automatically creates folders and sorts clips
- **Detailed Reports**: JSON report with scores and confidence levels
- **Safe Mode**: Copy by default, optional move mode

## 📋 Usage

### Basic Usage (Copy Mode)
```bash
python scripts/sort_clips_by_tone.py path/to/raw/clips
```

This will:
- Analyze all clips in the input directory
- Copy clips to `sorted_clips/` folder organized by tone
- Generate a summary report

### Custom Output Directory
```bash
python scripts/sort_clips_by_tone.py path/to/raw/clips -o path/to/output
```

### Move Mode (Don't Keep Originals)
```bash
python scripts/sort_clips_by_tone.py path/to/raw/clips --move
```

### Skip Report Generation
```bash
python scripts/sort_clips_by_tone.py path/to/raw/clips --no-report
```

## 📊 Output Structure

```
sorted_clips/
├── hype/           # High energy clips
├── laughter/       # Comedy clips
├── emotional/      # Emotionally intense clips
├── reaction/       # Reaction clips
├── energetic/      # Energy burst clips
├── calm/           # Calm clips
├── boring/         # Low engagement clips
├── uncategorized/  # Failed analysis
└── clip_sorting_report.json  # Detailed analysis data
```

## 📈 Report Example

```
📊 CLIP TONE SORTING REPORT
============================================================

📂 Input Directory: clips/raw
📂 Output Directory: sorted_clips
📋 Mode: COPY

📈 Total Clips Processed: 50

------------------------------------------------------------
📊 Distribution by Tone:
------------------------------------------------------------
🔥 HYPE             15 clips ( 30.0%) - High energy, exciting moments
😂 LAUGHTER         12 clips ( 24.0%) - Comedy, funny moments
💖 EMOTIONAL         8 clips ( 16.0%) - Emotionally intense moments
😮 REACTION          7 clips ( 14.0%) - Surprised/amazed reactions
⚡ ENERGETIC         5 clips ( 10.0%) - High energy bursts
😴 BORING            3 clips (  6.0%) - Low engagement, monotone
```

## 🔍 How It Works

1. **Audio Feature Extraction**: Analyzes volume, energy, speech rate, pauses, etc.
2. **Score Calculation**: Computes continuous scores (0-1) for each tone type
3. **Tone Classification**: Determines dominant tone based on score thresholds
4. **Organization**: Sorts clips into appropriate folders
5. **Reporting**: Generates detailed analysis report

## 📝 Supported Formats

- Video: `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`, `.flv`
- Audio: `.mp3`, `.wav`

## 🎓 Advanced Options

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `input_dir` | Directory with raw clips (required) | - |
| `-o, --output` | Output directory for sorted clips | `sorted_clips` |
| `-m, --move` | Move clips instead of copying | `False` |
| `--no-report` | Skip summary report generation | `False` |

## 💡 Tips

1. **Start with Copy Mode**: Always use copy mode first to verify results
2. **Check Reports**: Review the JSON report to understand tone detection
3. **Large Batches**: Process in smaller batches if you have many clips
4. **Audio Quality**: Better audio quality = better tone detection

## 🔧 Troubleshooting

**Problem**: "No analysis results for clip"
- **Solution**: Check if clip has audio, try a different format

**Problem**: Many clips end up in "uncategorized"
- **Solution**: Clips may have unclear tone, or audio quality is poor

**Problem**: Wrong tone detection
- **Solution**: Check the JSON report for scores, thresholds may need adjustment

## 📊 Understanding Scores

Each clip gets scores (0-1) for different features:

- `hype_score`: Energy + audience reaction
- `laughter_score`: Comedy detection
- `emotional_score`: Emotional intensity
- `energy_score`: Energy burst detection
- `boring_content_score`: Low engagement indicators
- `clip_worthiness_score`: Overall quality

Higher scores = stronger presence of that feature

## 🚀 Example Workflow

```bash
# 1. Sort clips (copy mode - safe)
python scripts/sort_clips_by_tone.py raw_clips -o sorted

# 2. Review the report
cat sorted/clip_sorting_report.json

# 3. Check the folders
ls -la sorted/

# 4. If satisfied, can run in move mode
python scripts/sort_clips_by_tone.py new_clips -o sorted --move
```

## 📧 Need Help?

Check the detailed JSON report for insights into why clips were categorized a certain way. The report includes all scores and indicators used for classification.



