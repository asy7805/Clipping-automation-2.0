#!/usr/bin/env python3
"""
Script to clean up all clips and ensure they have ONLY the past backend format.
Removes all multi-line breakdown formatting and applies concise single-line format.
"""

import os
import re
from dotenv import load_dotenv

load_dotenv()
os.environ["USE_SERVICE_ROLE"] = "true"

from src.db.supabase_client import get_client


def clean_transcript(transcript: str, confidence_score: float, channel_name: str = "unknown") -> str:
    """
    Clean transcript by removing ALL old formatting and applying past backend format only.
    """
    if transcript is None or transcript.strip() == "":
        transcript = f"Clip from {channel_name}"
    
    # Remove all old breakdown formatting patterns
    patterns_to_remove = [
        r"📊 SCORING BREAKDOWN:.*?\n",
        r"  • Overall Score:.*?\n",
        r"  • Energy \(35%\):.*?\n",
        r"  • Pitch Variance \(25%\):.*?\n",
        r"  • Emotion Intensity \(40%\):.*?\n",
        r"  • Keyword Boost \(15%\):.*?\n",
        r"  🔥 Contains hype keywords!.*?\n",
        r"  ℹ️ Note:.*?\n",
        r"\n📝 TRANSCRIPT:\n",
        r"📝 TRANSCRIPT:\n",
    ]
    
    cleaned = transcript
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, "", cleaned, flags=re.MULTILINE | re.DOTALL)
    
    # Remove leading/trailing whitespace and empty lines
    cleaned = "\n".join([line for line in cleaned.split("\n") if line.strip()])
    cleaned = cleaned.strip()
    
    # If transcript already has the correct format at the start, extract just the transcript part
    if cleaned.startswith("Score:"):
        # Split at first newline to get scoring line and transcript
        parts = cleaned.split("\n", 1)
        if len(parts) > 1:
            cleaned = parts[1].strip()
        else:
            cleaned = f"Clip from {channel_name}"
    
    # Create past backend format (concise single-line)
    estimated_energy = round(confidence_score * 0.35, 4)
    estimated_pitch = round(confidence_score * 0.25, 4)
    estimated_emotion = round(confidence_score * 0.40, 4)
    
    details_dict = {
        'energy': estimated_energy,
        'pitch': estimated_pitch,
        'emotion': estimated_emotion,
        'keyword': 0
    }
    
    # Check if this is a historical clip (has "estimated" in old format)
    is_historical = "(estimated)" in transcript or "📊" in transcript
    suffix = " (estimated)" if is_historical else ""
    
    scoring_line = f"Score: {confidence_score:.3f} | {details_dict}{suffix}\n"
    
    return scoring_line + cleaned


def main():
    print("🧹 Cleaning up all clip formatting...")
    print("   Removing old multi-line breakdowns")
    print("   Applying past backend format (concise single-line)\n")
    
    sb = get_client()
    
    # Fetch all clips
    print("📥 Fetching all clips from database...")
    result = sb.table('clips_metadata').select('*').execute()
    
    if not result.data:
        print("❌ No clips found in database")
        return
    
    clips = result.data
    print(f"✅ Found {len(clips)} clips to process\n")
    
    updated_count = 0
    error_count = 0
    
    # Show example of first clip transformation
    if clips:
        first_clip = clips[0]
        old_transcript = first_clip.get('transcript', '')
        new_transcript = clean_transcript(
            old_transcript,
            first_clip.get('confidence_score', 0.5),
            first_clip.get('channel_name', 'unknown')
        )
        
        print("📋 EXAMPLE TRANSFORMATION:")
        print("-" * 60)
        print("BEFORE:")
        print(old_transcript[:200] + "..." if len(old_transcript) > 200 else old_transcript)
        print("\nAFTER:")
        print(new_transcript[:200] + "..." if len(new_transcript) > 200 else new_transcript)
        print("-" * 60)
        print()
    
    # Process all clips
    for i, clip in enumerate(clips):
        try:
            clip_id = clip['id']
            transcript = clip.get('transcript', '')
            confidence_score = clip.get('confidence_score', 0.5)
            channel_name = clip.get('channel_name', 'unknown')
            
            # Clean and reformat transcript
            new_transcript = clean_transcript(transcript, confidence_score, channel_name)
            
            # Update in database
            update_result = sb.table('clips_metadata')\
                .update({'transcript': new_transcript})\
                .eq('id', clip_id)\
                .execute()
            
            if update_result.data:
                updated_count += 1
                if (updated_count % 50 == 0):
                    print(f"  ✅ Processed {updated_count}/{len(clips)} clips...")
            else:
                error_count += 1
                
        except Exception as e:
            print(f"  ❌ Error updating clip {clip.get('id', 'unknown')}: {e}")
            error_count += 1
    
    print(f"\n{'='*60}")
    print(f"🎉 CLEANUP COMPLETE")
    print(f"  • Total clips: {len(clips)}")
    print(f"  • Successfully cleaned: {updated_count}")
    print(f"  • Errors: {error_count}")
    print(f"{'='*60}\n")
    
    # Show sample of final format
    print("📋 FINAL FORMAT (sample from database):")
    sample_result = sb.table('clips_metadata').select('transcript, confidence_score').limit(3).execute()
    if sample_result.data:
        for i, sample in enumerate(sample_result.data, 1):
            print(f"\nClip {i}:")
            print("-" * 60)
            transcript_preview = sample['transcript'][:200] + "..." if len(sample['transcript']) > 200 else sample['transcript']
            print(transcript_preview)
            print("-" * 60)


if __name__ == "__main__":
    main()

