"""Celery execution engine handling state tracking wrappers and architectural routing shells."""

from typing import Any, Callable

from celery import shared_task

from app.core import pipeline_logic
from app.schemas import PipelinePhase, SimulationManifest, TaskContext
from app.services.task_helpers import manage_task_state


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
