#!/usr/bin/env python3
"""
Sort clips by tone/emotion into categorized folders.
Analyzes audio features and organizes clips based on their dominant emotional tone.
"""

import os
import sys
import shutil
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.audio_analysis_integration import analyze_audio_for_clip, CONTINUOUS_ANALYZER_AVAILABLE

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define tone categories and their thresholds
TONE_CATEGORIES = {
    "hype": {
        "description": "High energy, exciting moments",
        "color": "🔥",
        "priority": 1
    },
    "laughter": {
        "description": "Comedy, funny moments",
        "color": "😂",
        "priority": 2
    },
    "emotional": {
        "description": "Emotionally intense moments",
        "color": "💖",
        "priority": 3
    },
    "reaction": {
        "description": "Surprised/amazed reactions",
        "color": "😮",
        "priority": 4
    },
    "energetic": {
        "description": "High energy bursts",
        "color": "⚡",
        "priority": 5
    },
    "calm": {
        "description": "Low energy, calm moments",
        "color": "😌",
        "priority": 6
    },
    "boring": {
        "description": "Low engagement, monotone",
        "color": "😴",
        "priority": 7
    }
}

class ClipToneSorter:
    """Sorts clips into folders based on their emotional tone."""
    
    def __init__(self, input_dir: str, output_dir: str, copy_mode: bool = True):
        """
        Initialize the clip tone sorter.
        
        Args:
            input_dir: Directory containing raw clips to analyze
            output_dir: Base directory where sorted clips will be placed
            copy_mode: If True, copy clips. If False, move clips.
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.copy_mode = copy_mode
        self.stats = {category: 0 for category in TONE_CATEGORIES.keys()}
        self.stats["uncategorized"] = 0
        self.clip_results = []
        
        # Validate input directory
        if not self.input_dir.exists():
            raise ValueError(f"Input directory does not exist: {input_dir}")
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📂 Input directory: {self.input_dir}")
        logger.info(f"📂 Output directory: {self.output_dir}")
        logger.info(f"📋 Mode: {'COPY' if copy_mode else 'MOVE'}")
    
    def determine_tone_from_scores(self, scores: Dict[str, float]) -> Tuple[str, float]:
        """
        Determine the dominant tone from audio analysis scores.
        
        Args:
            scores: Dictionary of continuous scores (0-1) for each feature
            
        Returns:
            Tuple of (tone_category, confidence_score)
        """
        # Define tone detection logic with thresholds
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
        
        # Calm: Low energy but not boring (moderate quality)
        low_energy_score = scores.get('low_energy_score', 0)
        if low_energy_score > 0.5 and boring_score < 0.5:
            tone_scores['calm'] = low_energy_score * 0.7  # Lower confidence
        
        # If no clear tone detected, return uncategorized
        if not tone_scores:
            # Default categorization based on overall clip worthiness
            clip_worthiness = scores.get('clip_worthiness_score', 0)
            if clip_worthiness < 0.3:
                return 'boring', clip_worthiness
            else:
                return 'uncategorized', clip_worthiness
        
        # Return the tone with highest score
        dominant_tone = max(tone_scores.items(), key=lambda x: x[1])
        return dominant_tone[0], dominant_tone[1]
    
    def analyze_clip(self, clip_path: Path) -> Optional[Dict]:
        """
        Analyze a single clip and determine its tone.
        
        Args:
            clip_path: Path to the clip file
            
        Returns:
            Dictionary containing analysis results, or None if failed
        """
        try:
            logger.info(f"🎵 Analyzing: {clip_path.name}")
            
            # Analyze audio features
            analysis_result = analyze_audio_for_clip(str(clip_path))
            
            if not analysis_result:
                logger.warning(f"⚠️  No analysis results for: {clip_path.name}")
                return None
            
            # Extract scores
            scores = analysis_result.get('scores', {})
            
            if not scores:
                logger.warning(f"⚠️  No scores available for: {clip_path.name}")
                return None
            
            # Determine dominant tone
            tone, confidence = self.determine_tone_from_scores(scores)
            
            # Get combination results for additional context
            combination_results = analysis_result.get('combination_results', {})
            
            result = {
                'clip_path': clip_path,
                'clip_name': clip_path.name,
                'tone': tone,
                'confidence': confidence,
                'scores': scores,
                'combination_results': combination_results,
                'indicators': analysis_result.get('indicators', {})
            }
            
            logger.info(f"  ✅ Tone: {TONE_CATEGORIES.get(tone, {}).get('color', '❓')} {tone.upper()} (confidence: {confidence:.2f})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error analyzing {clip_path.name}: {e}")
            return None
    
    def create_category_folders(self):
        """Create folders for each tone category."""
        for category in TONE_CATEGORIES.keys():
            category_path = self.output_dir / category
            category_path.mkdir(exist_ok=True)
            logger.info(f"📁 Created folder: {category}")
        
        # Create uncategorized folder
        uncategorized_path = self.output_dir / "uncategorized"
        uncategorized_path.mkdir(exist_ok=True)
        logger.info(f"📁 Created folder: uncategorized")
    
    def sort_clip(self, analysis_result: Dict):
        """
        Sort a clip into the appropriate tone folder.
        
        Args:
            analysis_result: Dictionary containing clip analysis results
        """
        try:
            clip_path = analysis_result['clip_path']
            tone = analysis_result['tone']
            
            # Determine destination folder
            dest_folder = self.output_dir / tone
            dest_path = dest_folder / clip_path.name
            
            # Handle duplicate filenames
            counter = 1
            original_dest_path = dest_path
            while dest_path.exists():
                stem = original_dest_path.stem
                suffix = original_dest_path.suffix
                dest_path = dest_folder / f"{stem}_{counter}{suffix}"
                counter += 1
            
            # Copy or move the file
            if self.copy_mode:
                shutil.copy2(clip_path, dest_path)
                action = "Copied"
            else:
                shutil.move(clip_path, dest_path)
                action = "Moved"
            
            logger.info(f"  📦 {action} to: {tone}/{dest_path.name}")
            
            # Update statistics
            self.stats[tone] += 1
            
        except Exception as e:
            logger.error(f"❌ Error sorting {clip_path.name}: {e}")
    
    def get_video_files(self) -> List[Path]:
        """
        Get all video files from the input directory.
        
        Returns:
            List of video file paths
        """
        video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.mp3', '.wav']
        video_files = []
        
        for ext in video_extensions:
            video_files.extend(self.input_dir.glob(f"*{ext}"))
        
        return sorted(video_files)
    
    def process_all_clips(self):
        """Process all clips in the input directory."""
        # Create category folders
        self.create_category_folders()
        
        # Get all video files
        video_files = self.get_video_files()
        
        if not video_files:
            logger.warning(f"⚠️  No video files found in {self.input_dir}")
            return
        
        logger.info(f"📊 Found {len(video_files)} clips to process\n")
        
        # Process each clip
        for i, clip_path in enumerate(video_files, 1):
            logger.info(f"\n[{i}/{len(video_files)}] Processing: {clip_path.name}")
            
            # Analyze clip
            analysis_result = self.analyze_clip(clip_path)
            
            if analysis_result:
                # Store results
                self.clip_results.append(analysis_result)
                
                # Sort clip into appropriate folder
                self.sort_clip(analysis_result)
            else:
                # Move to uncategorized if analysis failed
                logger.warning(f"  ⚠️  Moving to uncategorized")
                uncategorized_path = self.output_dir / "uncategorized" / clip_path.name
                if self.copy_mode:
                    shutil.copy2(clip_path, uncategorized_path)
                else:
                    shutil.move(clip_path, uncategorized_path)
                self.stats["uncategorized"] += 1
        
        logger.info("\n" + "="*60)
        logger.info("✅ Processing complete!")
    
    def generate_report(self) -> str:
        """
        Generate a summary report of the sorting results.
        
        Returns:
            Formatted report string
        """
        report_lines = []
        report_lines.append("\n" + "="*60)
        report_lines.append("📊 CLIP TONE SORTING REPORT")
        report_lines.append("="*60)
        report_lines.append(f"\n📂 Input Directory: {self.input_dir}")
        report_lines.append(f"📂 Output Directory: {self.output_dir}")
        report_lines.append(f"📋 Mode: {'COPY' if self.copy_mode else 'MOVE'}")
        report_lines.append(f"\n📈 Total Clips Processed: {len(self.clip_results)}")
        report_lines.append("\n" + "-"*60)
        report_lines.append("📊 Distribution by Tone:")
        report_lines.append("-"*60)
        
        # Sort categories by count (descending)
        sorted_stats = sorted(self.stats.items(), key=lambda x: x[1], reverse=True)
        
        for category, count in sorted_stats:
            if count > 0:
                percentage = (count / len(self.clip_results) * 100) if self.clip_results else 0
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
                        report_lines.append(f"  • {clip['clip_name'][:50]} (confidence: {clip['confidence']:.2f})")
        
        report_lines.append("\n" + "="*60)
        
        report = "\n".join(report_lines)
        return report
    
    def save_detailed_report(self, output_file: str = "clip_sorting_report.json"):
        """
        Save detailed analysis results to a JSON file.
        
        Args:
            output_file: Name of the output JSON file
        """
        try:
            report_path = self.output_dir / output_file
            
            # Prepare data for JSON serialization
            json_data = {
                "input_directory": str(self.input_dir),
                "output_directory": str(self.output_dir),
                "mode": "copy" if self.copy_mode else "move",
                "total_clips": len(self.clip_results),
                "statistics": self.stats,
                "clips": []
            }
            
            # Add clip details
            for result in self.clip_results:
                clip_data = {
                    "clip_name": result['clip_name'],
                    "tone": result['tone'],
                    "confidence": float(result['confidence']),
                    "scores": {k: float(v) for k, v in result['scores'].items()},
                    "indicators": result['indicators']
                }
                json_data["clips"].append(clip_data)
            
            # Write to file
            with open(report_path, 'w') as f:
                json.dump(json_data, f, indent=2)
            
            logger.info(f"💾 Detailed report saved to: {report_path}")
            
        except Exception as e:
            logger.error(f"❌ Error saving detailed report: {e}")


def main():
    """Main function to run the clip tone sorter."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Sort clips by emotional tone into categorized folders")
    parser.add_argument("input_dir", help="Directory containing raw clips to analyze")
    parser.add_argument("-o", "--output", default="sorted_clips", 
                       help="Output directory for sorted clips (default: sorted_clips)")
    parser.add_argument("-m", "--move", action="store_true",
                       help="Move clips instead of copying them")
    parser.add_argument("--no-report", action="store_true",
                       help="Skip generating the summary report")
    
    args = parser.parse_args()
    
    # Check if continuous analyzer is available
    if not CONTINUOUS_ANALYZER_AVAILABLE:
        logger.warning("⚠️  Continuous audio analyzer not available. Analysis may be limited.")
    
    try:
        # Create sorter instance
        sorter = ClipToneSorter(
            input_dir=args.input_dir,
            output_dir=args.output,
            copy_mode=not args.move
        )
        
        # Process all clips
        sorter.process_all_clips()
        
        # Generate and display report
        if not args.no_report:
            report = sorter.generate_report()
            print(report)
            
            # Save detailed JSON report
            sorter.save_detailed_report()
        
        logger.info("\n✅ All done!")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()



