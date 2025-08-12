#!/usr/bin/env python3
"""
Weekly retraining script for the Self Training Clipping Model.
Automatically generates new embeddings and retrains the model with updated data.
"""

import os
import sys
import subprocess
from datetime import datetime

def run_embedding_generation():
    """
    Run the embedding generation process using preprocess.py
    """
    print("🔄 Step 1: Generating embeddings...")
    print("-" * 50)
    
    try:
        # Import and run the embedding generation
        from preprocess import generate_embeddings
        
        generate_embeddings()
        print("✅ Embedding generation completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during embedding generation: {e}")
        return False

def run_model_training():
    """
    Run the model training process using train_model.py
    """
    print("\n🔄 Step 2: Training model...")
    print("-" * 50)
    
    try:
        # Import and run the model training
        from train_model import main as train_main
        
        train_main()
        print("✅ Model training completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during model training: {e}")
        return False

def weekly_retrain():
    """
    Main function to run the complete weekly retraining pipeline.
    """
    start_time = datetime.now()
    
    print("🚀 Starting Weekly Retraining Pipeline")
    print("=" * 60)
    print(f"⏰ Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Step 1: Generate embeddings
    embedding_success = run_embedding_generation()
    
    if not embedding_success:
        print("❌ Embedding generation failed. Stopping retraining pipeline.")
        return False
    
    # Step 2: Train model
    training_success = run_model_training()
    
    if not training_success:
        print("❌ Model training failed. Retraining pipeline incomplete.")
        return False
    
    # Calculate completion time
    end_time = datetime.now()
    duration = end_time - start_time
    
    print("\n" + "=" * 60)
    print("✅ Weekly retraining complete!")
    print(f"⏱️  Total duration: {duration}")
    print(f"🕐 Completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    return True

def main():
    """
    Main entry point for the weekly retraining script.
    """
    try:
        success = weekly_retrain()
        
        if success:
            print("\n🎯 Weekly retraining pipeline completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Weekly retraining pipeline failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Weekly retraining interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during weekly retraining: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 