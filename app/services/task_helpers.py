"""Context manager tracking state boundaries and prerequisite chains for distributed simulation tasks."""

from contextlib import contextmanager
from typing import Generator

from app.schemas import ExecutionState, PipelinePhase, SimulationManifest
from app.services.orchestrator import PIPELINE_TOPOLOGY
from app.services.state_manager import get_manifest, update_manifest


@contextmanager
def manage_task_state(
    user_id: str, sim_id: str, current_phase: PipelinePhase
) -> Generator[SimulationManifest, None, None]:
    """Manage lifecycle state transitions and execution guards for async workers.

    Coordinates verification of foundational pipeline steps, handles transition
    to operational states, ensures serialization of workspaces on failure boundaries,
    and isolates exceptions to protect state tracking integrity.

    Args:
        user_id (str): Unique identifier of the user owning the workspace.
        sim_id (str): Unique identifier of the targeted simulation entity.
        current_phase (PipelinePhase): The active topological phase executing
            under this context manager framework.

    Raises:
        RuntimeError: Raised if prerequisite phase status evaluation fails or is
            not marked as completed in the workspace tracking manifest.
        Exception: Rethrows any unhandled exceptions caught during computational block
            execution to ensure appropriate worker orchestration tracking.

    Yields:
        Generator[SimulationManifest, None, None]: The freshly synchronized operational state
            manifest dictionary structure for safe workspace attribute modification.
    """
    # 1. Setup & Load
    manifest = get_manifest(user_id, sim_id)

    # 2. Extract Prerequisite safely from the PIPELINE_TOPOLOGY tuple matrix
    required_previous = next(
        (prereq for phase, _, prereq in PIPELINE_TOPOLOGY if phase == current_phase), None
    )

    # 3. Defense in Depth: Verify Prerequisite
    if required_previous is not None:
        if manifest.phase_statuses.get(required_previous) != ExecutionState.COMPLETED:
            manifest.phase_statuses[current_phase] = ExecutionState.FAILED
            manifest.error_message = (
                f"Worker rejected task: Prerequisite '{required_previous.value}' not completed."
            )
            update_manifest(user_id, sim_id, manifest)
            raise RuntimeError(manifest.error_message)

    # 4. Transition to Running
    manifest.phase_statuses[current_phase] = ExecutionState.RUNNING
    update_manifest(user_id, sim_id, manifest)

    try:
        # 5. Yield the manifest to the core task logic
        yield manifest

        # 6. On Success: Teardown & Complete
        manifest.phase_statuses[current_phase] = ExecutionState.COMPLETED
        # Clear out any stale errors from previous failed attempts if this retry succeeds
        manifest.error_message = None
        update_manifest(user_id, sim_id, manifest)

    except Exception as e:
        # 7. On Crash: Auto-Fail and log the traceback details
        manifest.phase_statuses[current_phase] = ExecutionState.FAILED
        manifest.error_message = f"{current_phase.value} failed: {str(e)}"
        update_manifest(user_id, sim_id, manifest)
        raise  # Rethrow so Celery handles task tracking and acks_late states properly
