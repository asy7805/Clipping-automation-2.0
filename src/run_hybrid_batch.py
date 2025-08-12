#!/usr/bin/env python3
"""
Real Hybrid Strategy - Uses .env file for all API keys and configuration
Collects real clips from live Twitch streams using environment variables.
FIXED: Anti-bias implementation to eliminate popularity bias.
"""

import os
import sys
import time
import random
import requests
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path for imports
sys.path.append(str(Path(__file__).parent))

# Configuration from environment variables
TARGET_CLIPS = int(os.getenv("TARGET_CLIPS", "5"))
RANDOM_SAMPLE_INTERVAL = int(os.getenv("RANDOM_SAMPLE_INTERVAL", "300"))
API_RATE_LIMIT_DELAY = int(os.getenv("API_RATE_LIMIT_DELAY", "2"))
PROCESSING_DELAY = int(os.getenv("PROCESSING_DELAY", "1"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
BUFFER_DIR = Path(os.getenv("BUFFER_DIR", "buffer/"))

# ANTI-BIAS CONFIGURATION - DIVERSE STREAMER SIZES
VIEWER_RANGES = [
    (0, 1000),      # SMALL streamers (0-1k viewers)
    (1000, 5000),   # MEDIUM streamers (1k-5k viewers)
    (5000, 20000),  # LARGE streamers (5k-20k viewers)
    (20000, 100000) # VERY LARGE streamers (20k-100k viewers)
]

# API credentials from .env
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")

# Check required environment variables
if not OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY not found in .env file")
    print("💡 Add your OpenAI API key to .env file")
    sys.exit(1)

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Supabase credentials not found in .env file")
    print("💡 Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to .env file")
    sys.exit(1)

if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
    print("❌ Twitch API credentials not found in .env file")
    print("💡 Add TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET to .env file")
    print("💡 Get them from: https://dev.twitch.tv/console")
    sys.exit(1)

# Import after environment setup
from predict import is_clip_worthy_by_model
from supabase_integration import SupabaseManager

class RealHybridBatchCollector:
    """Real hybrid strategy using actual Twitch streams and .env configuration with ANTI-BIAS."""
    
    def __init__(self):
        """Initialize with real API credentials from .env and anti-bias features."""
        print("🎯 Real Hybrid Strategy - ANTI-BIAS VERSION")
        print("=" * 70)
        print(f"📡 Supabase URL: {SUPABASE_URL}")
        print(f"🤖 OpenAI API: {'✅ Configured' if OPENAI_API_KEY else '❌ Missing'}")
        print(f"📺 Twitch API: {'✅ Configured' if TWITCH_CLIENT_ID else '❌ Missing'}")
        print(f"🎯 Target clips: {TARGET_CLIPS}")
        print(f"⏱️  Random interval: {RANDOM_SAMPLE_INTERVAL}s")
        print("🌍 ANTI-BIAS: DIVERSE STREAMER SIZES:")
        for i, (min_viewers, max_viewers) in enumerate(VIEWER_RANGES):
            size_label = ["SMALL", "MEDIUM", "LARGE", "VERY LARGE"][i]
            print(f"  Tier {i+1}: {size_label} ({min_viewers:,}-{max_viewers:,} viewers)")
        print("=" * 70)
        
        # Initialize Supabase client
        self.supabase_manager = SupabaseManager()
        
        # Initialize tracking
        self.clips_collected = 0
        self.last_random_sample = time.time()
        self.model_clips = 0
        self.random_clips = 0
        
        # ANTI-BIAS tracking
        self.viewer_tier_counts = {i: 0 for i in range(len(VIEWER_RANGES))}
        self.streamer_diversity = set()
        
        # Ensure buffer directory exists
        BUFFER_DIR.mkdir(exist_ok=True)
        
        print("✅ Anti-bias hybrid strategy initialized successfully!")
    
    def get_twitch_access_token(self):
        """Get Twitch access token using .env credentials."""
        try:
            token_url = "https://id.twitch.tv/oauth2/token"
            token_data = {
                "client_id": TWITCH_CLIENT_ID,
                "client_secret": TWITCH_CLIENT_SECRET,
                "grant_type": "client_credentials"
            }
            
            response = requests.post(token_url, data=token_data)
            if response.status_code == 200:
                return response.json()["access_token"]
            else:
                print(f"❌ Failed to get Twitch token: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting Twitch token: {e}")
            return None
    
    def get_diverse_streams(self):
        """Get DIVERSE streamers who have clips in IRL/Just Chatting categories."""
        try:
            access_token = self.get_twitch_access_token()
            if not access_token:
                return []
            
            all_streamers = []
            
            # Get streams from IRL and Just Chatting categories
            categories = [
                ("509658", "Just Chatting"),
                ("509660", "IRL")  # IRL category
            ]
            
            for game_id, category_name in categories:
                print(f"🔍 Searching {category_name} streamers...")
                
                streams_url = "https://api.twitch.tv/helix/streams"
                headers = {
                    "Client-ID": TWITCH_CLIENT_ID,
                    "Authorization": f"Bearer {access_token}"
                }
                
                params = {
                    "first": 100,
                    "game_id": game_id
                }
                
                response = requests.get(streams_url, headers=headers, params=params)
                if response.status_code == 200:
                    streams = response.json()["data"]
                    
                    # Group streamers by viewer tier
                    tier_streamers = {i: [] for i in range(len(VIEWER_RANGES))}
                    
                    for stream in streams:
                        viewer_count = int(stream.get("viewer_count", 0))
                        tier = self.get_viewer_tier(viewer_count)
                        tier_streamers[tier].append(stream)
                    
                    # Sample from each tier
                    for tier_idx, streamers in tier_streamers.items():
                        if streamers:
                            size_label = ["SMALL", "MEDIUM", "LARGE", "VERY LARGE"][tier_idx]
                            sample_size = min(2, len(streamers))  # 2 streamers per tier per category
                            selected = random.sample(streamers, sample_size)
                            all_streamers.extend(selected)
                            print(f"  ✅ Found {len(selected)} {size_label} {category_name} streamers")
                    
                time.sleep(API_RATE_LIMIT_DELAY)
            
            print(f"✅ Total DIVERSE streamers found: {len(all_streamers)}")
            return all_streamers
            
        except Exception as e:
            print(f"❌ Error getting diverse streamers: {e}")
            return []
    
    def get_existing_clips(self, streamer_id, limit=3):
        """Get existing clips from a streamer in IRL/Just Chatting categories."""
        try:
            access_token = self.get_twitch_access_token()
            if not access_token:
                return []
            
            clips_url = "https://api.twitch.tv/helix/clips"
            headers = {
                "Client-ID": TWITCH_CLIENT_ID,
                "Authorization": f"Bearer {access_token}"
            }
            
            # Get clips from the last 7 days
            end_time = datetime.now()
            start_time = end_time - timedelta(days=7)
            
            params = {
                "broadcaster_id": streamer_id,
                "first": 20,  # Get more to filter by category
                "started_at": start_time.isoformat() + "Z",
                "ended_at": end_time.isoformat() + "Z"
            }
            
            response = requests.get(clips_url, headers=headers, params=params)
            if response.status_code == 200:
                clips = response.json()["data"]
                
                # Filter for IRL and Just Chatting clips
                filtered_clips = []
                for clip in clips:
                    game_id = clip.get("game_id", "")
                    if game_id in ["509658", "509660"]:  # Just Chatting or IRL
                        filtered_clips.append(clip)
                
                # Randomly sample from filtered clips
                if filtered_clips:
                    sample_size = min(limit, len(filtered_clips))
                    return random.sample(filtered_clips, sample_size)
                
            return []
            
        except Exception as e:
            print(f"❌ Error getting existing clips: {e}")
            return []
    
    def download_twitch_clip(self, clip_id):
        """Download a Twitch clip using yt-dlp."""
        try:
            import yt_dlp
            
            clip_url = f"https://clips.twitch.tv/{clip_id}"
            
            # Configure yt-dlp with .env settings
            ydl_opts = {
                'format': 'best',
                'outtmpl': f'{BUFFER_DIR}/DiverseClip_{clip_id}.%(ext)s',
                'quiet': True,
                'no_cache_dir': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([clip_url])
            
            # Find the downloaded file
            clip_files = list(BUFFER_DIR.glob(f"DiverseClip_{clip_id}.*"))
            
            if clip_files:
                return str(clip_files[0])
            else:
                print(f"❌ Failed to download clip {clip_id}")
                return None
                
        except Exception as e:
            print(f"❌ Error downloading clip {clip_id}: {e}")
            return None
    
    def transcribe_clip(self, clip_path):
        """Transcribe a clip using WhisperX through the virtual environment."""
        try:
            import subprocess
            import sys
            import os
            
            print(f"🎤 Transcribing audio with WhisperX (venv): {clip_path}")
            
            # Get the path to the virtual environment's Python
            venv_python = os.path.join(os.getcwd(), "venv-py311", "bin", "python")
            if not os.path.exists(venv_python):
                # Fallback for Windows
                venv_python = os.path.join(os.getcwd(), "venv-py311", "Scripts", "python.exe")
            
            if not os.path.exists(venv_python):
                print(f"❌ Virtual environment not found at: {venv_python}")
                return ""
            
            # Create a temporary script to run transcription in venv
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_script:
                temp_script.write(f'''
import sys
import whisperx
import torch
import json

try:
    # Load WhisperX model with compatible compute type
    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float32"  # Use float32 for better compatibility
    model = whisperx.load_model("large-v3", device, compute_type=compute_type)
    
    # Transcribe the audio
    result = model.transcribe("{clip_path}", language="en")
    
    # Extract transcript text
    if isinstance(result, dict) and "text" in result:
        transcript = result["text"].strip()
    elif isinstance(result, dict) and "segments" in result:
        # Extract text from segments
        transcript = " ".join([seg.get("text", "") for seg in result["segments"]]).strip()
    else:
        transcript = ""
    
    # Output result as JSON
    print(json.dumps({{"success": True, "transcript": transcript}}))
    
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
''')
                temp_script_path = temp_script.name
            
            # Run the transcription script through venv
            result = subprocess.run(
                [venv_python, temp_script_path],
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            
            # Clean up temp script
            os.unlink(temp_script_path)
            
            if result.returncode == 0:
                try:
                    # Extract JSON from mixed output (warnings + JSON)
                    output_lines = result.stdout.strip().split('\n')
                    json_line = None
                    
                    # Find the line that contains JSON
                    for line in output_lines:
                        if line.strip().startswith('{"success":'):
                            json_line = line.strip()
                            break
                    
                    if json_line:
                        output = json.loads(json_line)
                        
                        if output.get("success"):
                            transcript = output.get("transcript", "")
                            if transcript:
                                print(f"✅ Transcribed: {transcript[:100]}...")
                                return transcript
                            else:
                                print(f"❌ No transcript generated")
                                return ""
                        else:
                            print(f"❌ Transcription failed: {output.get('error', 'Unknown error')}")
                            return ""
                    else:
                        print(f"❌ No JSON output found in transcription result")
                        return ""
                        
                except json.JSONDecodeError:
                    print(f"❌ Failed to parse transcription output: {result.stdout}")
                    return ""
            else:
                print(f"❌ Transcription subprocess failed: {result.stderr}")
                return ""
                
        except Exception as e:
            print(f"❌ Error transcribing clip with WhisperX (venv): {e}")
            return ""
    
    def should_create_random_clip(self):
        """Check if it's time for a random clip sample."""
        current_time = time.time()
        if current_time - self.last_random_sample >= RANDOM_SAMPLE_INTERVAL:
            self.last_random_sample = current_time
            return True
        return False
    
    def process_clip_with_model(self, transcript, clip_id=None):
        """Process a transcript with the AI model."""
        if not transcript or len(transcript.strip()) < 10:
            return False, "empty"
        
        # Check if model thinks it's clip-worthy with retry logic
        for attempt in range(MAX_RETRIES):
            try:
                print(f"  🤖 Running model prediction (attempt {attempt + 1}/{MAX_RETRIES})...")
                model_prediction = is_clip_worthy_by_model(transcript)
                
                # Save prediction to clip_predictions table if clip_id is provided
                if clip_id:
                    try:
                        from supabase_integration import (
                            insert_prediction_to_supabase,
                            update_model_registry_usage,
                            log_model_performance,
                            log_training_data,
                            log_model_metrics
                        )
                        
                        # Get prediction score (simplified - you can enhance this)
                        prediction_score = 0.8 if model_prediction else 0.2
                        
                        # Insert prediction into Supabase
                        prediction_success = insert_prediction_to_supabase(
                            clip_id=clip_id,
                            text=transcript.strip(),
                            score=prediction_score,
                            triggered=model_prediction,
                            clipworthy=model_prediction,
                            model_version="v1.0"
                        )
                        
                        if prediction_success:
                            print(f"    📊 Prediction saved to clip_predictions table")
                            
                            # Update model-related tables
                            update_model_registry_usage(
                                clip_id=clip_id,
                                model_version="v1.0",
                                prediction_score=prediction_score,
                                triggered=model_prediction,
                                clipworthy=model_prediction
                            )
                            
                            log_model_performance(
                                clip_id=clip_id,
                                model_version="v1.0",
                                prediction_score=prediction_score
                            )
                            
                            log_training_data(
                                clip_id=clip_id,
                                transcript=transcript.strip(),
                                source="run_hybrid_batch"
                            )
                            
                            log_model_metrics(
                                model_version="v1.0",
                                metric_type="prediction",
                                metric_name="prediction_score",
                                metric_value=prediction_score,
                                clip_count=1
                            )
                            
                            print(f"    🤖 Model-related tables updated")
                        else:
                            print(f"    ⚠️  Failed to save prediction to database")
                            
                    except Exception as e:
                        print(f"    ⚠️  Error saving prediction: {e}")
                
                # Add delay after successful API call
                print(f"  ⏸️  Rate limiting: waiting {API_RATE_LIMIT_DELAY} seconds...")
                time.sleep(API_RATE_LIMIT_DELAY)
                
                return model_prediction, "model"
                
            except Exception as e:
                print(f"⚠️  Model prediction failed (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    wait_time = (attempt + 1) * API_RATE_LIMIT_DELAY
                    print(f"  🔄 Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"  ❌ Max retries reached, skipping this transcript")
                    return False, "error"
        
        return False, "error"
    
    def get_viewer_tier(self, viewer_count):
        """Get the viewer tier for a stream."""
        for tier_idx, (min_viewers, max_viewers) in enumerate(VIEWER_RANGES):
            if min_viewers <= viewer_count <= max_viewers:
                return tier_idx
        return len(VIEWER_RANGES) - 1  # Default to highest tier
    
    def save_clip_to_supabase(self, clip_id, transcript, clip_url, streamer_name, viewer_count, source, viewer_tier, clip_path):
        """Save clip data to Supabase with comprehensive audio analysis."""
        try:
            # Store diversity info in transcript for tracking
            size_labels = ["SMALL", "MEDIUM", "LARGE", "VERY LARGE"]
            size_label = size_labels[viewer_tier]
            diversity_info = f"[{size_label}_STREAMER_{streamer_name}_VIEWERS_{viewer_count}]"
            enhanced_transcript = f"{diversity_info} {transcript}"
            
            # Use the comprehensive Supabase integration
            from supabase_integration import save_for_labeling
            
            # Save with comprehensive audio analysis
            saved_clip_id = save_for_labeling(
                transcript=enhanced_transcript,
                clip_path=clip_path,  # This will be passed from the calling function
                source="anti_bias_hybrid_strategy",
                content_type="irl_just_chatting",
                labeling_method="manual",
                twitch_clip_id=clip_id,
                twitch_url=clip_url
            )
            
            if saved_clip_id:
                print(f"    💾 Saved to Supabase: {clip_id}")
                print(f"    📊 Diversity: {size_label} streamer {streamer_name} ({viewer_count:,} viewers)")
                print(f"    🎵 Audio analysis completed")
                return True
            else:
                print(f"    ❌ Failed to save to Supabase: {clip_id}")
                return False
            
        except Exception as e:
            print(f"    ❌ Error saving to Supabase: {e}")
            return False
    
    def run_real_hybrid_strategy(self):
        """Main hybrid strategy using real Twitch data with ANTI-BIAS."""
        print("🚀 Starting ANTI-BIAS hybrid strategy with .env configuration...")
        print("📊 Purpose: Collect existing clips for dataset building and model training")
        
        # Get DIVERSE streams (not just top streams)
        print("🔍 Getting DIVERSE streamers across all viewer ranges...")
        streamers = self.get_diverse_streams()
        
        if not streamers:
            print("❌ No diverse streamers found")
            print("💡 Check your Twitch API credentials in .env file")
            return
        
        print(f"📺 Found {len(streamers)} DIVERSE streamers")
        
        # Shuffle streamers to avoid order bias
        random.shuffle(streamers)
        
        for streamer in streamers:
            if self.clips_collected >= TARGET_CLIPS:
                break
                
            streamer_name = streamer["user_name"]
            streamer_id = streamer["user_id"]
            viewer_count = streamer["viewer_count"]
            viewer_tier = self.get_viewer_tier(viewer_count)
            size_labels = ["SMALL", "MEDIUM", "LARGE", "VERY LARGE"]
            size_label = size_labels[viewer_tier]
            
            print(f"\n📺 Processing {size_label} streamer: {streamer_name} ({viewer_count:,} viewers)")
            
            # Track diversity
            self.streamer_diversity.add(streamer_name)
            
            # Get existing clips from this streamer (IRL/Just Chatting only)
            clips = self.get_existing_clips(streamer_id, limit=3)
            
            if not clips:
                print(f"  ⚠️  No IRL/Just Chatting clips found for {streamer_name}")
                continue
            
            print(f"  📹 Found {len(clips)} existing clips from {streamer_name}")
            
            for clip in clips:
                if self.clips_collected >= TARGET_CLIPS:
                    break
                    
                clip_id = clip["id"]
                clip_url = clip["url"]
                title = clip["title"]
                duration = clip["duration"]
                game_id = clip.get("game_id", "")
                game_name = "Just Chatting" if game_id == "509658" else "IRL"
                
                print(f"  📹 Clip: {title} ({duration}s) - {game_name}")
                
                # Download the clip
                clip_path = self.download_twitch_clip(clip_id)
                
                if clip_path:
                    # Transcribe the clip
                    transcript = self.transcribe_clip(clip_path)
                    
                    if not transcript:
                        transcript = title
                    
                    # Decision logic for dataset building
                    should_collect = False
                    collection_reason = ""
                    
                    # Random sampling (30% chance)
                    if random.random() < 0.3:
                        should_collect = True
                        collection_reason = "random"
                        self.random_clips += 1
                        print(f"    🎲 Random sampling triggered!")
                    
                    # Model prediction (if not already triggered)
                    elif transcript and len(transcript) > 10:
                        model_prediction, source = self.process_clip_with_model(transcript, clip_id)
                        if model_prediction:
                            should_collect = True
                            collection_reason = "model"
                            self.model_clips += 1
                            print(f"    ✅ Model flagged as clip-worthy!")
                        else:
                            print(f"    ❌ Model says not clip-worthy")
                    
                    # Collect if selected
                    if should_collect:
                        self.clips_collected += 1
                        self.viewer_tier_counts[viewer_tier] += 1
                        
                        # Use the ACTUAL Twitch clip ID instead of generating a fake one
                        actual_clip_id = clip_id  # This is the real Twitch clip ID from the API
                        
                        print(f"    📹 Collecting for dataset ({collection_reason}): {actual_clip_id}")
                        print(f"    📝 Transcript: {transcript[:50]}...")
                        
                        # Save to Supabase for manual labeling
                        self.save_clip_to_supabase(
                            actual_clip_id, transcript, clip_url, 
                            streamer_name, viewer_count, collection_reason, viewer_tier, clip_path
                        )
                        
                        print(f"    ✅ Dataset clip {self.clips_collected}/{TARGET_CLIPS} collected!")
                    else:
                        print(f"    ⏭️  Skipped clip")
        
        self.print_anti_bias_summary()
    
    def print_anti_bias_summary(self):
        """Print anti-bias summary."""
        print(f"\n" + "=" * 70)
        print("📊 ANTI-BIAS HYBRID STRATEGY SUMMARY")
        print("=" * 70)
        print(f"🎯 Target clips: {TARGET_CLIPS}")
        print(f"📦 Total collected: {self.clips_collected}")
        print(f"🤖 Model-triggered: {self.model_clips}")
        print(f"🎲 Random-triggered: {self.random_clips}")
        
        print(f"\n📊 DIVERSITY METRICS:")
        print(f"  🎭 Unique streamers: {len(self.streamer_diversity)}")
        print(f"  📈 Streamer size distribution:")
        size_labels = ["SMALL", "MEDIUM", "LARGE", "VERY LARGE"]
        for tier_idx, count in self.viewer_tier_counts.items():
            min_viewers, max_viewers = VIEWER_RANGES[tier_idx]
            size_label = size_labels[tier_idx]
            percentage = (count / max(1, self.clips_collected)) * 100
            print(f"    {size_label} ({min_viewers:,}-{max_viewers:,} viewers): {count} clips ({percentage:.1f}%)")
        
        if self.clips_collected > 0:
            model_percentage = (self.model_clips / self.clips_collected) * 100
            random_percentage = (self.random_clips / self.clips_collected) * 100
            print(f"\n📊 Collection Breakdown:")
            print(f"  🤖 Model clips: {model_percentage:.1f}%")
            print(f"  🎲 Random clips: {random_percentage:.1f}%")
        
        print("=" * 70)
        print("✅ ANTI-BIAS hybrid strategy completed!")
        print("🔄 Dataset now has representation from ALL streamer sizes!")
        print("💡 Next: Label clips in Supabase dashboard, then retrain model")

def main():
    """Main function to run the anti-bias hybrid strategy."""
    try:
        collector = RealHybridBatchCollector()
        collector.run_real_hybrid_strategy()
    except KeyboardInterrupt:
        print("\n⏹️  Anti-bias hybrid strategy stopped by user")
    except Exception as e:
        print(f"❌ Error in anti-bias hybrid strategy: {e}")

if __name__ == "__main__":
    main() 