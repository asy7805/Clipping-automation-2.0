#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.supabase_client import get_client

def test_storage():
    """Simple storage test"""
    # Use service role
    os.environ["USE_SERVICE_ROLE"] = "true"
    sb = get_client()
    bucket_name = "raw"
    
    print(f"🧪 Testing storage access...")
    
    try:
        # Test upload
        test_content = b"Hello from clipping automation!"
        test_path = "test.txt"
        
        print(f"📤 Uploading test file...")
        sb.storage.from_(bucket_name).upload(test_path, test_content, {"upsert": "true"})
        print(f"✅ Upload successful")
        
        # Test download
        print(f"📥 Downloading test file...")
        downloaded = sb.storage.from_(bucket_name).download(test_path)
        print(f"✅ Download successful: {downloaded.decode()}")
        
        # Test public URL
        print(f"🔗 Testing public URL...")
        from src.db.supabase_client import get_public_url
        url = get_public_url(bucket_name, test_path)
        print(f"✅ Public URL: {url}")
        
        # Clean up
        print(f"🧹 Cleaning up...")
        sb.storage.from_(bucket_name).remove([test_path])
        print(f"✅ Cleanup successful")
        
        print(f"\n🎉 Storage is working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Storage test failed: {e}")
        return False

if __name__ == "__main__":
    test_storage()

