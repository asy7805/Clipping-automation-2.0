#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.supabase_client import get_client

def check_storage_setup():
    """Check Supabase Storage configuration"""
    # Use service role for storage operations
    os.environ["USE_SERVICE_ROLE"] = "true"
    sb = get_client()
    bucket_name = os.getenv("STORAGE_BUCKET", "raw")
    
    print(f"🔍 Checking Supabase Storage setup...")
    print(f"Bucket: {bucket_name}")
    print("-" * 50)
    
    try:
        # Check if bucket exists
        buckets = sb.storage.list_buckets()
        bucket_exists = any(bucket['id'] == bucket_name for bucket in buckets)
        
        if bucket_exists:
            print(f"✅ Bucket '{bucket_name}' exists")
            
            # Get bucket details
            bucket_info = next((b for b in buckets if b['id'] == bucket_name), None)
            if bucket_info:
                print(f"   Public: {bucket_info.get('public', False)}")
                print(f"   File size limit: {bucket_info.get('file_size_limit', 'N/A')}")
                print(f"   Allowed MIME types: {bucket_info.get('allowed_mime_types', 'N/A')}")
        else:
            print(f"❌ Bucket '{bucket_name}' does not exist")
            print(f"Available buckets: {[b['id'] for b in buckets]}")
            return False
            
        # Try to list files (test access)
        try:
            files = sb.storage.from_(bucket_name).list("")
            print(f"✅ Can list files in bucket")
            print(f"   Found {len(files)} files/folders")
            
            if files:
                print("   Sample files:")
                for file in files[:5]:
                    print(f"     - {file['name']}")
            else:
                print("   No files found (bucket is empty)")
                
        except Exception as e:
            print(f"❌ Cannot list files: {e}")
            return False
            
        # Test upload (small test file)
        test_content = b"test file content"
        test_path = "test_access.txt"
        
        try:
            sb.storage.from_(bucket_name).upload(test_path, test_content, {"upsert": "true"})
            print(f"✅ Can upload files to bucket")
            
            # Test download
            downloaded = sb.storage.from_(bucket_name).download(test_path)
            if downloaded == test_content:
                print(f"✅ Can download files from bucket")
            else:
                print(f"❌ Download test failed")
                
            # Clean up test file
            sb.storage.from_(bucket_name).remove([test_path])
            print(f"✅ Can delete files from bucket")
            
        except Exception as e:
            print(f"❌ Upload/download test failed: {e}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Storage check failed: {e}")
        return False

def create_bucket_if_needed():
    """Create the raw bucket if it doesn't exist"""
    # Use service role for storage operations
    os.environ["USE_SERVICE_ROLE"] = "true"
    sb = get_client()
    bucket_name = os.getenv("STORAGE_BUCKET", "raw")
    
    try:
        # Check if bucket exists
        buckets = sb.storage.list_buckets()
        bucket_exists = any(bucket['id'] == bucket_name for bucket in buckets)
        
        if not bucket_exists:
            print(f"🛠️  Creating bucket '{bucket_name}'...")
            sb.storage.create_bucket(bucket_name)
            print(f"✅ Created bucket '{bucket_name}'")
            
            # Try to make it public
            try:
                sb.storage.update_bucket(bucket_name, {"public": True})
                print(f"✅ Made bucket '{bucket_name}' public")
            except Exception as e:
                print(f"⚠️  Could not make bucket public: {e}")
        else:
            print(f"ℹ️  Bucket '{bucket_name}' already exists")
            
    except Exception as e:
        print(f"❌ Failed to create bucket: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Check and fix Supabase Storage setup")
    parser.add_argument("--create-bucket", action="store_true", help="Create bucket if it doesn't exist")
    
    args = parser.parse_args()
    
    if args.create_bucket:
        create_bucket_if_needed()
    else:
        success = check_storage_setup()
        if not success:
            print("\n💡 Try running with --create-bucket to create the bucket")
