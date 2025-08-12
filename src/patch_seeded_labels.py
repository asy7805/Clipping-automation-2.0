#!/usr/bin/env python3
"""
Patch script for labeled_clips.csv to add missing columns and reorder them.
This script ensures the CSV has the correct structure for the auto-labeling system.
"""

import pandas as pd
import os
from pathlib import Path

DATA_DIR = os.getenv("MODEL_DATA_DIR", "data/")

def patch_seeded_labels(csv_path=None):
    if csv_path is None:
        csv_path = Path(DATA_DIR) / "labeled_clips.csv"
    """
    Patch the labeled_clips.csv file by adding missing columns and reordering them.
    
    Args:
        csv_path: Path to the labeled_clips.csv file
    """
    
    # Check if file exists
    if not os.path.exists(csv_path):
        print(f"❌ File not found: {csv_path}")
        return False
    
    print(f"📊 Loading data from {csv_path}")
    
    # Load the CSV file
    df = pd.read_csv(csv_path, keep_default_na=False)
    
    print(f"✅ Loaded {len(df)} clips")
    print(f"📋 Current columns: {list(df.columns)}")
    
    # Define the expected column order
    expected_columns = [
        'clip_id', 
        'text', 
        'label', 
        'views', 
        'watch_time', 
        'likes', 
        'comments', 
        'auto_label', 
        'label_type'
    ]
    
    # Add missing columns with default values
    print("\n🔧 Adding missing columns with default values...")
    
    missing_columns = []
    
    # Check and add each expected column
    if 'views' not in df.columns:
        df['views'] = 0
        missing_columns.append('views')
    else:
        # Ensure views is integer type
        df['views'] = df['views'].astype(int)
        print("🔄 Converted views to integer type")
    
    if 'watch_time' not in df.columns:
        df['watch_time'] = 0.0
        missing_columns.append('watch_time')
    
    if 'likes' not in df.columns:
        df['likes'] = 0
        missing_columns.append('likes')
    else:
        # Ensure likes is integer type
        df['likes'] = df['likes'].astype(int)
        print("🔄 Converted likes to integer type")
    
    if 'comments' not in df.columns:
        df['comments'] = 0
        missing_columns.append('comments')
    else:
        # Ensure comments is integer type
        df['comments'] = df['comments'].astype(int)
        print("🔄 Converted comments to integer type")
    
    # Ensure label is integer type (for 0, 1, 2 labels)
    if 'label' in df.columns:
        df['label'] = df['label'].astype(int)
        print("🔄 Converted label to integer type")
    
    if 'auto_label' not in df.columns:
        df['auto_label'] = ""
        missing_columns.append('auto_label')
    else:
        # Convert existing auto_label column to string and set empty values
        # Handle NaN values by filling them with empty strings and force string type
        df['auto_label'] = df['auto_label'].fillna("").astype(str)
        print("🔄 Converted auto_label column to string type and filled NaN values")
    
    if 'label_type' not in df.columns:
        df['label_type'] = "manual"
        missing_columns.append('label_type')
    elif df['label_type'].dtype == 'float64':
        # Convert existing label_type column to string and set manual values
        df['label_type'] = "manual"
        print("🔄 Converted label_type column to string type")
    else:
        # Reset all label_type values to "manual" for seeded data
        df['label_type'] = "manual"
        print("🔄 Reset all label_type values to 'manual'")
    
    if missing_columns:
        print(f"✅ Added missing columns: {missing_columns}")
    else:
        print("✅ All expected columns already exist")
    
    # Reorder columns to match expected structure
    print("\n🔄 Reordering columns...")
    
    # Get existing columns that are in the expected order
    ordered_columns = [col for col in expected_columns if col in df.columns]
    
    # Add any remaining columns that weren't in the expected order
    remaining_columns = [col for col in df.columns if col not in expected_columns]
    final_columns = ordered_columns + remaining_columns
    
    # Reorder the DataFrame
    df = df[final_columns]
    
    print(f"✅ Reordered columns: {list(df.columns)}")
    
    # Print summary of changes
    print("\n📈 Patching Summary:")
    print("-" * 40)
    print(f"Total clips: {len(df)}")
    print(f"Columns after patching: {len(df.columns)}")
    print(f"Columns added: {len(missing_columns)}")
    print(f"Column order: {list(df.columns)}")
    
    # Show sample of data to verify structure
    print("\n📋 Sample data structure:")
    print(df.head(2).to_string())
    
    # Save the updated DataFrame
    print(f"\n💾 Saving updated data to {csv_path}")
    df.to_csv(csv_path, index=False, na_rep='')
    
    print("✅ Patching completed successfully!")
    
    return True

def main():
    """Main function to run the patching pipeline."""
    try:
        success = patch_seeded_labels()
        if success:
            print(f"\n🎯 Patching pipeline completed!")
            print(f"📁 Updated file: {csv_path}")
        else:
            print(f"\n❌ Patching pipeline failed!")
    except Exception as e:
        print(f"❌ Error during patching: {e}")
        raise

if __name__ == "__main__":
    main() 