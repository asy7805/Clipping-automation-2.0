#!/usr/bin/env python3
"""
Script to check if the clips table exists in Supabase and provide setup instructions.
This table stores clip information including transcripts, labels, and engagement metrics.
"""

import os
import logging
from supabase import create_client, Client
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_clips_table():
    """Check if clips table exists and provide setup instructions."""
    
    # Get Supabase credentials
    url: str = os.getenv("SUPABASE_URL")
    key: str = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        logger.error("❌ Missing Supabase credentials. Set SUPABASE_URL and SUPABASE_KEY environment variables.")
        return False
    
    try:
        supabase: Client = create_client(url, key)
        table_name = "clips"
        
        # Check if table exists
        logger.info(f"🔍 Checking if table '{table_name}' exists...")
        existing = supabase.table(table_name).select("*").limit(1).execute()
        
        if existing.data is not None:
            logger.info(f"✅ Table '{table_name}' exists and is accessible")
            
            # Get table info
            try:
                count_result = supabase.table(table_name).select("count", count="exact").execute()
                record_count = count_result.count if hasattr(count_result, 'count') else len(existing.data)
                logger.info(f"📊 Table contains {record_count} records")
                
                # Show sample data structure
                if existing.data:
                    logger.info("📋 Sample record structure:")
                    sample = existing.data[0]
                    for key, value in sample.items():
                        logger.info(f"   {key}: {type(value).__name__} = {value}")
                
            except Exception as e:
                logger.warning(f"⚠️ Could not get detailed table info: {e}")
            
            return True
            
        else:
            logger.warning("❌ Table not found or not accessible")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error checking table: {e}")
        return False

def provide_table_schema():
    """Provide the SQL schema for creating the clips table."""
    
    schema = """
-- Create clips table
CREATE TABLE IF NOT EXISTS clips (
    id BIGSERIAL PRIMARY KEY,
    clip_id TEXT NOT NULL UNIQUE,
    text TEXT NOT NULL,
    label FLOAT,  -- Can be NULL for unlabeled clips
    views FLOAT DEFAULT 0.0,
    watch_time FLOAT DEFAULT 0.0,
    likes FLOAT DEFAULT 0.0,
    comments FLOAT DEFAULT 0.0,
    auto_label TEXT DEFAULT '',
    label_type TEXT DEFAULT 'manual',
    engagement_score FLOAT DEFAULT 0.0,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    source TEXT DEFAULT 'auto',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_clips_clip_id ON clips(clip_id);
CREATE INDEX IF NOT EXISTS idx_clips_label ON clips(label);
CREATE INDEX IF NOT EXISTS idx_clips_label_type ON clips(label_type);
CREATE INDEX IF NOT EXISTS idx_clips_created_at ON clips(created_at);

-- Create a function to update the updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Drop trigger if it exists (to avoid conflicts)
DROP TRIGGER IF EXISTS update_clips_updated_at ON clips;

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_clips_updated_at 
    BEFORE UPDATE ON clips 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (optional)
-- ALTER TABLE clips ENABLE ROW LEVEL SECURITY;

-- Create policy for full access (adjust based on your needs)
-- CREATE POLICY "Allow full access to clips" ON clips
--     FOR ALL USING (true);
"""
    
    return schema

def check_csv_compatibility():
    """Check if local CSV file exists and show its structure."""
    
    csv_path = Path("data/clips.csv")
    if csv_path.exists():
        try:
            import pandas as pd
            df = pd.read_csv(csv_path)
            logger.info(f"📄 Local CSV file found: {len(df)} records")
            logger.info("📋 CSV columns:")
            for col in df.columns:
                logger.info(f"   - {col}: {df[col].dtype}")
            return True
        except Exception as e:
            logger.error(f"❌ Error reading CSV: {e}")
            return False
    else:
        logger.warning("⚠️ Local CSV file not found: data/clips.csv")
        return False

def provide_migration_instructions():
    """Provide instructions for migrating data from CSV to Supabase."""
    
    logger.info("\n🚀 Migration Instructions:")
    logger.info("=" * 50)
    logger.info("1. Create the table in Supabase dashboard:")
    logger.info("   - Go to https://supabase.com/dashboard")
    logger.info("   - Select your project")
    logger.info("   - Go to SQL Editor")
    logger.info("   - Copy and paste the schema below")
    logger.info("   - Execute the SQL")
    
    logger.info("\n2. After creating the table, run:")
    logger.info("   python scripts/migrate_csv_to_supabase.py")
    
    logger.info("\n3. Verify the migration:")
    logger.info("   python src/create_clips_table.py")

def main():
    """Main function to check and setup clips table."""
    
    logger.info("🔍 Labeled Clips Table Setup")
    logger.info("=" * 50)
    
    # Check if table exists
    table_exists = create_clips_table()
    
    if not table_exists:
        logger.info("\n📋 Table 'clips' not found or not accessible")
        logger.info("Creating setup instructions...")
        
        # Check local CSV
        check_csv_compatibility()
        
        # Provide schema
        logger.info("\n📋 SQL Schema for clips table:")
        logger.info("=" * 50)
        schema = provide_table_schema()
        print(schema)
        
        # Save schema to file
        schema_file = Path("supabase_clips_schema.sql")
        with open(schema_file, "w") as f:
            f.write(schema)
        logger.info(f"\n💾 Schema saved to: {schema_file}")
        
        # Provide migration instructions
        provide_migration_instructions()
        
        logger.info("\n⚠️ Manual Setup Required:")
        logger.info("1. Copy the SQL schema above")
        logger.info("2. Go to Supabase SQL Editor")
        logger.info("3. Paste and execute the SQL")
        logger.info("4. Run this script again to verify")
        
    else:
        logger.info("\n✅ Table setup complete!")
        logger.info("📋 Next steps:")
        logger.info("   - Use the table for clip labeling")
        logger.info("   - Integrate with your ML pipeline")
        logger.info("   - Run: python scripts/migrate_csv_to_supabase.py (if needed)")

if __name__ == "__main__":
    main() 