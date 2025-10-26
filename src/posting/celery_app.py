"""
Celery configuration for background job processing.
Handles social media posting tasks and scheduled posts.
"""

import os
from pathlib import Path
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent.parent / '.env')

# Create Celery app
celery_app = Celery(
    'clipping_automation',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379')
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max per task
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
)

# Periodic tasks configuration
celery_app.conf.beat_schedule = {
    'process-scheduled-posts': {
        'task': 'src.posting.tasks.process_scheduled_posts',
        'schedule': crontab(minute='*'),  # Run every minute
    },
    'cleanup-old-queue-items': {
        'task': 'src.posting.tasks.cleanup_old_queue_items',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
    },
}

# Task routing - use default queue for simplicity
# celery_app.conf.task_routes = {
#     'src.posting.tasks.post_to_social_media': {'queue': 'social_posting'},
#     'src.posting.tasks.process_scheduled_posts': {'queue': 'scheduler'},
#     'src.posting.tasks.cleanup_old_queue_items': {'queue': 'maintenance'},
# }

# Error handling
celery_app.conf.task_annotations = {
    'src.posting.tasks.post_to_social_media': {
        'rate_limit': '10/m',  # Max 10 posts per minute
        'max_retries': 3,
        'default_retry_delay': 60,  # 1 minute
    }
}

# Import tasks to register them with Celery
# This must be done after celery_app is created
from . import tasks  # noqa: F401

if __name__ == '__main__':
    celery_app.start()
