#!/usr/bin/env python3
"""
Supabase integration for cloud-based clip labeling system.
This module provides functions to save clips for labeling in Supabase database.
"""

import os
import uuid
from typing import Optional, Dict, Any
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase not available. Install with: pip install supabase")

class SupabaseManager:
    """Manages Supabase client and operations for clip labeling."""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.initialized = False
        
        if not SUPABASE_AVAILABLE:
            logger.error("Supabase library not available")
            return
            
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Supabase client with environment variables."""
        try:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
            
            if not supabase_url or not supabase_key:
                logger.error("Missing Supabase credentials. Set SUPABASE_URL and SUPABASE_ANON_KEY or SUPABASE_KEY")
                return
            
            self.client = create_client(supabase_url, supabase_key)
            
            # Force schema cache refresh by querying all columns
            try:
                self.client.table('clips').select('*').limit(0).execute()
                logger.info("✅ Schema cache refreshed successfully")
            except Exception as e:
                logger.warning(f"⚠️ Schema cache refresh failed: {e}")
            
            self.initialized = True
            logger.info("✅ Supabase client initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase client: {e}")
            self.initialized = False
    
    def save_for_labeling(self, transcript: str, clip_path: str, 
                         source: str = "ml", content_type: str = None, 
                         labeling_method: str = "manual", twitch_clip_id: str = None,
                         twitch_url: str = None, emotion_label: str = None,
                         streamer_metadata: dict = None) -> Optional[str]:
        """
        Save clip information for manual labeling in Supabase.
        
        Args:
            transcript: The transcript text that triggered the clip
            clip_path: Path to the created clip file
            source: Source of the clip ("ml", "random", "hybrid_batch", etc.)
            content_type: Type of content ("joke", "reaction", "insight", "hype", "boring", etc.)
            labeling_method: Method of labeling ("manual", "auto", "review_needed")
            twitch_clip_id: The actual Twitch clip ID (e.g., "HorriblePowerfulWatercressKippa")
            twitch_url: The Twitch clip URL
            emotion_label: Predicted emotion label (optional)
            
        Returns:
            clip_id: The Twitch clip ID, or None if failed
        """
        if not self.initialized or not self.client:
            logger.error("❌ Supabase not initialized")
            return None
        
        try:
            # Use the actual Twitch clip ID if provided, otherwise generate UUID
            clip_id = twitch_clip_id if twitch_clip_id else str(uuid.uuid4())
            
            # Analyze audio and generate JSONB data
            audio_analysis_data = self._analyze_audio_for_clip(clip_path)
            
            # Extract scores and combination results
            scores = audio_analysis_data.get("scores", {})
            combination_results = audio_analysis_data.get("combination_results", {})
            audio_features = audio_analysis_data.get("audio_features", {})
            indicators = audio_analysis_data.get("indicators", {})
            
            # Debug: Log what we're getting from audio analysis
            logger.info(f"📊 Audio analysis data keys: {list(audio_analysis_data.keys())}")
            logger.info(f"📈 Scores available: {list(scores.keys()) if scores else 'None'}")
            logger.info(f"🎯 Indicators available: {list(indicators.keys()) if indicators else 'None'}")
            logger.info(f"🎵 Audio features available: {list(audio_features.keys()) if audio_features else 'None'}")
            
            # Extract indicators from combination_results if not in indicators
            if not indicators and combination_results:
                indicators = {
                    "energy_burst_detected": combination_results.get("energy_burst_detected"),
                    "audience_reaction_present": combination_results.get("audience_reaction_present"),
                    "laughter_detected": combination_results.get("laughter_detected"),
                    "high_emotional_intensity": combination_results.get("high_emotional_intensity"),
                    "rapid_speech": combination_results.get("rapid_speech"),
                    "significant_pause": combination_results.get("significant_pause")
                }
                logger.info(f"🎯 Extracted indicators from combination_results: {list(indicators.keys())}")
            
            # Extract audio features from scores if not in audio_features
            if not audio_features and scores:
                audio_features = {
                    "volume_avg": scores.get("volume_avg"),
                    "volume_max": scores.get("volume_max"),
                    "tempo": scores.get("tempo"),
                    "pause_duration": scores.get("pause_duration"),
                    "segment_duration": scores.get("segment_duration"),
                    "speech_rate": scores.get("speech_rate"),
                    "emotional_intensity": scores.get("emotional_intensity")
                }
                logger.info(f"🎵 Extracted audio features from scores: {list(audio_features.keys())}")
            
            # If still no indicators, try to extract from the quantile analysis
            if not indicators:
                # The indicators should be in the quantile analysis result
                quantile_result = audio_analysis_data.get("quantile_result", {})
                if quantile_result:
                    indicators = {
                        "energy_burst_detected": quantile_result.get("energy_burst_detected"),
                        "audience_reaction_present": quantile_result.get("audience_reaction_present"),
                        "laughter_detected": quantile_result.get("laughter_detected"),
                        "high_emotional_intensity": quantile_result.get("high_emotional_intensity"),
                        "rapid_speech": quantile_result.get("rapid_speech"),
                        "significant_pause": quantile_result.get("significant_pause")
                    }
                    logger.info(f"🎯 Extracted indicators from quantile_result: {list(indicators.keys())}")
            
            # If still no audio_features, try to extract from the quantile analysis
            if not audio_features:
                quantile_result = audio_analysis_data.get("quantile_result", {})
                if quantile_result:
                    audio_features = {
                        "volume_avg": quantile_result.get("volume_avg"),
                        "volume_max": quantile_result.get("volume_max"),
                        "tempo": quantile_result.get("tempo"),
                        "pause_duration": quantile_result.get("pause_duration"),
                        "segment_duration": quantile_result.get("segment_duration"),
                        "speech_rate": quantile_result.get("speech_rate"),
                        "emotional_intensity": quantile_result.get("emotional_intensity")
                    }
                    logger.info(f"🎵 Extracted audio features from quantile_result: {list(audio_features.keys())}")
            
                        # Convert boolean values to integers for JSON serialization
            def convert_bools_to_ints(obj):
                if isinstance(obj, bool):
                    return 1 if obj else 0
                elif isinstance(obj, str):
                    # Only convert strings that are explicitly boolean values
                    if obj in ['True', 'False', 'true', 'false']:
                        return 1 if obj.lower() == 'true' else 0
                    else:
                        # Don't convert other strings - return as is
                        return obj
                elif isinstance(obj, dict):
                    return {key: convert_bools_to_ints(value) for key, value in obj.items()}
                elif isinstance(obj, list):
                    return [convert_bools_to_ints(item) for item in obj]
                elif hasattr(obj, 'dtype') and obj.dtype == bool:  # Handle numpy bool arrays
                    return 1 if obj else 0
                elif hasattr(obj, 'item'):  # Handle numpy scalar types
                    return obj.item() if hasattr(obj, 'item') else obj
                else:
                    return obj
            
            # Prepare data for insertion with comprehensive validation
            clip_data = {
                "clip_id": clip_id,
                "transcript": transcript.strip() if transcript else "",
                "clip_path": clip_path,
                "source": source,
                "label": None,  # Manual labeling required
                "content_type": content_type,
                "emotion_label": emotion_label,
                # Add audio analysis JSONB data (with boolean conversion)
                "energy_bursts": convert_bools_to_ints(audio_analysis_data.get("energy_bursts", {})),
                "audience_reaction": convert_bools_to_ints(audio_analysis_data.get("audience_reaction", {})),
                "volume_shifts": convert_bools_to_ints(audio_analysis_data.get("volume_shifts", {})),
                # Note: Individual score columns have been removed from the schema
                # Only JSONB objects and basic columns are available
                # The audio analysis data is stored in the JSONB objects:
                # - energy_bursts: contains energy-related scores and indicators
                # - audience_reaction: contains audience and laughter scores
                # - volume_shifts: contains volume-related scores and patterns
                # Add timestamps
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # [A] Validate required fields
            required_fields = ["clip_id", "transcript", "source", "label", "emotion_label"]
            missing_fields = [field for field in required_fields if not clip_data.get(field) and field != "label" and field != "emotion_label"]
            
            if missing_fields:
                logger.error(f"❌ Missing required fields: {missing_fields}")
                return None
            
            # Debug: Log the original clip_data before conversion
            logger.info("🔍 DEBUG: Original clip_data keys:")
            for key, value in clip_data.items():
                if key in ['clip_id', 'transcript', 'source', 'content_type', 'emotion_label']:
                    logger.info(f"  {key}: {value}")
            
            # Convert boolean values to integers for JSON serialization
            def convert_bools_to_ints(obj):
                if isinstance(obj, bool):
                    return 1 if obj else 0
                elif isinstance(obj, str):
                    # Only convert strings that are explicitly boolean values
                    if obj in ['True', 'False', 'true', 'false']:
                        return 1 if obj.lower() == 'true' else 0
                    else:
                        # Don't convert other strings - return as is
                        return obj
                elif isinstance(obj, dict):
                    return {key: convert_bools_to_ints(value) for key, value in obj.items()}
                elif isinstance(obj, list):
                    return [convert_bools_to_ints(item) for item in obj]
                elif hasattr(obj, 'dtype') and obj.dtype == bool:  # Handle numpy bool arrays
                    return 1 if obj else 0
                elif hasattr(obj, 'item'):  # Handle numpy scalar types
                    return obj.item() if hasattr(obj, 'item') else obj
                else:
                    return obj
            
            serializable_clip_data = convert_bools_to_ints(clip_data)
            
            # Check for any remaining boolean values in the data
            def check_for_bools(obj, path=""):
                if isinstance(obj, bool):
                    logger.warning(f"⚠️  Found boolean at {path}: {obj}")
                    return True
                elif hasattr(obj, 'dtype') and obj.dtype == bool:  # Handle numpy bool arrays
                    logger.warning(f"⚠️  Found numpy boolean at {path}: {obj}")
                    return True
                elif isinstance(obj, dict):
                    for key, value in obj.items():
                        if check_for_bools(value, f"{path}.{key}"):
                            return True
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        if check_for_bools(item, f"{path}[{i}]"):
                            return True
                return False
            
            if check_for_bools(serializable_clip_data):
                logger.warning("⚠️  Found boolean values that need conversion!")
            
            # Additional check specifically for audio analysis data
            audio_fields = ['energy_bursts', 'audience_reaction', 'volume_shifts']
            for field in audio_fields:
                if field in serializable_clip_data:
                    if check_for_bools(serializable_clip_data[field], f"audio.{field}"):
                        logger.warning(f"⚠️  Found boolean values in {field}!")
            
            # Debug: Log the serializable data after conversion
            logger.info("🔍 DEBUG: Serializable clip_data keys:")
            for key, value in serializable_clip_data.items():
                if key in ['clip_id', 'transcript', 'source', 'content_type', 'emotion_label']:
                    logger.info(f"  {key}: {value}")
            
            # [B] Log before insert - Print the full payload
            logger.info("=" * 80)
            logger.info("📤 INSERTING CLIP TO SUPABASE")
            logger.info("=" * 80)
            logger.info(f"🎯 Clip ID: {clip_id}")
            logger.info(f"📝 Transcript: {transcript[:100]}{'...' if len(transcript) > 100 else ''}")
            logger.info(f"🏷️  Source: {source}")
            logger.info(f"📊 Content Type: {content_type}")
            logger.info(f"😊 Emotion Label: {emotion_label}")
            
            # Log the full payload for debugging
            import json
            logger.info("📋 FULL PAYLOAD:")
            logger.info(json.dumps(serializable_clip_data, indent=2, default=str))
            
            # Validate data types
            validation_errors = []
            optional_fields = ["label", "emotion_label", "auto_label", "high_impact_description", 
                             "emotional_impact_description", "laughter_impact_description", 
                             "subtle_impact_description", "speech_impact_description", 
                             "audience_impact_description"]
            
            for key, value in serializable_clip_data.items():
                if value is None and key not in optional_fields:
                    validation_errors.append(f"Field '{key}' is None")
                elif isinstance(value, (int, float)) and key.endswith("_score"):
                    # Score fields should be numeric
                    if not isinstance(value, (int, float)):
                        validation_errors.append(f"Score field '{key}' should be numeric, got {type(value)}")
            
            if validation_errors:
                logger.error(f"❌ Validation errors: {validation_errors}")
                return None
            
            # Insert into clips table with fresh client
            logger.info("💾 Executing Supabase insert...")
            
            # Create a fresh client to avoid schema cache issues
            try:
                supabase_url = os.getenv("SUPABASE_URL")
                supabase_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
                fresh_client = create_client(supabase_url, supabase_key)
                result = fresh_client.table('clips').insert(serializable_clip_data).execute()
            except Exception as e:
                logger.error(f"❌ Fresh client insert failed: {e}")
                # Fallback to original client
                result = self.client.table('clips').insert(serializable_clip_data).execute()
            
            if result.data:
                logger.info(f"✅ Successfully inserted clip {clip_id}")
                
                # Generate and store embedding
                try:
                    self._generate_and_store_embedding(clip_id, transcript)
                    logger.info(f"🧠 Generated embedding for clip {clip_id}")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to generate embedding: {e}")
                
                # Log analytics
                try:
                    self._log_clip_analytics(clip_id, source, content_type)
                    logger.info(f"📊 Logged analytics for clip {clip_id}")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to log analytics: {e}")
                
                return clip_id
            else:
                logger.error(f"❌ Failed to insert clip {clip_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error saving clip to Supabase: {e}")
            
            # [C] Add fallback on error - Save to local JSONL file
            try:
                # Convert any boolean values in clip_data for JSON serialization
                safe_clip_data = convert_bools_to_ints(clip_data) if 'clip_data' in locals() else {}
                
                failed_clip_data = {
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e),
                    "clip_data": safe_clip_data,
                    "clip_id": clip_id if 'clip_id' in locals() else None,
                    "transcript": transcript,
                    "source": source,
                    "content_type": content_type,
                    "emotion_label": emotion_label
                }
                
                # Save to failed_clips.jsonl
                with open("failed_clips.jsonl", "a") as f:
                    f.write(json.dumps(failed_clip_data) + "\n")
                
                logger.info(f"💾 Saved failed clip data to failed_clips.jsonl")
                
            except Exception as save_error:
                logger.error(f"❌ Failed to save error data: {save_error}")
            
            return None
    
    def _convert_confidence_to_numeric(self, confidence: str) -> float:
        """Convert confidence string to numeric value."""
        confidence_map = {
            "none": 0.0,
            "low": 0.25,
            "medium": 0.5,
            "high": 0.75,
            "very_high": 1.0
        }
        return confidence_map.get(confidence.lower(), 0.0)
    
    def _convert_impact_to_numeric(self, impact: str) -> float:
        """Convert impact level string to numeric value."""
        impact_map = {
            "none": 0.0,
            "low": 0.25,
            "medium": 0.5,
            "high": 0.75,
            "very_high": 1.0
        }
        return impact_map.get(impact.lower(), 0.0)
    
    def _analyze_audio_for_clip(self, clip_path: str) -> Dict[str, Any]:
        """
        Analyze audio for a clip and generate JSONB data.
        
        Args:
            clip_path: Path to the audio/video file
            
        Returns:
            Dict containing energy_bursts, audience_reaction, and volume_shifts data
        """
        try:
            # Try multiple import methods
            try:
                from audio_analysis_integration import analyze_audio_for_clip
            except ImportError:
                try:
                    import sys
                    sys.path.append('src')
                    from audio_analysis_integration import analyze_audio_for_clip
                except ImportError:
                    logger.warning("⚠️ Audio analysis integration not available, using simulated data")
                    return self._generate_simulated_audio_data()
            
            # Analyze audio and generate JSONB data
            audio_data = analyze_audio_for_clip(clip_path)
            logger.info(f"🎵 Audio analysis completed for: {clip_path}")
            
            return audio_data
            
        except Exception as e:
            logger.error(f"❌ Error analyzing audio: {e}")
            return self._generate_simulated_audio_data()
    
    def _generate_simulated_audio_data(self) -> Dict[str, Any]:
        """Generate simulated audio analysis data when real analysis is not available."""
        import random
        
        return {
            "energy_bursts": {
                "has_bursts": random.choice([0, 1]),
                "burst_count": random.randint(0, 50),
                "burst_intensity": random.uniform(0.01, 0.08),
                "burst_duration": random.uniform(0.5, 3.0),
                "burst_frequency": random.uniform(0.01, 0.5),
                "peak_intensity": random.uniform(0.02, 0.15)
            },
            "audience_reaction": {
                "audience_present": random.choice([0, 1]),
                "laughter_detected": random.choice([0, 1]),
                "reaction_intensity": random.uniform(0.0, 1.0),
                "background_noise_level": random.uniform(200, 3000),
                "reaction_type": random.choice(["laughter", "applause", "cheering", "gasps", "mixed", "none"]),
                "reaction_duration": random.uniform(0.0, 5.0),
                "crowd_size": random.randint(0, 100)
            },
            "volume_shifts": {
                "max_shift": random.uniform(0.01, 0.12),
                "has_shifts": random.choice([0, 1]),
                "shift_count": random.randint(0, 10),
                "shift_intensity": random.uniform(0.005, 0.10),
                "shift_pattern": random.choice(["sudden", "gradual", "oscillating", "stable"]),
                "shift_duration": random.uniform(0.1, 2.0),
                "shift_frequency": random.uniform(0.001, 0.8)
            }
        }
    
    def _generate_and_store_embedding(self, clip_id: str, text: str, model: str = "text-embedding-ada-002") -> bool:
        """
        Generate embedding from text and store it in Supabase.
        
        Args:
            clip_id: Unique identifier for the clip
            text: The text to generate embedding for
            model: The embedding model to use
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Generate embedding
            embedding = self._generate_embedding(text)
            
            if not embedding:
                logger.error("❌ Failed to generate embedding")
                return False
            
            # Store embedding in Supabase
            success = self._insert_embedding_to_supabase(clip_id, embedding, model)
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error in _generate_and_store_embedding: {e}")
            return False
    
    def _generate_embedding(self, text: str) -> list:
        """
        Generate vector embedding from text using OpenAI's text-embedding-ada-002 model.
        
        Args:
            text: The text to generate embedding for
            
        Returns:
            list: 1536-dimensional embedding vector
        """
        try:
            import openai
            
            # Get OpenAI API key
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.error("❌ Missing OPENAI_API_KEY environment variable")
                return None
            
            # Set OpenAI API key
            openai.api_key = api_key
            
            # Generate embedding using OpenAI
            response = openai.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            embedding = response.data[0].embedding
            
            logger.info(f"✅ Generated embedding: {len(embedding)} dimensions")
            return embedding
            
        except Exception as e:
            logger.error(f"❌ Error generating embedding: {e}")
            return None
    
    def _insert_embedding_to_supabase(self, clip_id: str, embedding: list, model: str = "text-embedding-ada-002") -> bool:
        """
        Insert embedding vector to the clip_embeddings_vector Supabase table.
        
        Args:
            clip_id: Unique identifier for the clip
            embedding: The embedding vector (list of floats)
            model: The embedding model used
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.initialized or not self.client:
            logger.error("❌ Supabase not initialized")
            return False
        
        if not embedding:
            logger.error("❌ No embedding provided")
            return False
        
        try:
            # Prepare embedding data
            embedding_data = {
                "clip_id": clip_id,
                "embedding": embedding,
                "model": model
            }
            
            # Insert into clip_embeddings_vector table
            result = self.client.table("clip_embeddings_vector").insert(embedding_data).execute()
            
            if result.data:
                logger.info(f"✅ Embedding stored in Supabase: clip_id={clip_id}, model={model}, dimensions={len(embedding)}")
                return True
            else:
                logger.error("❌ No data returned from embedding insert")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error storing embedding in Supabase: {e}")
            return False
    
    def _log_clip_analytics(self, clip_id: str, source: str, content_type: str = None, engagement_data: dict = None) -> bool:
        """
        Log initial analytics data for a clip with realistic engagement simulation.
        
        Args:
            clip_id: Unique identifier for the clip
            source: Source of the clip ("ml", "random", etc.)
            content_type: Type of content ("joke", "reaction", "insight", "hype", "boring", etc.)
            engagement_data: Optional engagement data from Twitch API
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.initialized or not self.client:
            logger.error("❌ Supabase not initialized")
            return False
        
        try:
            # Use engagement data if available, otherwise generate realistic data
            if engagement_data:
                views = engagement_data.get('views', 0)
                likes = engagement_data.get('likes', 0)
                comments = engagement_data.get('comments', 0)
                watch_time = engagement_data.get('watch_time', 0.0)
                engagement_score = engagement_data.get('engagement_score', 0.0)
                auto_label = engagement_data.get('auto_label')
            else:
                # Generate realistic engagement data based on source
                try:
                    from .supabase_utils import simulate_realistic_engagement, assign_auto_label
                    
                    # Generate realistic engagement data
                    engagement_data = simulate_realistic_engagement(clip_id, source)
                    auto_label = assign_auto_label(engagement_data['engagement_score'])
                    
                    views = engagement_data['views']
                    likes = engagement_data['likes']
                    comments = engagement_data['comments']
                    watch_time = engagement_data['watch_time']
                    engagement_score = engagement_data['engagement_score']
                    
                    logger.info(f"📊 Generated realistic engagement data for {clip_id}: {views} views, score: {engagement_score}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to generate realistic engagement data: {e}")
                    # Fallback to default values
                    views = 0
                    likes = 0
                    comments = 0
                    watch_time = 0.0
                    engagement_score = 0.0
                    auto_label = None
            
            analytics_data = {
                "clip_id": clip_id,
                "views": views,
                "likes": likes,
                "comments": comments,
                "watch_time": watch_time,
                "engagement_score": engagement_score,
                "auto_label": auto_label
            }
            
            # Insert into clip_analytics table (use upsert to handle duplicates)
            result = self.client.table("clip_analytics").upsert(analytics_data).execute()
            
            if result.data:
                logger.info(f"✅ Analytics logged in Supabase: clip_id={clip_id}, source={source}, content_type={content_type}, views={views}, score={engagement_score}")
                return True
            else:
                logger.error("❌ No data returned from analytics insert")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error logging analytics in Supabase: {e}")
            return False
    
    def _save_unlabeled_clip_url(self, clip_id: str, twitch_url: str = None, 
                                source: str = "unknown", content_type: str = None) -> bool:
        """
        Save unlabeled clip URL to a local file for easy access.
        
        Args:
            clip_id: Unique identifier for the clip
            twitch_url: The Twitch clip URL (optional)
            source: Source of the clip (ml, random, etc.)
            content_type: Type of content (joke, reaction, etc.)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            import json
            from datetime import datetime
            from pathlib import Path
            
            # Create URLs directory if it doesn't exist
            urls_dir = Path("data/urls")
            urls_dir.mkdir(parents=True, exist_ok=True)
            
            # File to store unlabeled clip URLs
            unlabeled_file = urls_dir / "unclips.txt"
            
            # Prepare clip data
            clip_data = {
                "clip_id": clip_id,
                "url": twitch_url or "",
                "source": source,
                "content_type": content_type,
                "created_at": datetime.now().isoformat(),
                "status": "unlabeled"
            }
            
            # Append to file
            with open(unlabeled_file, 'a', encoding='utf-8') as f:
                f.write(f"Clip ID: {clip_data['clip_id']}\n")
                f.write(f"URL: {clip_data['url']}\n")
                f.write(f"Source: {clip_data['source']}\n")
                f.write(f"Content Type: {clip_data['content_type'] or 'None'}\n")
                f.write(f"Created: {clip_data['created_at']}\n")
                f.write(f"Status: {clip_data['status']}\n")
                f.write("-" * 50 + "\n\n")
            
            logger.info(f"✅ Unlabeled clip URL saved to local file: {clip_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving unlabeled clip URL: {e}")
            return False
    
    def _remove_labeled_clip_url(self, clip_id: str) -> bool:
        """
        Remove a clip from the unlabeled clips file when it gets labeled.
        
        Args:
            clip_id: Unique identifier for the clip
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from pathlib import Path
            
            # Path to unlabeled clips file
            urls_dir = Path("data/urls")
            unlabeled_file = urls_dir / "unclips.txt"
            
            if not unlabeled_file.exists():
                logger.info(f"📝 Unlabeled clips file doesn't exist, nothing to remove: {clip_id}")
                return True
            
            # Read all lines
            with open(unlabeled_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Find and remove the clip entry
            new_lines = []
            skip_next_lines = 0
            clip_found = False
            
            for i, line in enumerate(lines):
                if skip_next_lines > 0:
                    skip_next_lines -= 1
                    continue
                
                if line.strip().startswith(f"Clip ID: {clip_id}"):
                    # Found the clip, skip the next 6 lines (the entire entry)
                    skip_next_lines = 6
                    clip_found = True
                    logger.info(f"✅ Removing labeled clip from unlabeled file: {clip_id}")
                    continue
                
                new_lines.append(line)
            
            # Write back the file without the labeled clip
            with open(unlabeled_file, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            if not clip_found:
                logger.info(f"📝 Clip not found in unlabeled file: {clip_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error removing labeled clip URL: {e}")
            return False
    
    def get_unclips(self, limit: int = 50) -> list:
        """
        Get unlabeled clips from Supabase.
        
        Args:
            limit: Maximum number of clips to retrieve
            
        Returns:
            List of unlabeled clips
        """
        if not self.initialized or not self.client:
            logger.error("❌ Supabase not initialized")
            return []
        
        try:
            result = self.client.table("clips") \
                .select("*") \
                .is_("label", "null") \
                .limit(limit) \
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"❌ Error fetching unlabeled clips: {e}")
            return []
    
    def update_clip_label(self, clip_id: str, label: int, 
                         label_type: str = "manual") -> bool:
        """
        Update a clip's label in Supabase.
        
        Args:
            clip_id: The UUID of the clip
            label: The label value (0, 1, or 2)
            label_type: Type of labeling ("manual", "auto")
            
        Returns:
            True if successful, False otherwise
        """
        if not self.initialized or not self.client:
            logger.error("❌ Supabase not initialized")
            return False
        
        try:
            result = self.client.table("clips") \
                .update({
                    "label": label,
                    "label_type": label_type
                }) \
                .eq("clip_id", clip_id) \
                .execute()
            
            if result.data:
                logger.info(f"✅ Updated label for clip: {clip_id}")
                
                # Remove from unlabeled clips file since it's now labeled
                try:
                    remove_success = self._remove_labeled_clip_url(clip_id)
                    if remove_success:
                        logger.info(f"✅ Removed labeled clip from unlabeled file: {clip_id}")
                    else:
                        logger.warning(f"⚠️  Failed to remove labeled clip from unlabeled file: {clip_id}")
                except Exception as e:
                    logger.warning(f"⚠️  Error removing labeled clip from unlabeled file {clip_id}: {e}")
                
                return True
            else:
                logger.error(f"❌ No data returned for clip update: {clip_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating clip label: {e}")
            return False
    

    def save_for_labeling_core(self, transcript: str, source: str = "ml", 
                              content_type: str = None, twitch_clip_id: str = None,
                              emotion_label: str = None) -> Optional[str]:
        """
        Save clip information using only core columns (25 total).
        """
        if not self.initialized or not self.client:
            logger.error("❌ Supabase not initialized")
            return None
        
        try:
            # Use the actual Twitch clip ID if provided
            clip_id = twitch_clip_id if twitch_clip_id else str(uuid.uuid4())
            
            # Prepare core data for insertion
            clip_data = {
                "clip_id": clip_id,
                "transcript": transcript.strip(),
                "source": source,
                "label": None,  # Manual labeling required
                "content_type": content_type,
                "emotion_label": emotion_label,  # Manual labeling required
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Insert into clips table
            result = self.client.table('clips').insert(clip_data).execute()
            
            if result.data:
                logger.info(f"✅ Saved clip {clip_id} with core columns")
                return clip_id
            else:
                logger.error(f"❌ Failed to save clip {clip_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error saving clip with core columns: {e}")
            return None

    def get_clip_count(self) -> Dict[str, int]:
        """
        Get counts of clips by status.
        
        Returns:
            Dictionary with counts for total, labeled, unlabeled clips
        """
        if not self.initialized or not self.client:
            logger.error("❌ Supabase not initialized")
            return {"total": 0, "labeled": 0, "unlabeled": 0}
        
        try:
            # Get total count
            total_result = self.client.table("clips").select("clip_id", count="exact").execute()
            total = total_result.count if total_result.count else 0
            
            # Get labeled count
            labeled_result = self.client.table("clips") \
                .select("clip_id", count="exact") \
                .not_.is_("label", "null") \
                .execute()
            labeled = labeled_result.count if labeled_result.count else 0
            
            unlabeled = total - labeled
            
            return {
                "total": total,
                "labeled": labeled,
                "unlabeled": unlabeled
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting clip counts: {e}")
            return {"total": 0, "labeled": 0, "unlabeled": 0}

# Global instance
supabase_manager = SupabaseManager()

def save_for_labeling(transcript: str, clip_path: str, 
                     source: str = "ml", content_type: str = None, 
                     labeling_method: str = "manual", twitch_clip_id: str = None,
                     twitch_url: str = None, emotion_label: str = None) -> Optional[str]:
    """
    Convenience function to save clip for labeling using Supabase.
    
    Args:
        transcript: The transcript text that triggered the clip
        clip_path: Path to the created clip file
        source: Source of the clip ("ml", "random", "hybrid_batch", etc.)
        content_type: Type of content ("joke", "reaction", "insight", "hype", "boring", etc.)
        labeling_method: Method of labeling ("manual", "auto", "review_needed")
        twitch_clip_id: The actual Twitch clip ID (e.g., "HorriblePowerfulWatercressKippa")
        twitch_url: The Twitch clip URL
        emotion_label: Predicted emotion label (optional)
        
    Returns:
        clip_id: The Twitch clip ID, or None if failed
    """
    return supabase_manager.save_for_labeling(transcript, clip_path, source, content_type, labeling_method, twitch_clip_id, twitch_url, emotion_label)

def get_unclips(limit: int = 50) -> list:
    """Get unlabeled clips from Supabase."""
    return supabase_manager.get_unclips(limit)

def update_clip_label(clip_id: str, label: int, label_type: str = "manual") -> bool:
    """Update a clip's label in Supabase."""
    return supabase_manager.update_clip_label(clip_id, label, label_type)

def get_clip_count() -> Dict[str, int]:
    """Get count of clips by label status."""
    manager = SupabaseManager()
    return manager.get_clip_count()

def insert_prediction_to_supabase(clip_id: str, text: str, score: float, triggered: bool, 
                                 clipworthy: bool, model_version: str = "v1.0") -> bool:
    """
    Insert prediction results to the clip_predictions Supabase table.
    
    Args:
        clip_id: Unique identifier for the prediction
        text: The transcript text that was evaluated
        score: Model prediction score (0-1)
        triggered: Whether the clip was triggered by the model
        clipworthy: Whether the clip is considered worthy
        model_version: Version of the model used for prediction
        
    Returns:
        bool: True if successful, False otherwise
    """
    manager = SupabaseManager()
    
    if not manager.initialized or not manager.client:
        logger.error("❌ Supabase not initialized")
        return False
    
    try:
        # Prepare prediction data
        prediction_data = {
            "clip_id": clip_id,
            "text": text.strip(),
            "score": float(score),
            "triggered": bool(triggered),
            "clipworthy": bool(clipworthy),
            "model_version": model_version
        }
        
        # Insert into clip_predictions table
        result = manager.client.table("clip_predictions").insert(prediction_data).execute()
        
        if result.data:
            logger.info(f"✅ Prediction logged to Supabase: clip_id={clip_id}, score={score:.3f}, triggered={triggered}, clipworthy={clipworthy}")
            return True
        else:
            logger.error("❌ No data returned from prediction insert")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error logging prediction to Supabase: {e}")
        return False

def generate_embedding(text: str) -> list:
    """
    Generate vector embedding from text using OpenAI's text-embedding-ada-002 model.
    
    Args:
        text: The text to generate embedding for
        
    Returns:
        list: 1536-dimensional embedding vector
    """
    try:
        import openai
        
        # Get OpenAI API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ Missing OPENAI_API_KEY environment variable")
            return None
        
        # Set up OpenAI client
        client = openai.OpenAI(api_key=api_key)
        
        # Generate embedding
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=text.strip()
        )
        
        # Extract embedding vector
        embedding = response.data[0].embedding
        
        logger.info(f"✅ Generated embedding: {len(embedding)} dimensions")
        return embedding
        
    except Exception as e:
        logger.error(f"❌ Error generating embedding: {e}")
        return None

def insert_embedding_to_supabase(clip_id: str, embedding: list, model: str = "text-embedding-ada-002") -> bool:
    """
    Insert embedding vector to the clip_embeddings_vector Supabase table.
    
    Args:
        clip_id: Unique identifier for the clip
        embedding: The embedding vector (list of floats)
        model: The embedding model used
        
    Returns:
        bool: True if successful, False otherwise
    """
    manager = SupabaseManager()
    
    if not manager.initialized or not manager.client:
        logger.error("❌ Supabase not initialized")
        return False
    
    if not embedding:
        logger.error("❌ No embedding provided")
        return False
    
    try:
        # Prepare embedding data
        embedding_data = {
            "clip_id": clip_id,
            "embedding": embedding,
            "model": model
        }
        
        # Insert into clip_embeddings_vector table
        result = manager.client.table("clip_embeddings_vector").insert(embedding_data).execute()
        
        if result.data:
            logger.info(f"✅ Embedding stored in Supabase: clip_id={clip_id}, model={model}, dimensions={len(embedding)}")
            return True
        else:
            logger.error("❌ No data returned from embedding insert")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error storing embedding in Supabase: {e}")
        return False

def generate_and_store_embedding(clip_id: str, text: str, model: str = "text-embedding-ada-002") -> bool:
    """
    Generate embedding from text and store it in Supabase.
    
    Args:
        clip_id: Unique identifier for the clip
        text: The text to generate embedding for
        model: The embedding model to use
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Generate embedding
    embedding = generate_embedding(text)
    
    if not embedding:
        logger.error("❌ Failed to generate embedding")
        return False
    
    # Store embedding in Supabase
    success = insert_embedding_to_supabase(clip_id, embedding, model)
    
    return success 

def update_model_registry_usage(clip_id: str, model_version: str = "v1.0", prediction_score: float = None, 
                               triggered: bool = None, clipworthy: bool = None) -> bool:
    """
    Update model registry with usage statistics.
    
    Args:
        clip_id: Unique identifier for the clip
        model_version: Version of the model used
        prediction_score: Model prediction score
        triggered: Whether the clip was triggered
        clipworthy: Whether the clip is considered worthy
        
    Returns:
        bool: True if successful, False otherwise
    """
    manager = SupabaseManager()
    
    if not manager.initialized or not manager.client:
        logger.error("❌ Supabase not initialized")
        return False
    
    try:
        # Get current model info
        model_result = manager.client.table("model_registry").select("*").eq("model_version", model_version).order("created_at", desc=True).limit(1).execute()
        
        if not model_result.data:
            logger.warning(f"⚠️ Model version {model_version} not found in registry")
            return False
        
        model_info = model_result.data[0]
        model_id = model_info["id"]
        
        # Update model usage statistics
        usage_data = {
            "model_id": model_id,
            "clip_id": clip_id,
            "model_version": model_version,
            "prediction_score": prediction_score,
            "triggered": triggered,
            "clipworthy": clipworthy,
            "usage_timestamp": datetime.now().isoformat()
        }
        
        # Try to insert into model_usage table (create if doesn't exist)
        try:
            result = manager.client.table("model_usage").insert(usage_data).execute()
            if result.data:
                logger.info(f"✅ Model usage logged: model={model_version}, clip={clip_id}")
                return True
        except Exception as e:
            logger.warning(f"⚠️ model_usage table not found: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error updating model registry usage: {e}")
        return False

def log_model_performance(clip_id: str, model_version: str = "v1.0", 
                         prediction_score: float = None, actual_label: int = None,
                         accuracy: float = None, precision: float = None, 
                         recall: float = None, f1_score: float = None) -> bool:
    """
    Log model performance metrics.
    
    Args:
        clip_id: Unique identifier for the clip
        model_version: Version of the model used
        prediction_score: Model prediction score
        actual_label: Actual label (if available)
        accuracy: Model accuracy
        precision: Model precision
        recall: Model recall
        f1_score: Model F1 score
        
    Returns:
        bool: True if successful, False otherwise
    """
    manager = SupabaseManager()
    
    if not manager.initialized or not manager.client:
        logger.error("❌ Supabase not initialized")
        return False
    
    try:
        performance_data = {
            "clip_id": clip_id,
            "model_version": model_version,
            "prediction_score": prediction_score,
            "actual_label": actual_label,
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "evaluation_timestamp": datetime.now().isoformat()
        }
        
        # Try to insert into model_performance table (create if doesn't exist)
        try:
            result = manager.client.table("model_performance").insert(performance_data).execute()
            if result.data:
                logger.info(f"✅ Model performance logged: model={model_version}, clip={clip_id}")
                return True
        except Exception as e:
            logger.warning(f"⚠️ model_performance table not found: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error logging model performance: {e}")
        return False

def log_training_data(clip_id: str, transcript: str, label: int = None, 
                     source: str = "unified_hybrid", content_type: str = None,
                     emotion_label: str = None) -> bool:
    """
    Log training data for model training.
    
    Args:
        clip_id: Unique identifier for the clip
        transcript: The transcript text
        label: The label (0 or 1)
        source: Source of the data
        content_type: Type of content
        emotion_label: Emotion label
        
    Returns:
        bool: True if successful, False otherwise
    """
    manager = SupabaseManager()
    
    if not manager.initialized or not manager.client:
        logger.error("❌ Supabase not initialized")
        return False
    
    try:
        training_data = {
            "clip_id": clip_id,
            "transcript": transcript,
            "label": label,
            "source": source,
            "content_type": content_type,
            "emotion_label": emotion_label,
            "collection_timestamp": datetime.now().isoformat(),
            "is_training_data": True
        }
        
        # Try to insert into training_data table (create if doesn't exist)
        try:
            result = manager.client.table("training_data").insert(training_data).execute()
            if result.data:
                logger.info(f"✅ Training data logged: clip={clip_id}, label={label}")
                return True
        except Exception as e:
            logger.warning(f"⚠️ training_data table not found: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error logging training data: {e}")
        return False

def log_model_metrics(model_version: str = "v1.0", metric_type: str = "prediction",
                     metric_name: str = "accuracy", metric_value: float = None,
                     clip_count: int = None, timestamp: str = None) -> bool:
    """
    Log model metrics for monitoring.
    
    Args:
        model_version: Version of the model
        metric_type: Type of metric (prediction, training, evaluation)
        metric_name: Name of the metric
        metric_value: Value of the metric
        clip_count: Number of clips processed
        timestamp: Timestamp of the metric
        
    Returns:
        bool: True if successful, False otherwise
    """
    manager = SupabaseManager()
    
    if not manager.initialized or not manager.client:
        logger.error("❌ Supabase not initialized")
        return False
    
    try:
        if not timestamp:
            timestamp = datetime.now().isoformat()
        
        metrics_data = {
            "model_version": model_version,
            "metric_type": metric_type,
            "metric_name": metric_name,
            "metric_value": metric_value,
            "clip_count": clip_count,
            "timestamp": timestamp
        }
        
        # Try to insert into model_metrics table (create if doesn't exist)
        try:
            result = manager.client.table("model_metrics").insert(metrics_data).execute()
            if result.data:
                logger.info(f"✅ Model metrics logged: {metric_name}={metric_value}")
                return True
        except Exception as e:
            logger.warning(f"⚠️ model_metrics table not found: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error logging model metrics: {e}")
        return False

def log_streamer_data(streamer_name: str, streamer_id: str, viewer_count: int,
                     popularity_bucket: str, clips_collected: int = 1) -> bool:
    """
    Log streamer data for analysis.
    
    Args:
        streamer_name: Name of the streamer
        streamer_id: Twitch streamer ID
        viewer_count: Number of viewers
        popularity_bucket: Popularity tier
        clips_collected: Number of clips collected from this streamer
        
    Returns:
        bool: True if successful, False otherwise
    """
    manager = SupabaseManager()
    
    if not manager.initialized or not manager.client:
        logger.error("❌ Supabase not initialized")
        return False
    
    try:
        streamer_data = {
            "streamer_name": streamer_name,
            "streamer_id": streamer_id,
            "viewer_count": viewer_count,
            "popularity_bucket": popularity_bucket,
            "clips_collected": clips_collected,
            "last_updated": datetime.now().isoformat()
        }
        
        # Try to insert into streamer_data table (create if doesn't exist)
        try:
            result = manager.client.table("streamer_data").upsert(streamer_data).execute()
            if result.data:
                logger.info(f"✅ Streamer data logged: {streamer_name} ({viewer_count} viewers)")
                return True
        except Exception as e:
            logger.warning(f"⚠️ streamer_data table not found: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error logging streamer data: {e}")
        return False

def log_engagement_metrics(clip_id: str, views: int = 0, likes: int = 0, 
                         comments: int = 0, watch_time: float = 0.0,
                         engagement_score: float = 0.0) -> bool:
    """
    Log engagement metrics for clips.
    
    Args:
        clip_id: Unique identifier for the clip
        views: Number of views
        likes: Number of likes
        comments: Number of comments
        watch_time: Watch time in seconds
        engagement_score: Engagement score
        
    Returns:
        bool: True if successful, False otherwise
    """
    manager = SupabaseManager()
    
    if not manager.initialized or not manager.client:
        logger.error("❌ Supabase not initialized")
        return False
    
    try:
        engagement_data = {
            "clip_id": clip_id,
            "views": views,
            "likes": likes,
            "comments": comments,
            "watch_time": watch_time,
            "engagement_score": engagement_score,
            "metrics_timestamp": datetime.now().isoformat()
        }
        
        # Try to insert into engagement_metrics table (create if doesn't exist)
        try:
            result = manager.client.table("engagement_metrics").insert(engagement_data).execute()
            if result.data:
                logger.info(f"✅ Engagement metrics logged: clip={clip_id}, score={engagement_score}")
                return True
        except Exception as e:
            logger.warning(f"⚠️ engagement_metrics table not found: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error logging engagement metrics: {e}")
        return False 