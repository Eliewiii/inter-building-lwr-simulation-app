"""Configuration engine for distributed Celery execution profiles and dynamic queue topologies."""

import os

from celery import Celery
from kombu import Queue

from app.config import settings
from app.workers import tasks

# 1. Initialize the Celery App Context
# Dynamically extract the underlying module string location to avoid hardcoded string tracking.
celery_app = Celery(
    "simulation_pipeline",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    include=[tasks.__name__],  # Resolves automatically to "app.workers.tasks"
)

# 2. Queue Configuration (The Fast/Slow Lanes)
celery_app.conf.task_queues = (
    Queue(settings.celery_fast_lane_queue),
    Queue(settings.celery_slow_lane_queue),
)

# Enforce the fallback queue directly from application environments
celery_app.conf.task_default_queue = settings.celery_slow_lane_queue

# 3. High-Performance / Heavy Compute Architectural Tuning
celery_app.conf.update(
    # Disable pre-fetching boundaries to prevent memory thrashing on heavy numerical processes.
    worker_prefetch_multiplier=1,
    # Enforce late acknowledgments so dropped worker instances trigger automatic message requeuing.
    task_acks_late=True,
    # Track runtime worker initializations for monitoring visibility
    task_track_started=True,
    # Strict serialization formatting definitions
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Prune historical results from backend data stores after 24 hours
    result_expires=86400,
)
