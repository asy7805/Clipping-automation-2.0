#!/usr/bin/env python3
"""
Migration script to move embeddings from X.npy to Supabase clip_embeddings_vector table.
This script uses pgvector for efficient vector storage and similarity search.
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.error("Supabase library not available. Install with: pip install supabase")

def check_supabase_setup() -> bool:
    """Check if Supabase is properly configured for pgvector."""
    if not SUPABASE_AVAILABLE:
        logger.error("❌ Supabase library not available")
        return False
    
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            logger.error("❌ Missing Supabase credentials")
            return False
        
        client = create_client(supabase_url, supabase_key)
        
        # Check if pgvector table exists
        response = client.table("clip_embeddings_vector").select("count", count="exact").execute()
        logger.info(f"✅ pgvector table accessible: {response.count} records")
        
        # Test similarity search function
        test_embedding = np.random.rand(1536).tolist()
        try:
            result = client.rpc('find_similar_clips', {
                'query_embedding': test_embedding,
                'similarity_threshold': 0.5,
                'limit_count': 5
            }).execute()
            logger.info("✅ pgvector similarity search working")
        except Exception as e:
            logger.warning(f"⚠️  Similarity search test failed: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Supabase connection failed: {e}")
        return False

def load_embeddings_and_clips() -> tuple[Optional[np.ndarray], Optional[pd.DataFrame]]:
    """
    Load embeddings from X.npy and clip data from clips.csv.
    
    Returns:
        tuple: (embeddings, clips_df)
    """
    try:
        # Load embeddings
        embeddings_path = Path("data/X.npy")
        if not embeddings_path.exists():
            logger.error(f"❌ Embeddings file not found: {embeddings_path}")
            return None, None
        
        embeddings = np.load(embeddings_path)
        logger.info(f"✅ Loaded embeddings: {embeddings.shape}")
        
        # Load labeled clips
        clips_path = Path("data/clips.csv")
        if not clips_path.exists():
            logger.error(f"❌ Labeled clips file not found: {clips_path}")
            return None, None
        
        clips_df = pd.read_csv(clips_path)
        logger.info(f"✅ Loaded labeled clips: {len(clips_df)} rows")
        
        # Verify data consistency
        if len(embeddings) != len(clips_df):
            logger.warning(f"⚠️  Mismatch: {len(embeddings)} embeddings vs {len(clips_df)} clips")
            # Use the smaller length to avoid errors
            min_length = min(len(embeddings), len(clips_df))
            embeddings = embeddings[:min_length]
            clips_df = clips_df.head(min_length)
            logger.info(f"✅ Adjusted to {min_length} records")
        
        return embeddings, clips_df
        
    except Exception as e:
        logger.error(f"❌ Error loading data: {e}")
        return None, None

def upload_embeddings_to_supabase(embeddings: np.ndarray, clip_ids: List[str], 
                                 batch_size: int = 25) -> tuple[int, int]:
    """
    Upload embeddings to Supabase clip_embeddings_vector table using pgvector.
    
    Args:
        embeddings: Embedding vectors as numpy array
        clip_ids: List of clip IDs corresponding to embeddings
        batch_size: Number of embeddings to upload per batch
        
    Returns:
        tuple: (successful_uploads, failed_uploads)
    """
    if not SUPABASE_AVAILABLE:
        logger.error("❌ Supabase not available")
        return 0, len(embeddings)
    
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        client = create_client(supabase_url, supabase_key)
        
        successful = 0
        failed = 0
        total_batches = (len(embeddings) + batch_size - 1) // batch_size
        
        logger.info(f"🔄 Starting upload of {len(embeddings)} embeddings to Supabase...")
        logger.info(f"   Batch size: {batch_size}")
        
        for i in range(0, len(embeddings), batch_size):
            batch_end = min(i + batch_size, len(embeddings))
            batch_embeddings = embeddings[i:batch_end]
            batch_clip_ids = clip_ids[i:batch_end]
            
            batch_data = []
            for j, (embedding, clip_id) in enumerate(zip(batch_embeddings, batch_clip_ids)):
                data = {
                    "clip_id": str(clip_id),
                    "embedding": embedding.tolist(),  # Convert to list for pgvector
                    "model": "openai",
                    "created_at": datetime.now().isoformat()
                }
                batch_data.append(data)
            
            try:
                response = client.table("clip_embeddings_vector").insert(batch_data).execute()
                successful += len(batch_data)
                batch_num = (i // batch_size) + 1
                logger.info(f"✅ Uploaded batch {batch_num}/{total_batches}: {len(batch_data)} embeddings")
                
            except Exception as e:
                failed += len(batch_data)
                logger.error(f"❌ Batch {batch_num} failed: {e}")
        
        logger.info(f"🎯 Upload completed:")
        logger.info(f"   ✅ Successful: {successful}")
        logger.info(f"   ❌ Failed: {failed}")
        logger.info(f"   📊 Total: {successful + failed}")
        
        return successful, failed
        
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        return 0, len(embeddings)

def verify_upload(original_count: int) -> bool:
    """
    Verify that the upload was successful by checking record count.
    
    Args:
        original_count: Number of embeddings that should have been uploaded
        
    Returns:
        bool: True if verification successful
    """
    if not SUPABASE_AVAILABLE:
        return False
    
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        client = create_client(supabase_url, supabase_key)
        
        response = client.table("clip_embeddings_vector").select("count", count="exact").execute()
        uploaded_count = response.count
        
        logger.info(f"📊 Verification:")
        logger.info(f"   Original embeddings: {original_count}")
        logger.info(f"   Uploaded to Supabase: {uploaded_count}")
        
        if uploaded_count >= original_count:
            logger.info("✅ Upload verification successful")
            return True
        else:
            logger.warning(f"⚠️  Upload verification failed: {uploaded_count} < {original_count}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False

def create_embeddings_table_schema() -> str:
    """Provide the SQL schema for the clip_embeddings_vector table."""
    schema = """
-- Create clip_embeddings_vector table with pgvector
CREATE TABLE IF NOT EXISTS clip_embeddings_vector (
    id BIGSERIAL PRIMARY KEY,
    clip_id TEXT NOT NULL,
    embedding vector(1536) NOT NULL,  -- pgvector type with 1536 dimensions
    model TEXT DEFAULT 'openai',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(clip_id, model)  -- Prevent duplicate embeddings for same clip/model
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_clip_embeddings_vector_clip_id ON clip_embeddings_vector(clip_id);
CREATE INDEX IF NOT EXISTS idx_clip_embeddings_vector_model ON clip_embeddings_vector(model);
CREATE INDEX IF NOT EXISTS idx_clip_embeddings_vector_created_at ON clip_embeddings_vector(created_at);

-- Create HNSW index for fast similarity search
CREATE INDEX IF NOT EXISTS idx_clip_embeddings_vector_embedding_hnsw 
ON clip_embeddings_vector 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Create similarity search function
CREATE OR REPLACE FUNCTION find_similar_clips(
    query_embedding vector(1536),
    similarity_threshold FLOAT DEFAULT 0.7,
    limit_count INTEGER DEFAULT 10
)
RETURNS TABLE (
    clip_id TEXT,
    similarity FLOAT,
    model TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cev.clip_id,
        1 - (cev.embedding <=> query_embedding) as similarity,
        cev.model
    FROM clip_embeddings_vector cev
    WHERE 1 - (cev.embedding <=> query_embedding) > similarity_threshold
    ORDER BY cev.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;
"""
    return schema

def main():
    """Main migration function."""
    logger.info("🚀 Starting embeddings migration to Supabase pgvector...")
    
    # Check Supabase setup
    if not check_supabase_setup():
        logger.error("❌ Supabase setup check failed")
        return
    
    # Load data
    embeddings, clips_df = load_embeddings_and_clips()
    if embeddings is None or clips_df is None:
        logger.error("❌ Failed to load data")
        return
    
    # Prepare clip IDs
    clip_ids = clips_df['clip_id'].astype(str).tolist()
    logger.info(f"✅ Prepared {len(embeddings)} embeddings with {len(clip_ids)} clip IDs")
    
    # Confirm with user
    response = input(f"\n📋 Ready to upload {len(embeddings)} embeddings to Supabase? (y/N): ")
    if response.lower() != 'y':
        logger.info("❌ Migration cancelled by user")
        return
    
    # Upload embeddings
    successful, failed = upload_embeddings_to_supabase(embeddings, clip_ids)
    
    if successful > 0:
        # Verify upload
        verify_upload(len(embeddings))
        
        logger.info("🎉 Migration completed successfully!")
        logger.info("📋 Next steps:")
        logger.info("   1. Test similarity search: python test_pgvector_functions.py")
        logger.info("   2. Update your code to use the new pgvector table")
        logger.info("   3. Consider removing local X.npy file to save space")
    else:
        logger.error("❌ Migration failed - no embeddings uploaded")

if __name__ == "__main__":
    main() 