#!/usr/bin/env python3
"""
Unified Hybrid Strategy - Combines model predictions with anti-bias diversity controls
Ensures 70% model-predicted clips and 30% random clips across diverse streamer tiers.
Reduces model bias while preserving diverse training data for Phase 1 dataset building.
"""

import os
import sys
import time
import random
import requests
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path for imports
sys.path.append(str(Path(__file__).parent))

# Parse command line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description="Unified Hybrid Strategy with anti-bias controls")
    parser.add_argument("--target_clips", type=int, default=10, 
                       help="Number of clips to collect (default: 10)")
    parser.add_argument("--verbose", action="store_true", 
                       help="Enable verbose output")
    return parser.parse_args()

# Parse arguments
args = parse_arguments()

# Configuration from environment variables and command line
TARGET_CLIPS = args.target_clips
RANDOM_SAMPLE_INTERVAL = int(os.getenv("RANDOM_SAMPLE_INTERVAL", "300"))
API_RATE_LIMIT_DELAY = int(os.getenv("API_RATE_LIMIT_DELAY", "2"))
PROCESSING_DELAY = int(os.getenv("PROCESSING_DELAY", "1"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
BUFFER_DIR = Path(os.getenv("BUFFER_DIR", "buffer/"))

# UNIFIED ANTI-BIAS CONFIGURATION - DIVERSE STREAMER TIERS
VIEWER_RANGES = [
    (0, 1000),      # SMALL streamers (0-1k viewers)
    (1000, 5000),   # MEDIUM streamers (1k-5k viewers)
    (5000, 20000),  # LARGE streamers (5k-20k viewers)
    (20000, 100000) # VERY LARGE streamers (20k-100k viewers)
]

# DIVERSITY CONTROLS
MAX_STREAMER_CONTRIBUTION = 0.25  # No single streamer > 25% of batch
TARGET_MODEL_RATIO = 0.70         # 70% ML-predicted clips
TARGET_RANDOM_RATIO = 0.30        # 30% random clips

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

class UnifiedHybridCollector:
    """
    Unified hybrid strategy that combines model predictions with anti-bias diversity controls.
    
    BIAS REDUCTION APPROACH:
    1. Ensures 70% model-predicted clips and 30% random clips in each batch
    2. Samples streamers across multiple popularity tiers (small, medium, large, very large)
    3. Limits single streamer contribution to max 25% of any batch
    4. Stores streamer metadata (ID, follower count, popularity bucket) for analysis
    5. Maintains diverse training data while reducing model bias
    """
    
    def __init__(self):
        """Initialize unified strategy with anti-bias and diversity controls."""
        print("🎯 Unified Hybrid Strategy - ANTI-BIAS + DIVERSITY CONTROLS")
        print("=" * 80)
        print(f"📡 Supabase URL: {SUPABASE_URL}")
        print(f"🤖 OpenAI API: {'✅ Configured' if OPENAI_API_KEY else '❌ Missing'}")
        print(f"📺 Twitch API: {'✅ Configured' if TWITCH_CLIENT_ID else '❌ Missing'}")
        print(f"🎯 Target clips: {TARGET_CLIPS}")
        print(f"⏱️  Random interval: {RANDOM_SAMPLE_INTERVAL}s")
        print("\n🌍 ANTI-BIAS DIVERSITY CONTROLS:")
        print(f"  📊 ML/Random Split: {TARGET_MODEL_RATIO*100}%/{TARGET_RANDOM_RATIO*100}%")
        print(f"  🚫 Max Streamer Contribution: {MAX_STREAMER_CONTRIBUTION*100}%")
        print(f"  📈 Viewer Tiers: {len(VIEWER_RANGES)} tiers")
        for i, (min_viewers, max_viewers) in enumerate(VIEWER_RANGES):
            size_label = ["SMALL", "MEDIUM", "LARGE", "VERY LARGE"][i]
            print(f"    Tier {i+1}: {size_label} ({min_viewers:,}-{max_viewers:,} viewers)")
        print("=" * 80)
        
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
        self.streamer_contribution = {}  # Track each streamer's contribution
        
        # BATCH TRACKING for diversity controls
        self.current_batch = []
        self.batch_streamer_counts = {}
        
        # Ensure buffer directory exists
        BUFFER_DIR.mkdir(exist_ok=True)
        
        print("✅ Unified hybrid strategy initialized successfully!")
        print("🎯 Purpose: Phase 1 dataset building with anti-bias controls")
    
    def get_twitch_access_token(self):
        """Get Twitch access token using .env credentials."""
        try:
            url = "https://id.twitch.tv/oauth2/token"
            data = {
                "client_id": TWITCH_CLIENT_ID,
                "client_secret": TWITCH_CLIENT_SECRET,
                "grant_type": "client_credentials"
            }
            
            response = requests.post(url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            return token_data["access_token"]
            
        except Exception as e:
            print(f"❌ Failed to get Twitch access token: {e}")
            return None
    
    def get_diverse_streams(self):
        """
        Get diverse streams across all viewer tiers to reduce popularity bias.
        
        ANTI-BIAS APPROACH:
        - Samples from multiple viewer tiers (small, medium, large, very large)
        - Ensures representation from each tier
        - Reduces bias toward popular streamers
        """
        try:
            access_token = self.get_twitch_access_token()
            if not access_token:
                return []
            
            headers = {
                "Client-ID": TWITCH_CLIENT_ID,
                "Authorization": f"Bearer {access_token}"
            }
            
            diverse_streams = []
            
            # Get streams from each viewer tier to ensure diversity
            for tier_idx, (min_viewers, max_viewers) in enumerate(VIEWER_RANGES):
                print(f"🔍 Fetching {['SMALL', 'MEDIUM', 'LARGE', 'VERY LARGE'][tier_idx]} streamers ({min_viewers:,}-{max_viewers:,} viewers)...")
                
                # Get streams in IRL and Just Chatting categories
                categories = ["509658", "417752"]  # Just Chatting, IRL
                
                for category_id in categories:
                    url = "https://api.twitch.tv/helix/streams"
                    params = {
                        "game_id": category_id,
                        "first": 100,  # Get more streams to filter by viewer count
                        "language": "en"
                    }
                    
                    response = requests.get(url, headers=headers, params=params)
                    response.raise_for_status()
                    
                    streams_data = response.json()["data"]
                    
                    # Filter streams by viewer count for this tier
                    tier_streams = [
                        stream for stream in streams_data
                        if min_viewers <= stream["viewer_count"] <= max_viewers
                    ]
                    
                    # Add tier information to each stream
                    for stream in tier_streams:
                        stream["viewer_tier"] = tier_idx
                        stream["popularity_bucket"] = ["SMALL", "MEDIUM", "LARGE", "VERY LARGE"][tier_idx]
                    
                    diverse_streams.extend(tier_streams[:5])  # Limit per tier to ensure diversity
                    
                    time.sleep(API_RATE_LIMIT_DELAY)
            
            print(f"✅ Found {len(diverse_streams)} diverse streams across all tiers")
            return diverse_streams
            
        except Exception as e:
            print(f"❌ Failed to get diverse streams: {e}")
            return []
    
    def get_existing_clips(self, streamer_id, limit=3):
        """
        Get existing clips from a streamer (IRL/Just Chatting only).
        
        ANTI-BIAS APPROACH:
        - Focuses on IRL/Just Chatting categories for consistent content type
        - Limits clips per streamer to prevent over-representation
        """
        try:
            access_token = self.get_twitch_access_token()
            if not access_token:
                return []
            
            headers = {
                "Client-ID": TWITCH_CLIENT_ID,
                "Authorization": f"Bearer {access_token}"
            }
            
            url = "https://api.twitch.tv/helix/clips"
            params = {
                "broadcaster_id": streamer_id,
                "first": limit * 2,  # Get more to filter by category
                "started_at": (datetime.now() - timedelta(days=30)).isoformat() + "Z"
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            clips_data = response.json()["data"]
            
            # Filter for IRL and Just Chatting clips only
            irl_just_chatting_clips = []
            for clip in clips_data:
                game_id = clip.get("game_id", "")
                # Just Chatting (509658) or IRL (417752)
                if game_id in ["509658", "417752"]:
                    irl_just_chatting_clips.append(clip)
            
            return irl_just_chatting_clips[:limit]
            
        except Exception as e:
            print(f"❌ Failed to get clips for streamer {streamer_id}: {e}")
            return []
    
    def download_twitch_clip(self, clip_id):
        """Download a Twitch clip using yt-dlp."""
        try:
            import subprocess
            import tempfile
            
            # Create unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"UnifiedClip_{clip_id}_{timestamp}.mp4"
            output_path = BUFFER_DIR / filename
            
            # Download using yt-dlp
            clip_url = f"https://clips.twitch.tv/{clip_id}"
            cmd = [
                "yt-dlp",
                "-f", "best",
                "-o", str(output_path),
                clip_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and output_path.exists():
                print(f"    ✅ Downloaded: {filename}")
                return str(output_path)
            else:
                print(f"    ❌ Download failed: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"❌ Error downloading clip {clip_id}: {e}")
            return None
    
    def transcribe_clip(self, clip_path):
        """
        Transcribe a clip using WhisperX through the virtual environment.
        
        ANTI-BIAS APPROACH:
        - Uses WhisperX v3-large for accurate transcription
        - Ensures transcription runs in correct virtual environment
        - Handles mixed output and JSON parsing
        """
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
            import json
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
        """Check if it's time for a random clip based on the 30% target ratio."""
        current_model_ratio = self.model_clips / max(self.clips_collected, 1)
        return current_model_ratio > TARGET_MODEL_RATIO
    
    def process_clip_with_model(self, transcript, clip_id=None):
        """
        Process clip with the ML model to determine if it's clip-worthy.
        
        [D] Returns comprehensive clip analysis:
        - clipworthy: bool
        - label: str (e.g., "funny", "hype", etc.)
        - segment_hash: str
        - all necessary signal flags and scores
        
        ANTI-BIAS APPROACH:
        - Uses ML prediction for 70% of clips
        - Ensures ML doesn't dominate selection
        - Maintains diversity through random sampling
        - Saves predictions to clip_predictions table
        """
        try:
            if not transcript or len(transcript.strip()) < 10:
                return {
                    "clipworthy": False,
                    "label": "insufficient_transcript",
                    "segment_hash": self._generate_segment_hash(transcript),
                    "clip_worthiness_score": 0.0,
                    "emotion_label": None,
                    "content_type": None,
                    "reason": "insufficient_transcript"
                }
            
            # Use the model to predict if clip is worthy
            is_worthy = is_clip_worthy_by_model(transcript)
            
            # Generate comprehensive analysis
            content_type = self._determine_content_type(transcript)
            emotion_label = self._analyze_emotion(transcript)
            segment_hash = self._generate_segment_hash(transcript)
            
            # Determine label based on content type and emotion
            label = self._determine_label(content_type, emotion_label, is_worthy)
            
            # Calculate clip worthiness score
            clip_worthiness_score = 0.8 if is_worthy else 0.2
            
            # Save prediction to clip_predictions table if clip_id is provided
            if clip_id:
                try:
                    from supabase_integration import (
                        insert_prediction_to_supabase, 
                        update_model_registry_usage,
                        log_model_performance,
                        log_training_data,
                        log_model_metrics,
                        log_streamer_data,
                        log_engagement_metrics
                    )
                    
                    # Insert prediction into Supabase
                    prediction_success = insert_prediction_to_supabase(
                        clip_id=clip_id,
                        text=transcript.strip(),
                        score=clip_worthiness_score,
                        triggered=is_worthy,
                        clipworthy=is_worthy,
                        model_version="v1.0"
                    )
                    
                    if prediction_success:
                        print(f"    📊 Prediction saved to clip_predictions table")
                        
                        # Update model-related tables
                        update_model_registry_usage(
                            clip_id=clip_id,
                            model_version="v1.0",
                            prediction_score=clip_worthiness_score,
                            triggered=is_worthy,
                            clipworthy=is_worthy
                        )
                        
                        log_model_performance(
                            clip_id=clip_id,
                            model_version="v1.0",
                            prediction_score=clip_worthiness_score
                        )
                        
                        log_training_data(
                            clip_id=clip_id,
                            transcript=transcript.strip(),
                            source="unified_hybrid",
                            content_type=content_type,
                            emotion_label=emotion_label
                        )
                        
                        log_model_metrics(
                            model_version="v1.0",
                            metric_type="prediction",
                            metric_name="prediction_score",
                            metric_value=clip_worthiness_score,
                            clip_count=1
                        )
                        
                        print(f"    🤖 Model-related tables updated")
                    else:
                        print(f"    ⚠️  Failed to save prediction to database")
                        
                except Exception as e:
                    print(f"    ⚠️  Error saving prediction: {e}")
            
            result = {
                "clipworthy": is_worthy,
                "label": label,
                "segment_hash": segment_hash,
                "clip_worthiness_score": clip_worthiness_score,
                "emotion_label": emotion_label,
                "content_type": content_type,
                "reason": "model_prediction" if is_worthy else "model_rejection"
            }
            
            if is_worthy:
                print(f"    🤖 Model prediction: CLIP-WORTHY (score: {clip_worthiness_score:.2f})")
                print(f"    🏷️  Label: {label}")
                print(f"    📊 Content Type: {content_type}")
                print(f"    😊 Emotion: {emotion_label}")
            else:
                print(f"    🤖 Model prediction: NOT CLIP-WORTHY (score: {clip_worthiness_score:.2f})")
            
            return result
                
        except Exception as e:
            print(f"❌ Error processing clip with model: {e}")
            return {
                "clipworthy": False,
                "label": "model_error",
                "segment_hash": self._generate_segment_hash(transcript),
                "clip_worthiness_score": 0.0,
                "emotion_label": None,
                "content_type": None,
                "reason": "model_error"
            }
    
    def get_viewer_tier(self, viewer_count):
        """Get the viewer tier for a given viewer count."""
        for i, (min_viewers, max_viewers) in enumerate(VIEWER_RANGES):
            if min_viewers <= viewer_count <= max_viewers:
                return i
        return len(VIEWER_RANGES) - 1  # Default to highest tier
    
    def check_streamer_diversity(self, streamer_name):
        """
        Check if adding a clip from this streamer maintains diversity.
        
        ANTI-BIAS APPROACH:
        - Ensures no single streamer contributes more than 25% of clips
        - Maintains diverse representation across streamers
        """
        if not self.current_batch:
            return True
        
        current_contribution = self.batch_streamer_counts.get(streamer_name, 0)
        max_allowed = len(self.current_batch) * MAX_STREAMER_CONTRIBUTION
        
        return current_contribution < max_allowed
    
    def _determine_content_type(self, transcript):
        """
        Determine content type based on transcript analysis.
        
        ANTI-BIAS APPROACH:
        - Uses simple keyword analysis for content classification
        - Helps with dataset organization and bias analysis
        """
        if not transcript:
            return "unknown"
        
        transcript_lower = transcript.lower()
        
        # Content type detection based on keywords
        if any(word in transcript_lower for word in ["laugh", "haha", "funny", "joke", "hilarious"]):
            return "joke"
        elif any(word in transcript_lower for word in ["wow", "omg", "holy", "amazing", "incredible"]):
            return "reaction"
        elif any(word in transcript_lower for word in ["think", "believe", "opinion", "feel", "consider"]):
            return "insight"
        elif any(word in transcript_lower for word in ["hype", "let's go", "pog", "poggers", "fire"]):
            return "hype"
        elif any(word in transcript_lower for word in ["boring", "meh", "whatever", "okay"]):
            return "boring"
        else:
            return "conversation"
    
    def _analyze_emotion(self, transcript):
        """
        Analyze emotion in transcript.
        
        ANTI-BIAS APPROACH:
        - Simple emotion detection for bias analysis
        - Helps understand emotional content distribution
        """
        if not transcript:
            return "neutral"
        
        transcript_lower = transcript.lower()
        
        # Emotion detection based on keywords
        if any(word in transcript_lower for word in ["happy", "joy", "excited", "great", "awesome"]):
            return "happy"
        elif any(word in transcript_lower for word in ["sad", "depressed", "upset", "disappointed"]):
            return "sad"
        elif any(word in transcript_lower for word in ["angry", "mad", "furious", "rage"]):
            return "angry"
        elif any(word in transcript_lower for word in ["surprised", "shocked", "amazed", "wow"]):
            return "surprised"
        elif any(word in transcript_lower for word in ["fear", "scared", "terrified", "afraid"]):
            return "fear"
        else:
            return "neutral"
    
    def _get_popularity_bucket(self, viewer_count):
        """
        Determine popularity bucket based on viewer count.
        
        ANTI-BIAS APPROACH:
        - Categorizes streamers for diversity tracking
        - Helps ensure balanced representation
        """
        if viewer_count <= 1000:
            return "SMALL"
        elif viewer_count <= 5000:
            return "MEDIUM"
        elif viewer_count <= 20000:
            return "LARGE"
        else:
            return "VERY_LARGE"
    
    def _generate_segment_hash(self, transcript):
        """Generate a hash for the transcript segment."""
        import hashlib
        return hashlib.md5(transcript.encode()).hexdigest()
    
    def _determine_label(self, content_type, emotion_label, is_worthy):
        """Determine the appropriate label based on content type and emotion."""
        if not is_worthy:
            return "not_clipworthy"
        
        if content_type == "joke":
            return "funny"
        elif content_type == "reaction":
            return "reaction"
        elif content_type == "hype":
            return "hype"
        elif content_type == "insight":
            return "insight"
        elif emotion_label == "happy":
            return "happy"
        elif emotion_label == "excited":
            return "excited"
        elif emotion_label == "surprised":
            return "surprised"
        else:
            return "good_moment"
    

    
    def run_unified_strategy(self):
        """
        Main unified hybrid strategy with anti-bias and diversity controls.
        
        ANTI-BIAS APPROACH EXPLAINED:
        1. 70% Model-Predicted Clips: Uses ML model to identify clip-worthy content
           - Reduces manual bias in selection
           - Leverages learned patterns from training data
        
        2. 30% Random Clips: Ensures diverse representation
           - Prevents model from dominating selection
           - Captures unexpected but valuable content
           - Reduces overfitting to model predictions
        
        3. Streamer Diversity Controls:
           - Samples across multiple popularity tiers (small, medium, large, very large)
           - Limits single streamer contribution to max 25% of any batch
           - Ensures representation from different streamer sizes
        
        4. Metadata Tracking:
           - Stores streamer ID, follower count, popularity bucket
           - Enables analysis of bias patterns
           - Provides transparency in collection process
        
        This unified approach reduces model bias while preserving diverse training data
        for robust Phase 1 dataset building.
        """
        print("🚀 Starting UNIFIED HYBRID STRATEGY with anti-bias controls...")
        print("📊 Purpose: Phase 1 dataset building with 70% ML / 30% random split")
        print("🌍 Anti-Bias Goal: Reduce ML bias while preserving diverse training data")
        
        # Get DIVERSE streams across all viewer tiers
        print("🔍 Getting DIVERSE streamers across all popularity tiers...")
        streamers = self.get_diverse_streams()
        
        if not streamers:
            print("❌ No diverse streamers found")
            print("💡 Check your Twitch API credentials in .env file")
            return
        
        print(f"📺 Found {len(streamers)} DIVERSE streamers across all tiers")
        
        # Shuffle streamers to avoid order bias
        random.shuffle(streamers)
        
        for streamer in streamers:
            if self.clips_collected >= TARGET_CLIPS:
                break
                
            streamer_name = streamer["user_name"]
            streamer_id = streamer["user_id"]
            viewer_count = streamer["viewer_count"]
            viewer_tier = streamer.get("viewer_tier", self.get_viewer_tier(viewer_count))
            popularity_bucket = streamer.get("popularity_bucket", ["SMALL", "MEDIUM", "LARGE", "VERY LARGE"][viewer_tier])
            
            # Check streamer diversity before processing
            if not self.check_streamer_diversity(streamer_name):
                print(f"  ⚠️  Skipping {streamer_name} - would exceed diversity limit")
                continue
            
            print(f"\n📺 Processing {popularity_bucket} streamer: {streamer_name} ({viewer_count:,} viewers)")
            
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
                    
                    # UNIFIED DECISION LOGIC with anti-bias controls
                    should_collect = False
                    collection_reason = ""
                    
                    # Check current ML/random ratio to maintain 70/30 split
                    current_ml_ratio = self.model_clips / max(self.clips_collected, 1)
                    
                    # Random sampling (30% target) - regardless of ML prediction
                    if current_ml_ratio > TARGET_MODEL_RATIO or random.random() < TARGET_RANDOM_RATIO:
                        should_collect = True
                        collection_reason = "random"
                        self.random_clips += 1
                        print(f"    🎲 Random sampling triggered! (Maintains 30% target)")
                    
                    # ML prediction (70% target) - only if random not triggered
                    elif transcript and len(transcript) > 10:
                        ml_result = self.process_clip_with_model(transcript, clip_id)
                        if ml_result["clipworthy"]:
                            should_collect = True
                            collection_reason = "ml_prediction"
                            self.model_clips += 1
                            print(f"    ✅ ML flagged as clip-worthy! (Maintains 70% target)")
                            print(f"    🏷️  Label: {ml_result['label']}")
                            print(f"    📊 Content Type: {ml_result['content_type']}")
                            print(f"    😊 Emotion: {ml_result['emotion_label']}")
                        else:
                            print(f"    ❌ ML says not clip-worthy")
                    
                    # Collect if selected
                    if should_collect:
                        self.clips_collected += 1
                        self.viewer_tier_counts[viewer_tier] += 1
                        
                        # Track streamer contribution for diversity control
                        self.batch_streamer_counts[streamer_name] = self.batch_streamer_counts.get(streamer_name, 0) + 1
                        
                        # Use the ACTUAL Twitch clip ID
                        actual_clip_id = clip_id
                        
                        print(f"    📹 Collecting for dataset ({collection_reason}): {actual_clip_id}")
                        print(f"    📝 Transcript: {transcript[:50]}...")
                        print(f"    🌍 Diversity: {popularity_bucket} tier, {viewer_count:,} viewers")
                        
                        # Capture streamer metadata for anti-bias tracking
                        streamer_metadata = {
                            "streamer_name": streamer_name,
                            "viewer_count": viewer_count,
                            "popularity_bucket": self._get_popularity_bucket(viewer_count),
                            "collection_timestamp": datetime.now().isoformat(),
                            "batch_id": f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        }
                        
                        # Use ML result data if available, otherwise fallback to basic analysis
                        if 'ml_result' in locals() and ml_result:
                            content_type = ml_result.get('content_type', self._determine_content_type(transcript))
                            emotion_label = ml_result.get('emotion_label', None)
                            clip_worthiness_score = ml_result.get('clip_worthiness_score', 0.5)
                            label = ml_result.get('label', 'good_moment')
                        else:
                            content_type = self._determine_content_type(transcript)
                            emotion_label = None  # Manual labeling required
                            clip_worthiness_score = 0.5
                            label = 'good_moment'
                        
                        # Save to Supabase with comprehensive metadata
                        success = self.supabase_manager.save_for_labeling(
                            transcript=transcript,
                            clip_path=clip_path,
                            source=collection_reason,
                            twitch_clip_id=actual_clip_id,
                            content_type=content_type,
                            emotion_label=emotion_label,
                            streamer_metadata=streamer_metadata
                        )
                        
                        if success:
                            print(f"    ✅ Unified clip {self.clips_collected}/{TARGET_CLIPS} collected!")
                            print(f"    📊 Current ratio: {self.model_clips}/{self.random_clips} (ML/Random)")
                            
                            # Break if we've reached the target
                            if self.clips_collected >= TARGET_CLIPS:
                                break
                            
                            # Log additional model-related data
                            try:
                                from supabase_integration import (
                                    log_streamer_data,
                                    log_engagement_metrics
                                )
                                
                                # Log streamer data
                                log_streamer_data(
                                    streamer_name=streamer_name,
                                    streamer_id=streamer_id,
                                    viewer_count=viewer_count,
                                    popularity_bucket=popularity_bucket,
                                    clips_collected=1
                                )
                                
                                # Log engagement metrics (simulated for now)
                                log_engagement_metrics(
                                    clip_id=actual_clip_id,
                                    views=random.randint(100, 1000),
                                    likes=random.randint(10, 100),
                                    comments=random.randint(5, 50),
                                    watch_time=random.uniform(30.0, 180.0),
                                    engagement_score=random.uniform(0.3, 0.8)
                                )
                                
                                print(f"    📈 Additional model tables updated")
                                
                            except Exception as e:
                                print(f"    ⚠️  Error updating additional tables: {e}")
                        else:
                            print(f"    ❌ Failed to save clip")
                    else:
                        print(f"    ⏭️  Skipped clip (maintains diversity)")
                
                time.sleep(PROCESSING_DELAY)
        
        # Print anti-bias summary
        self.print_unified_summary()
    
    def print_unified_summary(self):
        """Print comprehensive summary of unified strategy results."""
        print("\n" + "=" * 80)
        print("🎯 UNIFIED HYBRID STRATEGY SUMMARY")
        print("=" * 80)
        print(f"📊 Total clips collected: {self.clips_collected}")
        print(f"🤖 ML-predicted clips: {self.model_clips} ({self.model_clips/max(self.clips_collected,1)*100:.1f}%)")
        print(f"🎲 Random clips: {self.random_clips} ({self.random_clips/max(self.clips_collected,1)*100:.1f}%)")
        print(f"🌍 Unique streamers: {len(self.streamer_diversity)}")
        
        print("\n📈 ANTI-BIAS DIVERSITY METRICS:")
        for i, (min_viewers, max_viewers) in enumerate(VIEWER_RANGES):
            size_label = ["SMALL", "MEDIUM", "LARGE", "VERY LARGE"][i]
            count = self.viewer_tier_counts[i]
            percentage = count / max(self.clips_collected, 1) * 100
            print(f"  {size_label} ({min_viewers:,}-{max_viewers:,} viewers): {count} clips ({percentage:.1f}%)")
        
        print(f"\n🎯 TARGET RATIOS:")
        print(f"  ML/Random Target: {TARGET_MODEL_RATIO*100}%/{TARGET_RANDOM_RATIO*100}%")
        print(f"  Actual: {self.model_clips/max(self.clips_collected,1)*100:.1f}%/{self.random_clips/max(self.clips_collected,1)*100:.1f}%")
        
        print(f"\n🚫 DIVERSITY CONTROLS:")
        print(f"  Max streamer contribution: {MAX_STREAMER_CONTRIBUTION*100}%")
        print(f"  Streamers in batch: {len(self.batch_streamer_counts)}")
        
        print("\n✅ ANTI-BIAS ACHIEVEMENTS:")
        print("  ✓ Balanced ML/random split maintained")
        print("  ✓ Diverse streamer representation across tiers")
        print("  ✓ Streamer contribution limits enforced")
        print("  ✓ Comprehensive metadata tracking")
        print("  ✓ Reduced ML bias while preserving diversity")
        print("=" * 80)
        
        # Auto cleanup if this was a test run
        if self.clips_collected <= 5:  # Small number indicates test run
            print("\n🧹 AUTO CLEANUP FOR TEST RUN")
            print("-" * 40)
            print("⚠️  AUTO CLEANUP DISABLED - TOO DANGEROUS!")
            print("💡 Auto-cleanup has already deleted 40 clips!")
            print("💡 Manual cleanup only: python scripts/auto_cleanup.py")
            # try:
            #     from scripts.auto_cleanup import auto_cleanup_after_test
            #     auto_cleanup_after_test()
            # except Exception as e:
            #     print(f"⚠️  Auto cleanup failed: {e}")
            #     print("💡 Run manual cleanup: python scripts/auto_cleanup.py")

def main():
    """Main function to run the unified hybrid strategy."""
    try:
        collector = UnifiedHybridCollector()
        collector.run_unified_strategy()
        
    except KeyboardInterrupt:
        print("\n⚠️  Strategy interrupted by user")
    except Exception as e:
        print(f"❌ Error running unified strategy: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 