"""Celery execution engine.

It handles state tracking wrappers, architectural routing shells, and transaction boundaries.
"""

from contextlib import contextmanager
from typing import Any, Callable, Generator

from celery import shared_task

from app.core import pipeline_logic
from app.schemas import ExecutionState, PipelinePhase, SimulationManifest, TaskContext
from app.services.state_manager import get_manifest, update_manifest

# =====================================================================
# SYSTEM STRUCTURAL TOPOLOGY (Isolated from Execution Function Imports)
# =====================================================================
PIPELINE_TOPOLOGY = (
    (PipelinePhase.PRE_PROCESSING, PipelinePhase.PRE_PROCESSING, None),
    (PipelinePhase.VF_COMPUTATION, PipelinePhase.VF_COMPUTATION, PipelinePhase.PRE_PROCESSING),
    (
        PipelinePhase.LWR_PRE_PROCESSING,
        PipelinePhase.LWR_PRE_PROCESSING,
        PipelinePhase.VF_COMPUTATION,
    ),
    (PipelinePhase.LWR_SIMULATION, PipelinePhase.LWR_SIMULATION, PipelinePhase.LWR_PRE_PROCESSING),
    (PipelinePhase.POST_PROCESSING, PipelinePhase.POST_PROCESSING, PipelinePhase.LWR_SIMULATION),
)


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

    # 3. Defense in Depth: Verify Prerequisite and that the task is pending
    if required_previous is not None:
        if manifest.phase_statuses.get(required_previous) != ExecutionState.COMPLETED:
            manifest.phase_statuses[current_phase] = ExecutionState.FAILED
            manifest.error_message = (
                f"Worker rejected task: Prerequisite '{required_previous.value}' not completed."
            )
            update_manifest(user_id, sim_id, manifest)
            raise RuntimeError(manifest.error_message)
    current_task_state = manifest.phase_statuses.get(current_phase)
    if current_task_state is None:
        raise KeyError(
            f"System Integrity Bug: Phase '{current_phase.value}' does not exist "
            f"in the workspace manifest status matrix."
        )

    if current_task_state != ExecutionState.PENDING:
        raise RuntimeError(
            f"Worker rejected executing '{current_phase.value}': "
            f"Expected state 'pending', found '{current_task_state.value}'."
        )

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


def execute_pipeline_task(
    context_data: dict[str, Any],
    phase: PipelinePhase,
    logic_execution_block: Callable[[SimulationManifest], None],
) -> dict[str, Any]:
    """Execute computational step operations safely within standard manifest tracking boundaries.

    Parses runtime contexts, establishes transaction parameters using the lifecycle
    context manager, runs the isolated domain logic block, and serializes state schemas.

    Args:
        context_data (dict[str, Any]): Raw unstructured task context parameters transmitted
            via the broker queue network.
        phase (PipelinePhase): The active execution stage boundary descriptor.
        logic_execution_block (Callable[[SimulationManifest], None]): Functional algorithm
            implementation isolated from the orchestrator envelope.

    Returns:
        dict[str, Any]: Validated serializable payload structure required for sequential
            chain links.
    """
    # 1. Initialize data schema boundaries at entry layer
    task_context = TaskContext(**context_data)

    # 2. Enforce transaction state tracking constraints
    with manage_task_state(task_context.user_id, task_context.simulation_id, phase) as manifest:
        # 3. Transfer execution control to the isolated algorithm module
        logic_execution_block(manifest)

    return task_context.model_dump()


# =====================================================================
# CELERY SYSTEM INFRASTRUCTURE ENTRY POINTS (Thin Routing Shells)
# =====================================================================


@shared_task(bind=True)
def run_pre_processing(self, context: dict[str, Any]) -> dict[str, Any]:
    """Execute raw system data ingestion and foundational mapping diagnostics."""
    return execute_pipeline_task(
        context_data=context,
        phase=PipelinePhase.PRE_PROCESSING,
        logic_execution_block=pipeline_logic.compute_pre_processing,
    )


@shared_task(bind=True)
def run_vf_computation(self, context: dict[str, Any]) -> dict[str, Any]:
    """Execute architectural sky view factor geometric projection math."""
    return execute_pipeline_task(
        context_data=context,
        phase=PipelinePhase.VF_COMPUTATION,
        logic_execution_block=pipeline_logic.compute_view_factors,
    )


@shared_task(bind=True)
def run_lwr_pre_processing(self, context: dict[str, Any]) -> dict[str, Any]:
    """Execute long-wave radiation matrix initialization structures."""
    return execute_pipeline_task(
        context_data=context,
        phase=PipelinePhase.LWR_PRE_PROCESSING,
        logic_execution_block=pipeline_logic.compute_lwr_pre_processing,
    )


@shared_task(bind=True)
def run_lwr_simulation(self, context: dict[str, Any]) -> dict[str, Any]:
    """Execute parallelized iterative inter-building radiation exchange numerical solver."""
    return execute_pipeline_task(
        context_data=context,
        phase=PipelinePhase.LWR_SIMULATION,
        logic_execution_block=pipeline_logic.compute_lwr_simulation,
    )


@shared_task(bind=True)
def run_post_processing(self, context: dict[str, Any]) -> dict[str, Any]:
    """Execute output rendering conversions and metric storage exports."""
    return execute_pipeline_task(
        context_data=context,
        phase=PipelinePhase.POST_PROCESSING,
        logic_execution_block=pipeline_logic.compute_post_processing,
    )
