"""
Celery tasks for social media posting.
Handles background video uploads and scheduled posts.
"""

import os
import tempfile
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from celery import current_task
from .celery_app import celery_app
from .tiktok_publisher import TikTokPublisher
from .youtube_publisher import YouTubePublisher
from ..db.supabase_client import get_client

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def post_to_social_media(self, queue_item_id: str):
    """
    Background task to post video to social media.
    
    Args:
        queue_item_id: UUID of the posting queue item
    """
    try:
        logger.info(f"Starting social media post task for queue item: {queue_item_id}")
        
        # Get Supabase client
        supabase = get_client()
        
        # Fetch queue item from database
        queue_response = supabase.table('posting_queue').select('*').eq('id', queue_item_id).execute()
        
        if not queue_response.data:
            raise Exception(f"Queue item {queue_item_id} not found")
        
        queue_item = queue_response.data[0]
        
        # Update status to processing
        supabase.table('posting_queue').update({
            'status': 'processing',
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', queue_item_id).execute()
        
        # Fetch social account details
        account_response = supabase.table('social_accounts').select('*').eq('id', queue_item['social_account_id']).execute()
        
        if not account_response.data:
            raise Exception(f"Social account {queue_item['social_account_id']} not found")
        
        account = account_response.data[0]
        
        # Download video from Supabase storage
        clip_id = queue_item['clip_id']  # This is the filename
        video_path = _download_video(clip_id)
        
        try:
            # Initialize publisher based on platform
            if account['platform'] == 'tiktok':
                publisher = TikTokPublisher(
                    access_token=account['access_token'],
                    refresh_token=account.get('refresh_token')
                )
            elif account['platform'] == 'youtube':
                publisher = YouTubePublisher(
                    access_token=account['access_token'],
                    refresh_token=account.get('refresh_token')
                )
            else:
                raise Exception(f"Unsupported platform: {account['platform']}")
            
            # Upload video - prepare parameters with proper defaults
            caption = queue_item.get('caption') or 'Auto-generated gaming clip from Twitch stream'
            upload_kwargs = {
                'caption': caption,
                'privacy_level': 'PUBLIC' if account['platform'] == 'tiktok' else 'public',
                'title': caption[:100] if len(caption) > 100 else caption,
                'description': f"{caption}\n\n#gaming #twitch #clips"[:5000],
                'tags': ['gaming', 'twitch', 'clips', 'highlights']
            }
            
            result = asyncio.run(publisher.upload_video(video_path, **upload_kwargs))
            
            # Update queue item with success
            supabase.table('posting_queue').update({
                'status': 'posted',
                'posted_at': datetime.utcnow().isoformat(),
                'post_url': result['video_url'],
                'platform_specific_data': result,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', queue_item_id).execute()
            
            logger.info(f"Successfully posted to {account['platform']}: {result['video_url']}")
            
        finally:
            # Clean up temporary video file
            if 'video_path' in locals() and os.path.exists(video_path):
                os.unlink(video_path)
        
    except Exception as e:
        logger.error(f"Social media post task failed: {e}")
        
        # Update queue item with error
        try:
            supabase.table('posting_queue').update({
                'status': 'failed',
                'error_message': str(e),
                'retry_count': self.request.retries + 1,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', queue_item_id).execute()
        except Exception as update_error:
            logger.error(f"Failed to update queue item with error: {update_error}")
        
        # Retry if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task in {self.default_retry_delay} seconds...")
            raise self.retry(countdown=self.default_retry_delay)
        else:
            logger.error(f"Task failed after {self.max_retries} retries")
            raise


@celery_app.task
def process_scheduled_posts():
    """
    Periodic task to check and post scheduled items.
    Runs every minute to process scheduled posts.
    """
    try:
        logger.info("Processing scheduled posts...")
        
        supabase = get_client()
        now = datetime.utcnow().isoformat()
        
        # Find scheduled posts that are ready to be posted
        scheduled_response = supabase.table('posting_queue').select('*').eq('status', 'pending').lte('scheduled_at', now).execute()
        
        if not scheduled_response.data:
            logger.info("No scheduled posts ready for processing")
            return
        
        logger.info(f"Found {len(scheduled_response.data)} scheduled posts ready for processing")
        
        # Queue each scheduled post for processing
        for queue_item in scheduled_response.data:
            post_to_social_media.delay(queue_item['id'])
            logger.info(f"Queued scheduled post: {queue_item['id']}")
        
    except Exception as e:
        logger.error(f"Error processing scheduled posts: {e}")


@celery_app.task
def cleanup_old_queue_items():
    """
    Cleanup old queue items to prevent database bloat.
    Removes items older than 30 days that are not pending.
    """
    try:
        logger.info("Cleaning up old queue items...")
        
        supabase = get_client()
        cutoff_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        
        # Delete old queue items (except pending ones)
        delete_response = supabase.table('posting_queue').delete().lt('created_at', cutoff_date).neq('status', 'pending').execute()
        
        logger.info(f"Cleaned up {len(delete_response.data) if delete_response.data else 0} old queue items")
        
    except Exception as e:
        logger.error(f"Error cleaning up old queue items: {e}")


def _download_video(clip_id: str) -> str:
    """
    Download video from Supabase storage to temporary file.
    
    Args:
        clip_id: ID of the video (with underscores instead of slashes)
        
    Returns:
        Path to the downloaded temporary video file
    """
    import requests
    from ..db.supabase_client import get_client
    
    try:
        # Get Supabase client
        supabase = get_client()
        
        # The clip_id is the id field from the clips API
        # We need to get the actual storage URL from the clips API
        # Let's use the clips API to get the storage URL
        
        # The clip_id is the id field from the clips API
        # We need to get the actual storage URL from the clips API
        # Let's use the clips API to get the storage URL
        
        # The clip_id is actually the storage path, not a database ID
        # The clips API constructs the storage_url from this path
        # Let's construct the storage URL directly from the clip_id
        
        # The clip_id format is: raw_CHANNEL_FILENAME
        # We need to convert it to the storage path: raw/raw/CHANNEL/FILENAME
        # But the filename has underscores that should be slashes in the storage path
        if clip_id.startswith('raw_'):
            # Remove 'raw_' prefix
            remaining = clip_id[4:]
            # Split by the first underscore to get channel and filename
            parts = remaining.split('_', 1)
            if len(parts) == 2:
                channel = parts[0]
                filename = parts[1]
                # The filename structure is: live-CHANNEL-TIMESTAMP_YYYYMMDD_segment_TIMESTAMP.mp4
                # We need to convert specific underscores to slashes:
                # live-CHANNEL-TIMESTAMP/YYYYMMDD/segment_TIMESTAMP.mp4
                # Split by underscores but keep the last part (segment_TIMESTAMP.mp4) intact
                filename_parts = filename.split('_')
                if len(filename_parts) >= 3:
                    # Reconstruct: PART1/PART2/segment_TIMESTAMP.mp4
                    storage_filename = f"{filename_parts[0]}/{filename_parts[1]}/{filename_parts[2]}_{filename_parts[3]}"
                else:
                    # Fallback: replace all underscores
                    storage_filename = filename.replace('_', '/')
                # Construct the storage path: raw/raw/CHANNEL/FILENAME
                storage_path = f"raw/raw/{channel}/{storage_filename}"
            else:
                # Fallback: use the entire remaining string as filename
                storage_path = f"raw/raw/{remaining}"
        else:
            # Fallback: use the clip_id as is
            storage_path = f"raw/raw/{clip_id}"
        
        # Get the public URL from Supabase storage
        # The bucket is "raw" and the storage_path already contains "raw/raw/"
        # So we need to remove the first "raw/" from storage_path
        if storage_path.startswith("raw/"):
            storage_path = storage_path[4:]  # Remove the first "raw/"
        
        bucket = "raw"
        video_url = supabase.storage.from_(bucket).get_public_url(storage_path)
        
        logger.info(f"Attempting to download from URL: {video_url}")
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        temp_path = temp_file.name
        temp_file.close()
        
        # Download video
        response = requests.get(video_url, stream=True)
        response.raise_for_status()
        
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Downloaded video from {video_url} to: {temp_path}")
        return temp_path
        
    except Exception as e:
        logger.error(f"Failed to download video {clip_id}: {e}")
        raise Exception(f"Video download failed: {str(e)}")


@celery_app.task
def retry_failed_posts():
    """
    Retry failed posts that haven't exceeded max retries.
    Useful for manual retry of failed uploads.
    """
    try:
        logger.info("Retrying failed posts...")
        
        supabase = get_client()
        
        # Find failed posts that can be retried
        failed_response = supabase.table('posting_queue').select('*').eq('status', 'failed').lt('retry_count', 3).execute()
        
        if not failed_response.data:
            logger.info("No failed posts available for retry")
            return
        
        logger.info(f"Found {len(failed_response.data)} failed posts for retry")
        
        # Queue each failed post for retry
        for queue_item in failed_response.data:
            post_to_social_media.delay(queue_item['id'])
            logger.info(f"Queued failed post for retry: {queue_item['id']}")
        
    except Exception as e:
        logger.error(f"Error retrying failed posts: {e}")


# Task monitoring and health checks
@celery_app.task
def health_check():
    """Health check task to verify Celery is working."""
    return {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'worker_count': len(celery_app.control.inspect().active())
    }
