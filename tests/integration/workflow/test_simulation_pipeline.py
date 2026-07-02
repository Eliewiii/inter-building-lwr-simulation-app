"""Integration tests verifying multi-phase simulation orchestration and task execution."""

from unittest.mock import MagicMock, patch

import pytest

from app.schemas import ExecutionState, PipelinePhase, PipelineRunRequest, SimulationManifest
from app.services.orchestrator import schedule_pipeline

pytestmark = [pytest.mark.integration]


@pytest.fixture
def configure_eager_celery():
    """Force Celery to execute tasks synchronously on the local calling thread.

    Bypasses the asynchronous broker to allow sequential pipeline tracing within the
    active testing process context.
    """
    from app.workers.celery_app import celery_app

    original_eager = celery_app.conf.task_always_eager
    celery_app.conf.task_always_eager = True
    yield
    celery_app.conf.task_always_eager = original_eager


def test_orchestrator_to_worker_chain_integration(
    sample_manifest: SimulationManifest,
    request: pytest.FixtureRequest,
) -> None:
    """Execute a scheduled orchestration request through sequential worker layers down to logic.

    Verifies that a successful multi-phase simulation transitions targeted phases to pending,
    passes data sequentially through the task layers, executes core logic, and updates the
    workspace manifest to completed.
    """
    sample_manifest.phase_statuses = {
        PipelinePhase.PRE_PROCESSING: ExecutionState.UNSTARTED,
        PipelinePhase.VF_COMPUTATION: ExecutionState.UNSTARTED,
    }
    state_history = []

    def save_state_spy(user_id: str, sim_id: str, manifest: SimulationManifest) -> None:
        state_history.append(dict(manifest.phase_statuses))

    # Explicitly patch execution namespaces directly where the functions are consumed
    with (
        patch("app.services.orchestrator.get_manifest", return_value=sample_manifest),
        patch("app.services.orchestrator.update_manifest", side_effect=save_state_spy),
        patch("app.workers.tasks.get_manifest", return_value=sample_manifest),
        patch("app.workers.tasks.update_manifest", side_effect=save_state_spy),
        patch("app.core.pipeline_logic.compute_pre_processing") as mock_pre_logic,
        patch("app.core.pipeline_logic.compute_view_factors") as mock_vf_logic,
    ):
        # Dynamically trigger eager worker registration within the active mock environment
        request.getfixturevalue("configure_eager_celery")

        request_payload = PipelineRunRequest(
            run_pre_processing=True,
            run_vf_computation=True,
            run_lwr_pre_processing=False,
            run_lwr_simulation=False,
            run_post_processing=False,
            priority_queue=False,
        )

        # Trigger execution
        chain_id = schedule_pipeline(
            user_id=sample_manifest.user_id,
            sim_id=sample_manifest.simulation_id,
            request=request_payload,
        )

        # Assert full workflow execution integrity boundaries
        assert chain_id is not None
        mock_pre_logic.assert_called_once()
        mock_vf_logic.assert_called_once()

        # Validate chronological lifecycle mutations
        assert state_history[0][PipelinePhase.PRE_PROCESSING] == ExecutionState.PENDING
        assert state_history[0][PipelinePhase.VF_COMPUTATION] == ExecutionState.PENDING
        assert (
            sample_manifest.phase_statuses[PipelinePhase.PRE_PROCESSING] == ExecutionState.COMPLETED
        )
        assert (
            sample_manifest.phase_statuses[PipelinePhase.VF_COMPUTATION] == ExecutionState.COMPLETED
        )


def test_pipeline_stops_and_saves_error_on_partial_failure(
    sample_manifest: SimulationManifest,
    request: pytest.FixtureRequest,
) -> None:
    """Verify that a mid-pipeline execution crash gracefully halts downstream tasks and saves state.

    Ensures that an internal processing failure is caught by the tracking scaffolding,
    transitions the broken phase to a failed state, updates error logs, and prevents the
    remaining workflow dependencies from continuing.
    """
    sample_manifest.phase_statuses = {
        PipelinePhase.PRE_PROCESSING: ExecutionState.UNSTARTED,
        PipelinePhase.VF_COMPUTATION: ExecutionState.UNSTARTED,
    }
    state_history = []

    def save_state_spy(user_id: str, sim_id: str, manifest: SimulationManifest) -> None:
        state_history.append(dict(manifest.phase_statuses))

    # Inject execution variables: phase 1 passes, phase 2 throws an explicit runtime error
    mock_pre_logic = MagicMock(return_value=True)
    mock_vf_logic = MagicMock(side_effect=ZeroDivisionError("Matrix calculation failure"))

    with (
        patch("app.services.orchestrator.get_manifest", return_value=sample_manifest),
        patch("app.services.orchestrator.update_manifest", side_effect=save_state_spy),
        patch("app.workers.tasks.get_manifest", return_value=sample_manifest),
        patch("app.workers.tasks.update_manifest", side_effect=save_state_spy),
        patch("app.core.pipeline_logic.compute_pre_processing", mock_pre_logic),
        patch("app.core.pipeline_logic.compute_view_factors", mock_vf_logic),
    ):
        request.getfixturevalue("configure_eager_celery")

        request_payload = PipelineRunRequest(
            run_pre_processing=True,
            run_vf_computation=True,
            run_lwr_pre_processing=False,
            run_lwr_simulation=False,
            run_post_processing=False,
            priority_queue=False,
        )

        # Trigger execution (Worker framework handles exception internally to save state)
        chain_id = schedule_pipeline(
            user_id=sample_manifest.user_id,
            sim_id=sample_manifest.simulation_id,
            request=request_payload,
        )

        # Assert functional block execution results
        assert chain_id is not None
        mock_pre_logic.assert_called_once()
        mock_vf_logic.assert_called_once()

        # Validate that upstream changes are saved while downstream failures are logged cleanly
        assert (
            sample_manifest.phase_statuses[PipelinePhase.PRE_PROCESSING] == ExecutionState.COMPLETED
        )
        assert sample_manifest.phase_statuses[PipelinePhase.VF_COMPUTATION] == ExecutionState.FAILED

        assert sample_manifest.error_message is not None
        assert "Matrix calculation failure" in sample_manifest.error_message
