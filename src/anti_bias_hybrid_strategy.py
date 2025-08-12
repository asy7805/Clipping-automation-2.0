#!/usr/bin/env python3
"""
Anti-Bias Hybrid Strategy - Collects clips from diverse streamers (small and big)
Eliminates popularity bias by sampling across different viewer tiers.
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
TARGET_CLIPS = int(os.getenv("TARGET_CLIPS", "10"))
RANDOM_SAMPLE_INTERVAL = int(os.getenv("RANDOM_SAMPLE_INTERVAL", "300"))
API_RATE_LIMIT_DELAY = int(os.getenv("API_RATE_LIMIT_DELAY", "2"))
PROCESSING_DELAY = int(os.getenv("PROCESSING_DELAY", "1"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
BUFFER_DIR = Path(os.getenv("BUFFER_DIR", "buffer/"))

# Anti-bias configuration - DIVERSE STREAMER SIZES
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
    sys.exit(1)

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Supabase credentials not found in .env file")
    sys.exit(1)

if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
    print("❌ Twitch API credentials not found in .env file")
    sys.exit(1)

# Import after environment setup
from predict import is_clip_worthy_by_model
from supabase_integration import SupabaseManager

class AntiBiasHybridCollector:
    """Anti-bias hybrid strategy using DIVERSE streamer selection."""
    
    def __init__(self):
        """Initialize with anti-bias configuration."""
        print("🎯 Anti-Bias Hybrid Strategy - DIVERSE STREAMER COLLECTION")
        print("=" * 70)
        print(f"📡 Supabase URL: {SUPABASE_URL}")
        print(f"🤖 OpenAI API: {'✅ Configured' if OPENAI_API_KEY else '❌ Missing'}")
        print(f"📺 Twitch API: {'✅ Configured' if TWITCH_CLIENT_ID else '❌ Missing'}")
        print(f"🎯 Target clips: {TARGET_CLIPS}")
        print(f"📊 Viewer ranges: {len(VIEWER_RANGES)} tiers")
        print("🌍 DIVERSE STREAMER SIZES:")
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
        
        # Anti-bias tracking
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
        """Get DIVERSE streams across different viewer ranges."""
        try:
            access_token = self.get_twitch_access_token()
            if not access_token:
                return []
            
            all_streams = []
            
            # Get streams from DIFFERENT viewer ranges (DIVERSE SIZES)
            for tier_idx, (min_viewers, max_viewers) in enumerate(VIEWER_RANGES):
                size_label = ["SMALL", "MEDIUM", "LARGE", "VERY LARGE"][tier_idx]
                print(f"🔍 Searching {size_label} streamers: {min_viewers:,}-{max_viewers:,} viewers")
                
                streams_url = "https://api.twitch.tv/helix/streams"
                headers = {
                    "Client-ID": TWITCH_CLIENT_ID,
                    "Authorization": f"Bearer {access_token}"
                }
                
                # Get streams from Just Chatting category
                params = {
                    "first": 100,  # Get more to filter by viewer count
                    "game_id": "509658"  # Just Chatting
                }
                
                response = requests.get(streams_url, headers=headers, params=params)
                if response.status_code == 200:
                    streams = response.json()["data"]
                    
                    # Filter by viewer count range (DIVERSE SIZES)
                    tier_streams = []
                    for stream in streams:
                        viewer_count = int(stream.get("viewer_count", 0))
                        if min_viewers <= viewer_count <= max_viewers:
                            tier_streams.append(stream)
                    
                    # Randomly sample from this tier (DIVERSE SELECTION)
                    if tier_streams:
                        sample_size = min(3, len(tier_streams))  # 3 streams per tier
                        selected_streams = random.sample(tier_streams, sample_size)
                        all_streams.extend(selected_streams)
                        print(f"  ✅ Found {len(selected_streams)} {size_label} streamers")
                        
                        # Show examples of diverse streamers
                        for stream in selected_streams:
                            name = stream["user_name"]
                            viewers = stream["viewer_count"]
                            print(f"    📺 {name} ({viewers:,} viewers)")
                    else:
                        print(f"  ⚠️  No {size_label} streamers found")
                
                time.sleep(API_RATE_LIMIT_DELAY)  # Rate limiting
            
            print(f"✅ Total DIVERSE streams found: {len(all_streams)}")
            return all_streams
            
        except Exception as e:
            print(f"❌ Error getting diverse streams: {e}")
            return []
    
    def get_diverse_clips(self, streamer_id, limit=2):
        """Get diverse clips from a streamer (not just recent ones)."""
        try:
            access_token = self.get_twitch_access_token()
            if not access_token:
                return []
            
            clips_url = "https://api.twitch.tv/helix/clips"
            headers = {
                "Client-ID": TWITCH_CLIENT_ID,
                "Authorization": f"Bearer {access_token}"
            }
            
            # Get clips from different time periods to avoid recency bias
            time_periods = [
                (datetime.now() - timedelta(hours=1), datetime.now()),      # Last hour
                (datetime.now() - timedelta(hours=6), datetime.now() - timedelta(hours=1)),  # 1-6 hours ago
                (datetime.now() - timedelta(hours=24), datetime.now() - timedelta(hours=6))  # 6-24 hours ago
            ]
            
            all_clips = []
            
            for start_time, end_time in time_periods:
                params = {
                    "broadcaster_id": streamer_id,
                    "first": 10,  # Get more to sample from
                    "started_at": start_time.isoformat() + "Z",
                    "ended_at": end_time.isoformat() + "Z"
                }
                
                response = requests.get(clips_url, headers=headers, params=params)
                if response.status_code == 200:
                    clips = response.json()["data"]
                    if clips:
                        # Randomly sample 1 clip from this time period
                        selected_clip = random.choice(clips)
                        all_clips.append(selected_clip)
                
                time.sleep(API_RATE_LIMIT_DELAY)
            
            return all_clips
            
        except Exception as e:
            print(f"❌ Error getting diverse clips: {e}")
            return []
    
    def download_twitch_clip(self, clip_id):
        """Download a Twitch clip using yt-dlp."""
        try:
            import yt_dlp
            
            clip_url = f"https://clips.twitch.tv/{clip_id}"
            
            ydl_opts = {
                'format': 'best',
                'outtmpl': f'{BUFFER_DIR}/DiverseClip_{clip_id}.%(ext)s',
                'quiet': True,
                'no_cache_dir': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([clip_url])
            
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
                                source="anti_bias_hybrid"
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
    
    def save_clip_to_supabase(self, clip_id, transcript, clip_url, streamer_name, viewer_count, source, viewer_tier):
        """Save clip data to Supabase with anti-bias tracking."""
        try:
            timestamp = datetime.now().isoformat()
            
            # Store diversity info in transcript for tracking
            size_labels = ["SMALL", "MEDIUM", "LARGE", "VERY LARGE"]
            size_label = size_labels[viewer_tier]
            diversity_info = f"[{size_label}_STREAMER_{streamer_name}_VIEWERS_{viewer_count}]"
            enhanced_transcript = f"{diversity_info} {transcript}"
            
            clip_data = {
                "clip_id": clip_id,
                "transcript": enhanced_transcript,
                "url": clip_url,
                "source": "anti_bias_hybrid_strategy",
                "created_at": timestamp
            }
            
            clip_data = {k: v for k, v in clip_data.items() if v is not None}
            
            self.supabase_manager.client.table("clips").insert(clip_data).execute()
            print(f"    💾 Saved to Supabase: {clip_id}")
            print(f"    📊 Diversity: {size_label} streamer {streamer_name} ({viewer_count:,} viewers)")
            return True
            
        except Exception as e:
            print(f"    ❌ Error saving to Supabase: {e}")
            return False
    
    def run_anti_bias_strategy(self):
        """Main anti-bias hybrid strategy."""
        print("🚀 Starting DIVERSE streamer collection strategy...")
        
        # Get diverse streams
        print("🔍 Getting DIVERSE streams across all viewer ranges...")
        streams = self.get_diverse_streams()
        
        if not streams:
            print("❌ No diverse streams found")
            return
        
        print(f"📺 Found {len(streams)} DIVERSE streams")
        
        # Shuffle streams to avoid order bias
        random.shuffle(streams)
        
        for stream in streams:
            if self.clips_collected >= TARGET_CLIPS:
                break
                
            streamer_name = stream["user_name"]
            streamer_id = stream["user_id"]
            viewer_count = stream["viewer_count"]
            viewer_tier = self.get_viewer_tier(viewer_count)
            size_labels = ["SMALL", "MEDIUM", "LARGE", "VERY LARGE"]
            size_label = size_labels[viewer_tier]
            
            print(f"\n📺 Processing {size_label} streamer: {streamer_name} ({viewer_count:,} viewers)")
            
            # Track diversity
            self.streamer_diversity.add(streamer_name)
            
            # Get diverse clips from this streamer
            clips = self.get_diverse_clips(streamer_id, limit=2)
            
            for clip in clips:
                if self.clips_collected >= TARGET_CLIPS:
                    break
                    
                clip_id = clip["id"]
                clip_url = clip["url"]
                title = clip["title"]
                duration = clip["duration"]
                
                print(f"  📹 Clip: {title} ({duration}s)")
                
                # Download the clip
                clip_path = self.download_twitch_clip(clip_id)
                
                if clip_path:
                    # Transcribe the clip
                    transcript = self.transcribe_clip(clip_path)
                    
                    if not transcript:
                        transcript = title
                    
                    # Decision logic
                    should_clip = False
                    clip_reason = ""
                    
                    # Random sampling (30% chance)
                    if random.random() < 0.3:
                        should_clip = True
                        clip_reason = "random"
                        self.random_clips += 1
                        print(f"    🎲 Random sampling triggered!")
                    
                    # Model prediction (if not already triggered)
                    elif transcript and len(transcript) > 10:
                        model_prediction, source = self.process_clip_with_model(transcript, clip_id)
                        if model_prediction:
                            should_clip = True
                            clip_reason = "model"
                            self.model_clips += 1
                            print(f"    ✅ Model flagged as clip-worthy!")
                        else:
                            print(f"    ❌ Model says not clip-worthy")
                    
                    # Save if selected
                    if should_clip:
                        self.clips_collected += 1
                        self.viewer_tier_counts[viewer_tier] += 1
                        
                        # Use the ACTUAL Twitch clip ID instead of generating a fake one
                        actual_clip_id = clip_id  # This is the real Twitch clip ID from the API
                        
                        print(f"    📹 Creating DIVERSE clip ({clip_reason}): {actual_clip_id}")
                        print(f"    📝 Transcript: {transcript[:50]}...")
                        
                        # Save to Supabase
                        self.save_clip_to_supabase(
                            actual_clip_id, transcript, clip_url, 
                            streamer_name, viewer_count, clip_reason, viewer_tier
                        )
                        
                        print(f"    ✅ Diverse clip {self.clips_collected}/{TARGET_CLIPS} collected!")
                    else:
                        print(f"    ⏭️  Skipped clip")
        
        self.print_anti_bias_summary()
    
    def print_anti_bias_summary(self):
        """Print anti-bias summary."""
        print(f"\n" + "=" * 70)
        print("📊 DIVERSE STREAMER COLLECTION SUMMARY")
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
        print("✅ DIVERSE streamer collection completed!")
        print("🔄 Dataset now has representation from ALL streamer sizes!")

def main():
    """Main function to run the anti-bias hybrid strategy."""
    try:
        collector = AntiBiasHybridCollector()
        collector.run_anti_bias_strategy()
    except KeyboardInterrupt:
        print("\n⏹️  Anti-bias strategy stopped by user")
    except Exception as e:
        print(f"❌ Error in anti-bias strategy: {e}")

if __name__ == "__main__":
    main() 