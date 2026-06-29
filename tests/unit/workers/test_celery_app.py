"""Unit tests verifying Celery application instance configurations."""

from kombu import Queue

from app.config import settings
from app.workers.celery_app import celery_app


def test_celery_app_initialization_metadata() -> None:
    """Verify that the central Celery application instance configures the correct metadata."""
    # Assert the primary app namespace matches your targeted configuration name
    assert celery_app.main == "simulation_pipeline"


def test_celery_queue_topology_and_routing_lanes() -> None:
    """Verify that the dynamic fast-lane and slow-lane queue boundaries are instantiated correctly.

    Ensures that custom environmental settings map cleanly onto the underlying Kombu
    Queue structures and that fallback default lanes are securely set.
    """
    # 1. Extract the active queue configuration map
    active_queues = celery_app.conf.task_queues
    assert active_queues is not None

    # 2. Map structural queue tracking names from the instantiated tuples
    queue_names = {queue.name for queue in active_queues if isinstance(queue, Queue)}

    # 3. Assert both dynamic environmental boundaries are registered securely
    assert settings.celery_fast_lane_queue in queue_names
    assert settings.celery_slow_lane_queue in queue_names

    # 4. Verify the fallback default channel aligns with your environment expectations
    assert celery_app.conf.task_default_queue == settings.celery_slow_lane_queue


def test_celery_high_performance_compute_tweaks() -> None:
    """Verify that heavy compute and memory-safe architectural settings are enforced.

    Asserts that the prefetch multiplier blocks queue thrashing and that late
    acknowledgments are active to secure automatic task retries on resource exhaustion crashes.
    """
    # 1. Assert prefetch multiplier is exactly 1 to isolate execution per worker core
    assert celery_app.conf.worker_prefetch_multiplier == 1

    # 2. Assert late acknowledgments are active to enforce transactional durability bounds
    assert celery_app.conf.task_acks_late is True

    # 3. Assert worker active state visibility parameters are running
    assert celery_app.conf.task_track_started is True


def test_celery_serialization_and_expiry_boundaries() -> None:
    """Verify strict JSON serialization constraints and database results expiration timers."""
    # 1. Assert secure, lightweight JSON data transport formatting is enforced globally
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert "json" in celery_app.conf.accept_content

    # 2. Assert historical task metadata records expire accurately after 24 hours (86,400 seconds)
    assert celery_app.conf.result_expires == 86400
