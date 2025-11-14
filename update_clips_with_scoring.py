#!/usr/bin/env python3
"""
Script to update all existing clips with scoring breakdown in their transcript.
Since we don't have the original detailed metrics, we'll add a simplified breakdown
based on the confidence_score that's already stored.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Set service role for database access
os.environ["USE_SERVICE_ROLE"] = "true"

from src.db.supabase_client import get_client

def add_scoring_breakdown_to_transcript(transcript: str, confidence_score: float, channel_name: str = "unknown") -> str:
    """
    Add scoring breakdown to existing transcript in past backend format.
    Since we don't have the detailed metrics, we'll create an estimated breakdown.
    """
    # Handle null/empty transcripts
    if transcript is None:
        transcript = f"Clip from {channel_name}"
    
    # Check if already has past backend format (concise single-line)
    if transcript.startswith("Score:") and "| {" in transcript:
        return transcript  # Already has past backend format
    
    # If has multi-line breakdown format, extract the transcript part and reformat
    if "📊 SCORING BREAKDOWN:" in transcript:
        # Extract just the transcript portion (after the last newline section)
        if "📝 TRANSCRIPT:" in transcript:
            transcript = transcript.split("📝 TRANSCRIPT:\n", 1)[1]
        elif "\n\n" in transcript:
            # Find the actual transcript after all the breakdown info
            parts = transcript.split("\n")
            # Skip lines with breakdown info
            transcript_lines = []
            found_transcript = False
            for line in parts:
                if not line.strip().startswith(("📊", "•", "ℹ️", "📝")) and line.strip():
                    found_transcript = True
                if found_transcript:
                    transcript_lines.append(line)
            transcript = "\n".join(transcript_lines).strip()
    
    # Create estimated breakdown from confidence score (past backend format)
    # Distribute the confidence score across metrics (rough estimation)
    estimated_energy = round(confidence_score * 0.35, 4)
    estimated_pitch = round(confidence_score * 0.25, 4)
    estimated_emotion = round(confidence_score * 0.40, 4)
    
    # Past backend format: "Score: X.XXX | {details} | Transcript"
    details_dict = {
        'energy': estimated_energy,
        'pitch': estimated_pitch,
        'emotion': estimated_emotion,
        'keyword': 0  # Unknown for historical clips
    }
    
    scoring_line = f"Score: {confidence_score:.3f} | {details_dict} (estimated)\n"
    
    return scoring_line + transcript


def main():
    print("🔄 Starting to update existing clips with scoring breakdown...")
    
    sb = get_client()
    
    # Fetch all clips
    print("📥 Fetching all clips from database...")
    result = sb.table('clips_metadata').select('*').execute()
    
    if not result.data:
        print("❌ No clips found in database")
        return
    
    clips = result.data
    print(f"✅ Found {len(clips)} clips to update")
    
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    for clip in clips:
        try:
            clip_id = clip['id']
            transcript = clip.get('transcript', '')
            confidence_score = clip.get('confidence_score', 0.5)
            channel_name = clip.get('channel_name', 'unknown')
            
            # Check if already has past backend format (concise single-line with dict)
            if transcript and transcript.startswith("Score:") and "| {" in transcript[:100]:
                skipped_count += 1
                continue
            
            # Add scoring breakdown
            new_transcript = add_scoring_breakdown_to_transcript(transcript, confidence_score, channel_name)
            
            # Update in database
            update_result = sb.table('clips_metadata')\
                .update({'transcript': new_transcript})\
                .eq('id', clip_id)\
                .execute()
            
            if update_result.data:
                updated_count += 1
                if updated_count % 10 == 0:
                    print(f"  ✅ Updated {updated_count} clips...")
            else:
                print(f"  ⚠️ Failed to update clip {clip_id}")
                error_count += 1
                
        except Exception as e:
            print(f"  ❌ Error updating clip {clip.get('id', 'unknown')}: {e}")
            error_count += 1
    
    print(f"\n{'='*60}")
    print(f"📊 UPDATE COMPLETE")
    print(f"  • Total clips: {len(clips)}")
    print(f"  • Updated: {updated_count}")
    print(f"  • Skipped (already had breakdown): {skipped_count}")
    print(f"  • Errors: {error_count}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()

