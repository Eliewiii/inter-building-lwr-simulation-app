"""Unit tests verifying orchestration routing logic, structural guards, and Celery workflows."""

from unittest.mock import MagicMock, patch

import pytest

from app.schemas import ExecutionState, PipelinePhase, PipelineRunRequest, SimulationManifest
from app.services.orchestrator import (
    _extract_ordered_phases,
    _validate_execution_request,
    schedule_pipeline,
)


@pytest.fixture
def run_request() -> PipelineRunRequest:
    """Generate a mock request with standard preprocessing and view factor steps enabled."""
    return PipelineRunRequest(
        run_pre_processing=True,
        run_vf_computation=True,
        run_lwr_pre_processing=False,
        run_lwr_simulation=False,
        run_post_processing=False,
        priority_queue=False,
    )


# =====================================================================
# INTERNAL WORKFLOW UTILITY TESTS
# =====================================================================


def test_extract_ordered_phases_filters_by_request_toggles(
    run_request: PipelineRunRequest,
) -> None:
    """Extract requested phases from the topology matrix sequentially based on toggles.

    Evaluates the request boolean configuration fields against the execution matrix to ensure
    that active steps are selected and arranged in strict pipeline order.
    """
    phases = _extract_ordered_phases(run_request)
    assert phases == [PipelinePhase.PRE_PROCESSING, PipelinePhase.VF_COMPUTATION]


def test_validate_request_raises_error_if_no_phases_selected() -> None:
    """Raise a ValueError if the extracted ordered phase array is empty.

    Ensures that a user cannot submit an empty payload block that contains zero active execution
    flags to prevent dead worker execution requests.
    """
    manifest = MagicMock(spec=SimulationManifest)
    with pytest.raises(ValueError, match="No simulation phases were selected"):
        _validate_execution_request(manifest, [])


def test_validate_request_blocks_concurrency_on_active_tasks(
    sample_manifest: SimulationManifest,
) -> None:
    """Raise a ValueError if any phase in the workspace manifest is currently processing.

    Scans the data store status dictionary to ensure a workspace lock is enforced if an existing
    asynchronous process is in a PENDING or RUNNING operational boundary.
    """
    sample_manifest.phase_statuses[PipelinePhase.PRE_PROCESSING] = ExecutionState.RUNNING
    ordered_phases = [PipelinePhase.VF_COMPUTATION]

    with pytest.raises(ValueError, match="Simulation workspace is locked"):
        _validate_execution_request(sample_manifest, ordered_phases)


def test_validate_request_enforces_topological_prerequisites(
    sample_manifest: SimulationManifest,
) -> None:
    """Raise a ValueError if the foundational prerequisite step for the entry phase is uncompleted.

    Ensures pipeline structural continuity by checking that downstream steps (like view factors)
    cannot be kicked off if their preceding requirements are missing or failed.
    """
    # 1. Clear out all default statuses to guarantee the concurrency guard passes cleanly
    sample_manifest.phase_statuses = {
        PipelinePhase.PRE_PROCESSING: ExecutionState.FAILED,
        PipelinePhase.VF_COMPUTATION: ExecutionState.UNSTARTED,
    }
    ordered_phases = [PipelinePhase.VF_COMPUTATION]

    # 2. Assert that the prerequisite validation failure is successfully intercepted
    with pytest.raises(ValueError, match="foundational step .* must be successfully completed"):
        _validate_execution_request(sample_manifest, ordered_phases)


# =====================================================================
# CENTRAL SCHEDULER TESTS (schedule_pipeline)
# =====================================================================


@patch("app.services.orchestrator._dispatch_chain")
@patch("app.services.orchestrator.update_manifest")
@patch("app.services.orchestrator.get_manifest")
def test_schedule_pipeline_mutates_manifest_and_dispatches_chain(
    mock_get: MagicMock,
    mock_update: MagicMock,
    mock_dispatch: MagicMock,
    sample_manifest: SimulationManifest,
    run_request: PipelineRunRequest,
) -> None:
    """Assemble a sequential Celery canvas chain and update database status markers to pending.

    Ensures that targeted phases transition to PENDING instantly to acquire the workspace lock,
    verifies that context payloads are injected into the head link, and confirms the canvas
    object passes downstream to the message broker.
    """
    sample_manifest.phase_statuses = {
        PipelinePhase.PRE_PROCESSING: ExecutionState.UNSTARTED,
        PipelinePhase.VF_COMPUTATION: ExecutionState.UNSTARTED,
    }
    mock_get.return_value = sample_manifest
    mock_dispatch.return_value = "mock_chain_parent_id"

    chain_id = schedule_pipeline("user_99", "sim_baseline", run_request)

    # Verify tracking indicators were flushed to database before broker transmission
    assert sample_manifest.phase_statuses[PipelinePhase.PRE_PROCESSING] == ExecutionState.PENDING
    assert sample_manifest.phase_statuses[PipelinePhase.VF_COMPUTATION] == ExecutionState.PENDING
    mock_update.assert_called_once_with("user_99", "sim_baseline", sample_manifest)

    # Verify execution pipeline structural characteristics passed down to applying layer
    assert chain_id == "mock_chain_parent_id"
    mock_dispatch.assert_called_once()
    celery_chain = mock_dispatch.call_args[0][0]

    # Validate signature links: The lead task must possess the full TaskContext payload
    assert len(celery_chain.tasks) == 2
    assert celery_chain.tasks[0].args == ({"user_id": "user_99", "simulation_id": "sim_baseline"},)
    assert celery_chain.tasks[1].args == ()  # Chained tasks pull inputs sequentially from runtime
