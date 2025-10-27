#!/usr/bin/env python3
"""
Sort clips from Supabase Storage by tone/emotion.
Downloads clips from Supabase, analyzes them, and organizes by tone.
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.db.supabase_client import get_client, get_public_url
from src.audio_analysis_integration import analyze_audio_for_clip

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Tone categories
TONE_CATEGORIES = {
    "hype": {"description": "High energy, exciting moments", "color": "🔥"},
    "laughter": {"description": "Comedy, funny moments", "color": "😂"},
    "emotional": {"description": "Emotionally intense moments", "color": "💖"},
    "reaction": {"description": "Surprised/amazed reactions", "color": "😮"},
    "energetic": {"description": "High energy bursts", "color": "⚡"},
    "calm": {"description": "Low energy, calm moments", "color": "😌"},
    "boring": {"description": "Low engagement, monotone", "color": "😴"}
}


class SupabaseClipSorter:
    """Downloads clips from Supabase Storage and sorts them by tone."""
    
    def __init__(self, bucket_name: str = "raw", output_dir: str = "sorted_clips", 
                 storage_prefix: str = "", max_clips: int = None):
        """
        Initialize the Supabase clip sorter.
        
        Args:
            bucket_name: Supabase storage bucket name
            output_dir: Local directory to save sorted clips
            storage_prefix: Path prefix in Supabase storage (e.g., "channel/stream_id")
            max_clips: Maximum number of clips to process (None = all)
        """
        self.bucket_name = bucket_name
        self.output_dir = Path(output_dir)
        self.storage_prefix = storage_prefix
        self.max_clips = max_clips
        self.stats = {category: 0 for category in TONE_CATEGORIES.keys()}
        self.stats["uncategorized"] = 0
        self.clip_results = []
        
        # Initialize Supabase client
        self.sb = self._initialize_supabase()
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📂 Supabase Bucket: {bucket_name}")
        logger.info(f"📂 Storage Prefix: {storage_prefix or '(root)'}")
        logger.info(f"📂 Output Directory: {output_dir}")
        if max_clips:
            logger.info(f"📊 Max Clips: {max_clips}")
    
    def _initialize_supabase(self):
        """Initialize Supabase client with service role."""
        try:
            # Use service role for full access
            os.environ["USE_SERVICE_ROLE"] = "true"
            sb = get_client()
            logger.info("✅ Connected to Supabase")
            return sb
        except Exception as e:
            logger.error(f"❌ Failed to connect to Supabase: {e}")
            raise
    
    def list_clips_in_storage(self) -> List[Dict]:
        """
        List all video clips in Supabase storage.
        
        Returns:
            List of file metadata dictionaries
        """
        try:
            logger.info(f"🔍 Listing clips in bucket '{self.bucket_name}'...")
            
            # List files in storage
            files = self.sb.storage.from_(self.bucket_name).list(self.storage_prefix)
            
            # Filter for video files
            video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv']
            video_files = []
            
            for file in files:
                file_name = file.get('name', '')
                if any(file_name.lower().endswith(ext) for ext in video_extensions):
                    video_files.append(file)
            
            logger.info(f"✅ Found {len(video_files)} video clips")
            
            # Limit clips if max_clips is set
            if self.max_clips and len(video_files) > self.max_clips:
                logger.info(f"📊 Limiting to {self.max_clips} clips")
                video_files = video_files[:self.max_clips]
            
            return video_files
            
        except Exception as e:
            logger.error(f"❌ Error listing clips: {e}")
            return []
    
    def download_clip(self, file_path: str, temp_dir: Path) -> Optional[Path]:
        """
        Download a clip from Supabase storage to temporary directory.
        
        Args:
            file_path: Path to file in Supabase storage
            temp_dir: Temporary directory to download to
            
        Returns:
            Path to downloaded file, or None if failed
        """
        try:
            # Construct full path
            full_path = f"{self.storage_prefix}/{file_path}" if self.storage_prefix else file_path
            
            # Download file
            logger.info(f"📥 Downloading: {file_path}")
            response = self.sb.storage.from_(self.bucket_name).download(full_path)
            
            # Save to temp file
            temp_file = temp_dir / file_path
            temp_file.parent.mkdir(parents=True, exist_ok=True)
            temp_file.write_bytes(response)
            
            logger.info(f"  ✅ Downloaded to: {temp_file.name}")
            return temp_file
            
        except Exception as e:
            logger.error(f"  ❌ Failed to download {file_path}: {e}")
            return None
    
    def determine_tone_from_scores(self, scores: Dict[str, float]) -> Tuple[str, float]:
        """
        Determine the dominant tone from audio analysis scores.
        
        Args:
            scores: Dictionary of continuous scores (0-1) for each feature
            
        Returns:
            Tuple of (tone_category, confidence_score)
        """
        tone_scores = {}
        
        # Hype: High energy + audience reaction
        hype_score = scores.get('hype_score', 0)
        if hype_score > 0.5:
            tone_scores['hype'] = hype_score
        
        # Laughter: High laughter detection
        laughter_score = scores.get('laughter_score', 0)
        if laughter_score > 0.6:
            tone_scores['laughter'] = laughter_score
        
        # Emotional: High emotional intensity
        emotional_score = scores.get('emotional_score', 0)
        if emotional_score > 0.5:
            tone_scores['emotional'] = emotional_score
        
        # Reaction: High audience score without laughter
        audience_score = scores.get('audience_score', 0)
        if audience_score > 0.6 and laughter_score < 0.5:
            tone_scores['reaction'] = audience_score
        
        # Energetic: High energy bursts
        energy_score = scores.get('energy_score', 0)
        if energy_score > 0.6:
            tone_scores['energetic'] = energy_score
        
        # Boring: High boring content score
        boring_score = scores.get('boring_content_score', 0)
        if boring_score > 0.6:
            tone_scores['boring'] = boring_score
        
        # Calm: Low energy but not boring
        low_energy_score = scores.get('low_energy_score', 0)
        if low_energy_score > 0.5 and boring_score < 0.5:
            tone_scores['calm'] = low_energy_score * 0.7
        
        # If no clear tone detected
        if not tone_scores:
            clip_worthiness = scores.get('clip_worthiness_score', 0)
            if clip_worthiness < 0.3:
                return 'boring', clip_worthiness
            else:
                return 'uncategorized', clip_worthiness
        
        # Return the tone with highest score
        dominant_tone = max(tone_scores.items(), key=lambda x: x[1])
        return dominant_tone[0], dominant_tone[1]
    
    def analyze_clip(self, clip_path: Path, file_name: str, storage_path: str) -> Optional[Dict]:
        """
        Analyze a single clip and determine its tone.
        
        Args:
            clip_path: Local path to the downloaded clip
            file_name: Original file name
            storage_path: Path in Supabase storage
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            logger.info(f"🎵 Analyzing: {file_name}")
            
            # Analyze audio features
            analysis_result = analyze_audio_for_clip(str(clip_path))
            
            if not analysis_result:
                logger.warning(f"⚠️  No analysis results for: {file_name}")
                return None
            
            # Extract scores
            scores = analysis_result.get('scores', {})
            
            if not scores:
                logger.warning(f"⚠️  No scores available for: {file_name}")
                return None
            
            # Determine dominant tone
            tone, confidence = self.determine_tone_from_scores(scores)
            
            result = {
                'file_name': file_name,
                'storage_path': storage_path,
                'local_path': str(clip_path),
                'tone': tone,
                'confidence': confidence,
                'scores': scores,
                'indicators': analysis_result.get('indicators', {})
            }
            
            emoji = TONE_CATEGORIES.get(tone, {}).get('color', '❓')
            logger.info(f"  ✅ Tone: {emoji} {tone.upper()} (confidence: {confidence:.2f})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error analyzing {file_name}: {e}")
            return None
    
    def save_clip_to_category(self, analysis_result: Dict, source_path: Path):
        """
        Save a clip to the appropriate tone category folder.
        
        Args:
            analysis_result: Dictionary containing clip analysis
            source_path: Path to the downloaded clip file
        """
        try:
            tone = analysis_result['tone']
            file_name = analysis_result['file_name']
            
            # Create category folder
            category_dir = self.output_dir / tone
            category_dir.mkdir(exist_ok=True)
            
            # Destination path
            dest_path = category_dir / file_name
            
            # Handle duplicates
            counter = 1
            original_dest_path = dest_path
            while dest_path.exists():
                stem = original_dest_path.stem
                suffix = original_dest_path.suffix
                dest_path = category_dir / f"{stem}_{counter}{suffix}"
                counter += 1
            
            # Copy file
            import shutil
            shutil.copy2(source_path, dest_path)
            
            logger.info(f"  💾 Saved to: {tone}/{dest_path.name}")
            
            # Update statistics
            self.stats[tone] += 1
            
        except Exception as e:
            logger.error(f"❌ Error saving {analysis_result['file_name']}: {e}")
    
    def create_category_folders(self):
        """Create folders for each tone category."""
        for category in TONE_CATEGORIES.keys():
            (self.output_dir / category).mkdir(exist_ok=True)
        (self.output_dir / "uncategorized").mkdir(exist_ok=True)
    
    def process_clips(self):
        """Main processing loop - download, analyze, and sort clips."""
        # Create category folders
        self.create_category_folders()
        
        # List clips in storage
        clips = self.list_clips_in_storage()
        
        if not clips:
            logger.warning("⚠️  No clips found in storage")
            return
        
        logger.info(f"\n📊 Processing {len(clips)} clips from Supabase...\n")
        
        # Create temporary directory for downloads
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            for i, clip_file in enumerate(clips, 1):
                file_name = clip_file.get('name', '')
                logger.info(f"\n[{i}/{len(clips)}] Processing: {file_name}")
                
                # Download clip
                local_clip = self.download_clip(file_name, temp_path)
                
                if not local_clip:
                    logger.warning(f"  ⚠️  Skipping - download failed")
                    self.stats["uncategorized"] += 1
                    continue
                
                # Analyze clip
                storage_path = f"{self.storage_prefix}/{file_name}" if self.storage_prefix else file_name
                analysis_result = self.analyze_clip(local_clip, file_name, storage_path)
                
                if analysis_result:
                    # Store results
                    self.clip_results.append(analysis_result)
                    
                    # Save to category folder
                    self.save_clip_to_category(analysis_result, local_clip)
                else:
                    logger.warning(f"  ⚠️  Moving to uncategorized")
                    uncategorized_path = self.output_dir / "uncategorized" / file_name
                    import shutil
                    shutil.copy2(local_clip, uncategorized_path)
                    self.stats["uncategorized"] += 1
        
        logger.info("\n" + "="*60)
        logger.info("✅ Processing complete!")
    
    def generate_report(self) -> str:
        """Generate a summary report of the sorting results."""
        report_lines = []
        report_lines.append("\n" + "="*60)
        report_lines.append("📊 SUPABASE CLIP TONE SORTING REPORT")
        report_lines.append("="*60)
        report_lines.append(f"\n📦 Supabase Bucket: {self.bucket_name}")
        report_lines.append(f"📂 Storage Prefix: {self.storage_prefix or '(root)'}")
        report_lines.append(f"📂 Output Directory: {self.output_dir}")
        report_lines.append(f"\n📈 Total Clips Processed: {len(self.clip_results)}")
        report_lines.append("\n" + "-"*60)
        report_lines.append("📊 Distribution by Tone:")
        report_lines.append("-"*60)
        
        # Sort categories by count
        sorted_stats = sorted(self.stats.items(), key=lambda x: x[1], reverse=True)
        
        for category, count in sorted_stats:
            if count > 0:
                percentage = (count / max(len(self.clip_results), 1) * 100)
                color = TONE_CATEGORIES.get(category, {}).get('color', '❓')
                desc = TONE_CATEGORIES.get(category, {}).get('description', 'Unknown')
                report_lines.append(f"{color} {category.upper():15} {count:3} clips ({percentage:5.1f}%) - {desc}")
        
        report_lines.append("\n" + "-"*60)
        report_lines.append("📋 Top Clips by Category:")
        report_lines.append("-"*60)
        
        # Group clips by tone
        clips_by_tone = {}
        for result in self.clip_results:
            tone = result['tone']
            if tone not in clips_by_tone:
                clips_by_tone[tone] = []
            clips_by_tone[tone].append(result)
        
        # Show top 3 clips per category
        for category in TONE_CATEGORIES.keys():
            if category in clips_by_tone:
                clips = sorted(clips_by_tone[category], key=lambda x: x['confidence'], reverse=True)[:3]
                if clips:
                    color = TONE_CATEGORIES[category]['color']
                    report_lines.append(f"\n{color} {category.upper()}:")
                    for clip in clips:
                        report_lines.append(f"  • {clip['file_name'][:50]} (confidence: {clip['confidence']:.2f})")
        
        report_lines.append("\n" + "="*60)
        
        return "\n".join(report_lines)
    
    def save_detailed_report(self, output_file: str = "supabase_sorting_report.json"):
        """Save detailed analysis results to JSON."""
        try:
            report_path = self.output_dir / output_file
            
            json_data = {
                "source": "supabase",
                "bucket": self.bucket_name,
                "storage_prefix": self.storage_prefix,
                "output_directory": str(self.output_dir),
                "total_clips": len(self.clip_results),
                "statistics": self.stats,
                "clips": []
            }
            
            for result in self.clip_results:
                clip_data = {
                    "file_name": result['file_name'],
                    "storage_path": result['storage_path'],
                    "tone": result['tone'],
                    "confidence": float(result['confidence']),
                    "scores": {k: float(v) for k, v in result['scores'].items()},
                    "indicators": result['indicators']
                }
                json_data["clips"].append(clip_data)
            
            with open(report_path, 'w') as f:
                json.dump(json_data, f, indent=2)
            
            logger.info(f"💾 Detailed report saved to: {report_path}")
            
        except Exception as e:
            logger.error(f"❌ Error saving detailed report: {e}")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Sort clips from Supabase Storage by tone")
    parser.add_argument("-b", "--bucket", default=os.getenv("STORAGE_BUCKET", "raw"),
                       help="Supabase storage bucket name (default: raw)")
    parser.add_argument("-p", "--prefix", default="",
                       help="Storage path prefix (e.g., 'channel/stream_id')")
    parser.add_argument("-o", "--output", default="sorted_clips_from_supabase",
                       help="Output directory for sorted clips")
    parser.add_argument("--max-clips", type=int, default=None,
                       help="Maximum number of clips to process")
    parser.add_argument("--no-report", action="store_true",
                       help="Skip generating the summary report")
    
    args = parser.parse_args()
    
    try:
        # Create sorter instance
        sorter = SupabaseClipSorter(
            bucket_name=args.bucket,
            output_dir=args.output,
            storage_prefix=args.prefix,
            max_clips=args.max_clips
        )
        
        # Process clips
        sorter.process_clips()
        
        # Generate and display report
        if not args.no_report:
            report = sorter.generate_report()
            print(report)
            
            # Save detailed JSON report
            sorter.save_detailed_report()
        
        logger.info("\n✅ All done!")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()




