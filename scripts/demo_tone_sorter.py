#!/usr/bin/env python3
"""
Demo script to show how the tone sorter would categorize clips.
Creates example output without needing actual video files.
"""

import json
from pathlib import Path

# Example analysis results that the real script would generate
EXAMPLE_CLIPS = [
    {
        "clip_name": "funny_moment_123.mp4",
        "tone": "laughter",
        "confidence": 0.87,
        "scores": {
            "hype_score": 0.45,
            "laughter_score": 0.87,
            "emotional_score": 0.32,
            "energy_score": 0.56,
            "boring_content_score": 0.15
        }
    },
    {
        "clip_name": "epic_reaction_456.mp4",
        "tone": "hype",
        "confidence": 0.92,
        "scores": {
            "hype_score": 0.92,
            "laughter_score": 0.34,
            "emotional_score": 0.67,
            "energy_score": 0.89,
            "boring_content_score": 0.08
        }
    },
    {
        "clip_name": "slow_talking_789.mp4",
        "tone": "boring",
        "confidence": 0.73,
        "scores": {
            "hype_score": 0.12,
            "laughter_score": 0.08,
            "emotional_score": 0.15,
            "energy_score": 0.11,
            "boring_content_score": 0.73
        }
    },
    {
        "clip_name": "heartfelt_speech_234.mp4",
        "tone": "emotional",
        "confidence": 0.78,
        "scores": {
            "hype_score": 0.35,
            "laughter_score": 0.12,
            "emotional_score": 0.78,
            "energy_score": 0.42,
            "boring_content_score": 0.22
        }
    },
    {
        "clip_name": "crazy_moment_567.mp4",
        "tone": "energetic",
        "confidence": 0.85,
        "scores": {
            "hype_score": 0.65,
            "laughter_score": 0.45,
            "emotional_score": 0.55,
            "energy_score": 0.85,
            "boring_content_score": 0.15
        }
    },
    {
        "clip_name": "surprised_890.mp4",
        "tone": "reaction",
        "confidence": 0.81,
        "scores": {
            "hype_score": 0.58,
            "laughter_score": 0.32,
            "emotional_score": 0.61,
            "energy_score": 0.72,
            "boring_content_score": 0.19
        }
    },
    {
        "clip_name": "chill_vibes_345.mp4",
        "tone": "calm",
        "confidence": 0.68,
        "scores": {
            "hype_score": 0.25,
            "laughter_score": 0.18,
            "emotional_score": 0.35,
            "energy_score": 0.22,
            "boring_content_score": 0.45
        }
    },
]

TONE_EMOJIS = {
    "hype": "🔥",
    "laughter": "😂",
    "emotional": "💖",
    "reaction": "😮",
    "energetic": "⚡",
    "calm": "😌",
    "boring": "😴"
}

TONE_DESCRIPTIONS = {
    "hype": "High energy, exciting moments",
    "laughter": "Comedy, funny moments",
    "emotional": "Emotionally intense moments",
    "reaction": "Surprised/amazed reactions",
    "energetic": "High energy bursts",
    "calm": "Low energy, calm moments",
    "boring": "Low engagement, monotone"
}

def generate_demo_report():
    """Generate a demo report showing what the sorter produces."""
    
    print("="*60)
    print("🎭 CLIP TONE SORTER - DEMO OUTPUT")
    print("="*60)
    print("\nThis shows what the real script would output when analyzing clips.\n")
    
    # Count clips by tone
    tone_counts = {}
    for clip in EXAMPLE_CLIPS:
        tone = clip['tone']
        tone_counts[tone] = tone_counts.get(tone, 0) + 1
    
    # Display summary
    print("📊 SORTING SUMMARY")
    print("-"*60)
    print(f"Total Clips Processed: {len(EXAMPLE_CLIPS)}")
    print("\nDistribution by Tone:")
    print("-"*60)
    
    for tone, count in sorted(tone_counts.items(), key=lambda x: x[1], reverse=True):
        emoji = TONE_EMOJIS.get(tone, '❓')
        desc = TONE_DESCRIPTIONS.get(tone, 'Unknown')
        percentage = (count / len(EXAMPLE_CLIPS)) * 100
        print(f"{emoji} {tone.upper():15} {count} clips ({percentage:5.1f}%) - {desc}")
    
    # Display example clips
    print("\n" + "-"*60)
    print("📋 EXAMPLE CLIPS BY CATEGORY")
    print("-"*60)
    
    clips_by_tone = {}
    for clip in EXAMPLE_CLIPS:
        tone = clip['tone']
        if tone not in clips_by_tone:
            clips_by_tone[tone] = []
        clips_by_tone[tone].append(clip)
    
    for tone in sorted(clips_by_tone.keys()):
        emoji = TONE_EMOJIS.get(tone, '❓')
        print(f"\n{emoji} {tone.upper()}:")
        for clip in clips_by_tone[tone]:
            print(f"  • {clip['clip_name']} (confidence: {clip['confidence']:.2f})")
            print(f"    Scores: hype={clip['scores']['hype_score']:.2f}, "
                  f"laughter={clip['scores']['laughter_score']:.2f}, "
                  f"energy={clip['scores']['energy_score']:.2f}")
    
    # Show folder structure
    print("\n" + "="*60)
    print("📁 OUTPUT FOLDER STRUCTURE")
    print("="*60)
    print("\nsorted_clips/")
    for tone in sorted(clips_by_tone.keys()):
        emoji = TONE_EMOJIS.get(tone, '❓')
        count = len(clips_by_tone[tone])
        print(f"├── {tone}/  {emoji} ({count} clips)")
        for clip in clips_by_tone[tone][:2]:  # Show first 2
            print(f"│   ├── {clip['clip_name']}")
        if len(clips_by_tone[tone]) > 2:
            print(f"│   └── ... and {len(clips_by_tone[tone]) - 2} more")
    print("└── clip_sorting_report.json")
    
    # Generate JSON report
    json_report = {
        "total_clips": len(EXAMPLE_CLIPS),
        "statistics": tone_counts,
        "clips": EXAMPLE_CLIPS
    }
    
    output_file = "demo_sorting_report.json"
    with open(output_file, 'w') as f:
        json.dump(json_report, f, indent=2)
    
    print(f"\n💾 Demo report saved to: {output_file}")
    
    # Show usage instructions
    print("\n" + "="*60)
    print("🚀 HOW TO USE THE REAL SCRIPT")
    print("="*60)
    print("\n1. Basic usage (copy mode):")
    print("   python scripts/sort_clips_by_tone.py your_clips_folder")
    print("\n2. Specify output directory:")
    print("   python scripts/sort_clips_by_tone.py your_clips_folder -o sorted")
    print("\n3. Move instead of copy:")
    print("   python scripts/sort_clips_by_tone.py your_clips_folder --move")
    print("\n4. Process downloaded clips:")
    print("   python scripts/sort_clips_by_tone.py buffer -o sorted_clips")
    
    print("\n" + "="*60)
    print("✅ Demo complete! See above for example output.")
    print("="*60)
    print("\n📚 For more info, see:")
    print("   - scripts/README_TONE_SORTER.md")
    print("   - scripts/QUICK_START_TONE_SORTER.md")
    print()

if __name__ == "__main__":
    generate_demo_report()



