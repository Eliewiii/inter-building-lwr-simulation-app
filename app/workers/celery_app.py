import os

from celery import Celery
from kombu import Queue

# 1. Initialize the Celery App
# The 'include' list tells Celery exactly which files to scan for @shared_task decorators.
celery_app = Celery(
    "simulation_pipeline",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    include=[
        "app.workers.tasks_preproc",
        "app.workers.tasks_vf",
        "app.workers.tasks_lwr_pre",
        "app.workers.tasks_lwr_sim",
        "app.workers.tasks_post",
    ],
)

# 2. Queue Configuration (The Fast/Slow Lanes)
# Explicitly define the queues so your Docker containers can bind to them.
celery_app.conf.task_queues = (
    Queue("fast_lane"),
    Queue("slow_lane"),
)

# Default routing: If a task gets fired without a specific queue, default to the slow lane.
celery_app.conf.task_default_queue = "slow_lane"

# 3. High-Performance / Heavy Compute Tweaks
celery_app.conf.update(
    # VERY IMPORTANT FOR R&D:
    # By default, a Celery worker reserves 4 tasks at a time per CPU core.
    # For heavy spatial/thermal tasks, this will cause memory thrashing.
    # Setting this to 1 forces the worker to only pull one task at a time.
    worker_prefetch_multiplier=1,
    # Do not tell Redis the task is "done" until the Python function actually returns.
    # If a worker container runs out of RAM and is killed by the OS mid-calculation,
    # the task will remain in Redis and can be retried automatically.
    task_acks_late=True,
    # State tracking
    task_track_started=True,
    # We are passing pure Pydantic/JSON dictionaries around, nothing else.
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Do not bloat Redis with old task results. Clear them after 24 hours.
    result_expires=86400,
)
