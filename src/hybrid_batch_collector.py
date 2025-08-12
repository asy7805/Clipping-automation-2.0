#!/usr/bin/env python3
"""
Hybrid Batch Collection Script for Self-Clipping AI Model.
Combines model predictions with random sampling to collect clips for labeling.
"""

import time
import random
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predict import is_clip_worthy_by_model
from realtime_transcription import RealtimeTranscription

class HybridBatchCollector:
    """Collects clips using both model predictions and random sampling"""
    
    def __init__(self, target_clips=100, random_interval_minutes=2):
        self.target_clips = target_clips
        self.random_interval_minutes = random_interval_minutes
        self.collected_clips = 0
        self.model_clips = 0
        self.random_clips = 0
        
        # Initialize tracking
        self.last_random_time = datetime.now()
        self.clip_data = []
        
        # Setup paths
        self.data_dir = Path("data")
        self.csv_path = self.data_dir / "clips.csv"
        
        # Initialize realtime transcription
        self.textion = RealtimeTranscription()
        
        print(f"🎯 Hybrid Batch Collector initialized")
        print(f"📊 Target: {target_clips} clips")
        print(f"🎲 Random sampling every {random_interval_minutes} minutes")
        print("=" * 60)
    
    def should_create_random_clip(self):
        """Check if it's time for a random clip"""
        now = datetime.now()
        time_since_last = now - self.last_random_time
        return time_since_last >= timedelta(minutes=self.random_interval_minutes)
    
    def save_label_to_supabase(self, clip_id, transcript, label=None, source="auto", views=0, watch_time=0, likes=0, comments=0, auto_label="", label_type="manual", engagement_score=0, timestamp=None):
        """
        Save a label entry to Supabase clips table with full CSV format.
        
        Args:
            clip_id: The unique clip ID
            transcript: The transcript text
            label: The label value (can be None for unlabeled clips)
            source: The source of the clip ("auto", "manual", "ml", "random", etc.)
            views: Number of views (default: 0)
            watch_time: Watch time in seconds (default: 0)
            likes: Number of likes (default: 0)
            comments: Number of comments (default: 0)
            auto_label: Auto-assigned label (default: "")
            label_type: Type of labeling ("manual", "auto", "review_needed") (default: "manual")
            engagement_score: Calculated engagement score (default: 0)
            timestamp: Timestamp of creation (default: None, will use current time)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from supabase import create_client
            import os
            from datetime import datetime
            
            # Get Supabase credentials from environment
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
            
            if not supabase_url or not supabase_key:
                print("⚠️  Supabase credentials not found in environment variables")
                print("   Please set SUPABASE_URL and SUPABASE_ANON_KEY or SUPABASE_KEY")
                return False
            
            # Create Supabase client
            supabase = create_client(supabase_url, supabase_key)
            
            # Use current timestamp if none provided
            if timestamp is None:
                timestamp = datetime.now().isoformat()
            
            # Prepare data for insertion with full CSV format
            data = {
                "clip_id": clip_id,
                "text": transcript,
                "label": label,
                "views": views,
                "watch_time": watch_time,
                "likes": likes,
                "comments": comments,
                "auto_label": auto_label,
                "label_type": label_type,
                "engagement_score": engagement_score,
                "timestamp": timestamp,
                "source": source
            }
            
            # Insert into Supabase
            response = supabase.table("clips").insert(data).execute()
            
            if response.data:
                print(f"✅ Saved to Supabase: {clip_id}")
                return True
            else:
                print(f"❌ No data returned from Supabase insert for {clip_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error saving to Supabase: {e}")
            return False

    def save_for_labeling(self, transcript, clip_path, clip_id=None):
        """Save clip data for later labeling using Supabase"""
        if clip_id is None:
            clip_id = f"hybrid_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.collected_clips}"
        
        # Try Supabase first
        try:
            from src.supabase_integration import save_for_labeling as supabase_save
            supabase_clip_id = supabase_save(transcript, str(clip_path), source="hybrid_batch", is_random=False)
            if supabase_clip_id:
                print(f"💾 Saved clip {clip_id} for labeling (Supabase)")
                return clip_id
        except Exception as e:
            print(f"⚠️  Supabase save failed, falling back to CSV: {e}")
        
        # Fallback to CSV method
        clip_data = {
            'clip_id': clip_id,
            'text': transcript,
            'label': '',  # Leave blank for manual labeling
            'clip_path': str(clip_path),
            'source': 'hybrid_batch',
            'timestamp': datetime.now().isoformat()
        }
        
        # Add to our collection
        self.clip_data.append(clip_data)
        
        # Save to CSV
        self._append_to_csv(clip_data)
        
        print(f"💾 Saved clip {clip_id} for labeling (CSV fallback)")
        
        # Also try to save to Supabase as a supplement (don't modify existing CSV behavior)
        try:
            self.save_label_to_supabase(clip_id, transcript, label=None, source="auto")
        except Exception as e:
            print(f"⚠️  Supplemental Supabase save failed: {e}")
        
        return clip_id
    
    def _append_to_csv(self, clip_data):
        """Append clip data to CSV file (fallback method)"""
        try:
            # Load existing data
            if self.csv_path.exists():
                df = pd.read_csv(self.csv_path)
            else:
                df = pd.DataFrame(columns=['clip_id', 'text', 'label', 'clip_path', 'source', 'timestamp'])
            
            # Add new row
            new_row = pd.DataFrame([clip_data])
            df = pd.concat([df, new_row], ignore_index=True)
            
            # Save back to CSV
            df.to_csv(self.csv_path, index=False)
            
        except Exception as e:
            print(f"❌ Error saving to CSV: {e}")
    
    def create_clip_from_buffer(self, transcript):
        """Create a clip from the current buffer"""
        try:
            # Generate clip ID
            clip_id = f"hybrid_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.collected_clips}"
            
            # Create clip path (this would integrate with your existing clip creation logic)
            clip_path = self.data_dir / "raw_clips" / "hybrid" / f"{clip_id}.mp4"
            clip_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Here you would integrate with your existing clip creation system
            # For now, we'll create a placeholder file
            clip_path.touch()
            
            return clip_path, clip_id
            
        except Exception as e:
            print(f"❌ Error creating clip: {e}")
            return None, None
    
    def process_transcript(self, transcript):
        """Process a transcript and decide whether to create a clip"""
        if self.collected_clips >= self.target_clips:
            return False
        
        should_clip = False
        clip_reason = ""
        
        # Check model prediction
        try:
            model_prediction = is_clip_worthy_by_model(transcript)
            if model_prediction:
                should_clip = True
                clip_reason = "model"
                self.model_clips += 1
                print(f"🤖 Model flagged clip: {transcript[:50]}...")
        except Exception as e:
            print(f"⚠️  Model prediction failed: {e}")
        
        # Check random sampling
        if self.should_create_random_clip():
            should_clip = True
            clip_reason = "random"
            self.random_clips += 1
            self.last_random_time = datetime.now()
            print(f"🎲 Random clip triggered: {transcript[:50]}...")
        
        # Create clip if needed
        if should_clip:
            clip_path, clip_id = self.create_clip_from_buffer(transcript)
            if clip_path:
                self.save_for_labeling(transcript, clip_path, clip_id)
                self.collected_clips += 1
                
                print(f"📹 Created clip ({clip_reason}): {clip_id}")
                print(f"📊 Progress: {self.collected_clips}/{self.target_clips}")
        
        return should_clip
    
    def run_live_collection(self):
        """Run live collection from Twitch stream"""
        print("🎥 Starting live collection...")
        print("💡 Press Ctrl+C to stop early")
        
        try:
            # Start realtime transcription
            self.textion.start()
            
            while self.collected_clips < self.target_clips:
                # Get latest transcript from buffer
                transcript = self.textion.get_latest_transcript()
                
                if transcript and transcript.strip():
                    self.process_transcript(transcript)
                
                # Small delay to prevent excessive CPU usage
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n⏹️  Collection stopped by user")
        except Exception as e:
            print(f"❌ Error during collection: {e}")
        finally:
            self.textion.stop()
    
    def run_simulation(self, duration_minutes=30):
        """Run simulation with mock transcripts for testing"""
        print(f"🧪 Running simulation for {duration_minutes} minutes...")
        
        # Sample transcripts for testing
        sample_transcripts = [
            "That was absolutely insane! Did you see that play?",
            "I can't believe what just happened, this is crazy!",
            "What a clutch moment, this is going to be a great clip!",
            "The timing on that was perfect, absolutely perfect!",
            "This is the kind of content that makes streaming worth it!",
            "I'm speechless, that was incredible!",
            "The chat is going wild right now!",
            "This is definitely going to be a highlight reel moment!",
            "I've never seen anything like that before!",
            "That was the most epic thing I've ever witnessed!"
        ]
        
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        try:
            while datetime.now() < end_time and self.collected_clips < self.target_clips:
                # Simulate transcript every few seconds
                if random.random() < 0.3:  # 30% chance each iteration
                    transcript = random.choice(sample_transcripts)
                    self.process_transcript(transcript)
                
                time.sleep(2)  # Wait 2 seconds between iterations
                
        except KeyboardInterrupt:
            print("\n⏹️  Simulation stopped by user")
    
    def print_summary(self):
        """Print collection summary"""
        print("\n" + "=" * 60)
        print("📊 HYBRID BATCH COLLECTION SUMMARY")
        print("=" * 60)
        print(f"🎯 Target clips: {self.target_clips}")
        print(f"📹 Total collected: {self.collected_clips}")
        print(f"🤖 Model-triggered clips: {self.model_clips}")
        print(f"🎲 Random clips: {self.random_clips}")
        print(f"📁 Saved to: {self.csv_path}")
        
        if self.collected_clips > 0:
            model_percentage = (self.model_clips / self.collected_clips) * 100
            random_percentage = (self.random_clips / self.collected_clips) * 100
            print(f"📈 Model success rate: {model_percentage:.1f}%")
            print(f"🎲 Random sampling rate: {random_percentage:.1f}%")
        
        print("=" * 60)
        print("✅ Collection complete! Ready for manual labeling.")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Hybrid Batch Clip Collection")
    parser.add_argument("--target", type=int, default=100, help="Target number of clips to collect")
    parser.add_argument("--random-interval", type=int, default=2, help="Random sampling interval in minutes")
    parser.add_argument("--mode", choices=["live", "simulation"], default="simulation", help="Collection mode")
    parser.add_argument("--duration", type=int, default=30, help="Simulation duration in minutes")
    
    args = parser.parse_args()
    
    # Initialize collector
    collector = HybridBatchCollector(
        target_clips=args.target,
        random_interval_minutes=args.random_interval
    )
    
    # Run collection
    if args.mode == "live":
        collector.run_live_collection()
    else:
        collector.run_simulation(args.duration)
    
    # Print summary
    collector.print_summary()

if __name__ == "__main__":
    main() 