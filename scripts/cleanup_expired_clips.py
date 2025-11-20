#!/usr/bin/env python3
"""
Cleanup job for expired free trial clips.
Deletes clips that have expired (30 days old) for free trial users.

Run this daily via cron or scheduled task.
Example cron: 0 2 * * * /path/to/python /path/to/cleanup_expired_clips.py
"""

import os
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.db.supabase_client import get_admin_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cleanup_expired_clips():
    """
    Delete expired free trial clips from storage and database.
    """
    try:
        os.environ["USE_SERVICE_ROLE"] = "true"
        sb = get_admin_client()
        
        # Query expired clips from free trial users
        # Clips expire 30 days after creation for trial users
        now = datetime.now(timezone.utc)
        
        # Get expired clips
        expired_clips = sb.table('clips_metadata')\
            .select('id, storage_path, user_id, channel_name, created_at, expires_at')\
            .not_.is_('expires_at', 'null')\
            .lt('expires_at', now.isoformat())\
            .execute()
        
        if not expired_clips.data:
            logger.info("No expired clips found")
            return
        
        logger.info(f"Found {len(expired_clips.data)} expired clips to delete")
        
        deleted_count = 0
        failed_count = 0
        
        # Get bucket from environment
        bucket = os.getenv("STORAGE_BUCKET", "raw")
        
        for clip in expired_clips.data:
            try:
                clip_id = clip['id']
                storage_path = clip.get('storage_path')
                user_id = clip.get('user_id')
                
                # Delete from storage if storage_path exists
                if storage_path:
                    try:
                        # Extract bucket and path from storage_path if it includes bucket
                        # Format might be: "bucket/path/to/file" or just "path/to/file"
                        if '/' in storage_path:
                            path_parts = storage_path.split('/', 1)
                            if len(path_parts) == 2:
                                # Assume format is "bucket/path"
                                storage_bucket = path_parts[0]
                                storage_key = path_parts[1]
                            else:
                                storage_bucket = bucket
                                storage_key = storage_path
                        else:
                            storage_bucket = bucket
                            storage_key = storage_path
                        
                        sb.storage.from_(storage_bucket).remove([storage_key])
                        logger.info(f"Deleted storage file: {storage_key}")
                    except Exception as e:
                        logger.warning(f"Failed to delete storage file {storage_path}: {e}")
                        # Continue with database deletion even if storage deletion fails
                
                # Delete from database
                sb.table('clips_metadata').delete().eq('id', clip_id).execute()
                deleted_count += 1
                logger.info(f"Deleted clip {clip_id} (user: {user_id}, created: {clip.get('created_at')})")
                
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to delete clip {clip.get('id')}: {e}")
        
        logger.info(f"Cleanup complete: {deleted_count} deleted, {failed_count} failed")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    logger.info("Starting expired clips cleanup job...")
    cleanup_expired_clips()
    logger.info("Cleanup job completed")

