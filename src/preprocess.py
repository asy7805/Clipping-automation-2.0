#!/usr/bin/env python3
"""
Preprocessing script for Self Training Clipping Model.
Loads labeled clips from Supabase, generates embeddings using OpenAI API,
and uploads them to Supabase clip_embeddings_vector table.
"""

import numpy as np
import openai
import os
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATA_DIR = os.getenv("MODEL_DATA_DIR", "data/")

# Load OpenAI API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY environment variable is required. Please set it before running this script.")

def load_data_from_supabase():
    """Load labeled data directly from Supabase clips table."""
    try:
        # Get Supabase credentials
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found. Set SUPABASE_URL and SUPABASE_ANON_KEY/SUPABASE_KEY")
        
        # Create Supabase client
        supabase = create_client(supabase_url, supabase_key)
        
        # Query clips table for rows where label IS NOT NULL
        print("🔍 Querying clips table from Supabase...")
        response = supabase.table("clips").select("clip_id,text,label").not_.is_("label", "null").execute()
        
        if not response.data:
            print("⚠️ No labeled data found in Supabase")
            return []
        
        print(f"✅ Found {len(response.data)} labeled clips in Supabase")
        return response.data
        
    except Exception as e:
        print(f"❌ Error loading data from Supabase: {e}")
        return []

def generate_embeddings():
    """Generate embeddings and upload to Supabase."""
    
    # Load data from Supabase
    clips_data = load_data_from_supabase()
    if not clips_data:
        print("❌ No data to process")
        return
    
    print("🔄 Generating embeddings...")
    
    successful_uploads = 0
    failed_uploads = 0
    
    for i, clip in enumerate(clips_data, 1):
        clip_id = clip.get("clip_id", f"clip_{i}")
        text = clip.get("text", "")
        label = clip.get("label")
        
        if not isinstance(text, str) or not text.strip():
            print(f"⚠️  Skipping clip {clip_id}: No text content")
            continue

        try:
            # Generate embedding using OpenAI
            response = openai.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            embedding = response.data[0].embedding
            
            # Upload to Supabase directly
            try:
                # Get Supabase credentials
                supabase_url = os.getenv("SUPABASE_URL")
                supabase_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
                
                if not supabase_url or not supabase_key:
                    print(f"⚠️  Supabase credentials not found for {clip_id}")
                    failed_uploads += 1
                    continue
                
                # Create Supabase client
                supabase = create_client(supabase_url, supabase_key)
                
                # Prepare embedding data
                embedding_data = {
                    "clip_id": clip_id,
                    "embedding": embedding,
                    "model": "text-embedding-3-small",
                    "created_at": "now()"
                }
                
                # Insert into clip_embeddings_vector table
                response = supabase.table("clip_embeddings_vector").insert(embedding_data).execute()
                
                if response.data:
                    successful_uploads += 1
                    print(f"✅ Uploaded embedding for {clip_id}")
                else:
                    failed_uploads += 1
                    print(f"⚠️  Failed to upload embedding for {clip_id}")
                
            except Exception as e:
                print(f"⚠️  Failed to upload embedding for {clip_id}: {e}")
                failed_uploads += 1
                
        except Exception as e:
            print(f"❌ Embedding generation failed for {clip_id}: {e}")
            failed_uploads += 1
            continue

    print(f"\n📊 Embedding Generation Summary:")
    print(f"   ✅ Successful uploads: {successful_uploads}")
    print(f"   ❌ Failed uploads: {failed_uploads}")
    print(f"   📈 Success rate: {(successful_uploads/(successful_uploads+failed_uploads)*100):.1f}%")
    
    # Show Supabase upload summary if available
    try:
        # Get Supabase credentials
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
        
        if supabase_url and supabase_key:
            # Create Supabase client
            supabase = create_client(supabase_url, supabase_key)
            
            # Get total count
            total_response = supabase.table("clip_embeddings_vector").select("clip_id", count="exact").execute()
            total_count = total_response.count if hasattr(total_response, 'count') else len(total_response.data)
            
            print(f"📊 Supabase embeddings: {total_count} total")
    except Exception as e:
        print(f"⚠️  Could not get Supabase counts: {e}")

def main():
    """Main function to run the preprocessing pipeline"""
    try:
        generate_embeddings()
        print("✅ Preprocessing completed successfully!")
    except Exception as e:
        print(f"❌ Error during preprocessing: {e}")
        raise

if __name__ == "__main__":
    main() 