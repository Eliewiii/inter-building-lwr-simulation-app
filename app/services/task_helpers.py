from contextlib import contextmanager

from app.schemas import ExecutionState, PipelinePhase
from app.services.orchestrator import PREREQUISITES
from app.services.state_manager import get_manifest, update_manifest


@contextmanager
def manage_task_state(user_id: str, sim_id: str, current_phase: PipelinePhase):
    """
    A generic context manager for Celery tasks to handle state transitions,
    prerequisite verification, and error catching safely.
    """
    # 1. Setup & Load
    manifest = get_manifest(user_id, sim_id)

    # 2. Defense in Depth: Verify Prerequisite
    required_previous = PREREQUISITES.get(current_phase)
    if required_previous and manifest.phase_statuses[required_previous] != ExecutionState.COMPLETED:
        # If we fail here, we don't even try to run the math
        manifest.phase_statuses[current_phase] = ExecutionState.FAILED
        manifest.error_message = (
            f"Worker rejected task: Prerequisite '{required_previous.value}' not completed."
        )
        update_manifest(user_id, sim_id, manifest)
        raise RuntimeError(manifest.error_message)

    # 3. Transition to Running
    manifest.phase_statuses[current_phase] = ExecutionState.RUNNING
    update_manifest(user_id, sim_id, manifest)

    try:
        # 4. Yield the manifest to the core task logic
        yield manifest

        # 5. On Success: Teardown & Complete
        manifest.phase_statuses[current_phase] = ExecutionState.COMPLETED
        update_manifest(user_id, sim_id, manifest)

    except Exception as e:
        # 6. On Crash: Auto-Fail and log
        manifest.phase_statuses[current_phase] = ExecutionState.FAILED
        manifest.error_message = f"{current_phase.value} failed: {str(e)}"
        update_manifest(user_id, sim_id, manifest)
        raise  # Rethrow so Celery knows the task failed
