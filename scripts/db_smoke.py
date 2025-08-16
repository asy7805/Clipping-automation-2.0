# scripts/db_smoke.py
import os
import sys
import json
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.supabase_client import get_client, insert_row, fetch_one, upload_bytes, get_public_url

def main():
    # Set environment to use service role for smoke test
    os.environ["USE_SERVICE_ROLE"] = "true"
    
    sb = get_client()
    print("✅ Supabase client initialized (using service role).")

    # --- 1) Insert into streams (adjust fields to match your schema defaults) ---
    payload = {
        "twitch_stream_id": f"smoke-{int(time.time())}",
        "user_id": os.getenv("SMOKE_TEST_USER_ID", None),  # optional: set this in .env for a real FK
        "channel_name": "smoke_test_channel",
        "title": "Smoke Test Stream",
        "category": "Just Chatting",
        "started_at": "2025-08-15T00:00:00Z",
        "viewer_count": 0,
    }

    row = insert_row("streams", payload)
    stream_id = row["id"]
    print(f"✅ Inserted stream id={stream_id}")

    # --- 2) Read back by id ---
    fetched = fetch_one("streams", id=stream_id)
    assert fetched is not None, "Failed to read back inserted stream"
    print(f"✅ Read back stream title={fetched['title']}")

    # --- 3) Storage upload (small JSON) ---
    bucket = os.getenv("STORAGE_BUCKET", "raw")
    path = f"smoke/{stream_id}.json"
    blob = json.dumps({"hello": "world", "stream_id": stream_id}).encode("utf-8")
    upload_bytes(bucket, path, blob, upsert=True)
    print(f"✅ Uploaded blob to {bucket}/{path}")

    # If bucket is public, show a URL; if private, this will still return a path (not accessible publicly).
    public_url = get_public_url(bucket, path)
    print(f"ℹ️  Public URL (if bucket is public): {public_url}")

    print("🎉 Smoke test completed.")

if __name__ == "__main__":
    main()
