"""Unit tests verifying Celery routing, context management, and execution."""

from unittest.mock import MagicMock, patch

import pytest

from app.schemas import ExecutionState, PipelinePhase, SimulationManifest
from app.workers.tasks import (
    execute_pipeline_task,
    manage_task_state,
    run_lwr_pre_processing,
    run_lwr_simulation,
    run_post_processing,
    run_pre_processing,
    run_vf_computation,
)

# =====================================================================
# CONTEXT MANAGER TESTS (manage_task_state)
# =====================================================================


@patch("app.workers.tasks.update_manifest")
@patch("app.workers.tasks.get_manifest")
def test_manage_task_state_success_lifecycle(
    mock_get: MagicMock,
    mock_update: MagicMock,
    sample_manifest: SimulationManifest,
) -> None:
    """Verify state transitions from RUNNING to COMPLETED on success.

    Ensures that the context manager loads the manifest from storage, transitions the target
    phase to RUNNING on entry, yields control to the worker logic block, and conclusively
    marks the phase as COMPLETED upon a successful exit.
    """
    sample_manifest.phase_statuses = {
        PipelinePhase.PRE_PROCESSING: ExecutionState.COMPLETED,
        PipelinePhase.VF_COMPUTATION: ExecutionState.PENDING,
    }
    mock_get.return_value = sample_manifest

    phase = PipelinePhase.VF_COMPUTATION
    with manage_task_state(
        sample_manifest.user_id, sample_manifest.simulation_id, phase
    ) as manifest:
        assert manifest.phase_statuses[phase] == ExecutionState.RUNNING

    assert sample_manifest.phase_statuses[phase] == ExecutionState.COMPLETED
    assert sample_manifest.error_message is None
    assert mock_update.call_count == 2


@patch("app.workers.tasks.update_manifest")
@patch("app.workers.tasks.get_manifest")
def test_manage_task_state_prerequisite_failure_guard(
    mock_get: MagicMock,
    mock_update: MagicMock,
    sample_manifest: SimulationManifest,
) -> None:
    """Verify execution aborts immediately if prerequisites are unfulfilled.

    Evaluates the state machine's defensive interception. If a prerequisite step in the
    pipeline topology is missing, unstarted, or failed, the context manager must immediately
    mark the current task as FAILED, log an error, and raise a RuntimeError before yielding.
    """
    sample_manifest.phase_statuses = {
        PipelinePhase.PRE_PROCESSING: ExecutionState.FAILED,
        PipelinePhase.VF_COMPUTATION: ExecutionState.PENDING,
    }
    mock_get.return_value = sample_manifest

    phase = PipelinePhase.VF_COMPUTATION
    with pytest.raises(RuntimeError, match="Worker rejected task: Prerequisite"):
        with manage_task_state(sample_manifest.user_id, sample_manifest.simulation_id, phase):
            pytest.fail("Context manager yielded control on failed prereq.")

    assert sample_manifest.phase_statuses[phase] == ExecutionState.FAILED
    assert "not completed" in str(sample_manifest.error_message)
    mock_update.assert_called_once_with(
        sample_manifest.user_id, sample_manifest.simulation_id, sample_manifest
    )


@patch("app.workers.tasks.update_manifest")
@patch("app.workers.tasks.get_manifest")
def test_manage_task_state_exception_isolation(
    mock_get: MagicMock,
    mock_update: MagicMock,
    sample_manifest: SimulationManifest,
) -> None:
    """Verify internal crashes trigger auto-fail persistence states.

    Ensures that any unhandled runtime exceptions arising inside the execution block are
    caught by the teardown layer. The context manager must persist the failure state to the
    data store, then cleanly re-raise the error to let the Celery broker track the crash.
    """
    sample_manifest.phase_statuses = {
        PipelinePhase.PRE_PROCESSING: ExecutionState.COMPLETED,
        PipelinePhase.VF_COMPUTATION: ExecutionState.PENDING,
    }
    mock_get.return_value = sample_manifest

    phase = PipelinePhase.VF_COMPUTATION
    with pytest.raises(ZeroDivisionError):
        with manage_task_state(sample_manifest.user_id, sample_manifest.simulation_id, phase):
            _ = 1 / 0

    assert sample_manifest.phase_statuses[phase] == ExecutionState.FAILED
    assert "division by zero" in str(sample_manifest.error_message)
    assert mock_update.call_count == 2


# =====================================================================
# TASK EXECUTION RUNNER & ROUTING ENTRY POINT TESTS
# =====================================================================


@patch("app.workers.tasks.update_manifest")
@patch("app.workers.tasks.get_manifest")
def test_execute_pipeline_task_success_flow(
    mock_get: MagicMock,
    mock_update: MagicMock,
    sample_manifest: SimulationManifest,
) -> None:
    """Verify execute_pipeline_task coordinates context lifecycle.

    Ensures that the primary execution wrapper deserializes incoming raw broker dictionaries
    into a validated TaskContext schema, handles the transaction boundaries via the context
    manager, triggers the domain logic, and serializes the context state for Celery.
    """
    sample_manifest.phase_statuses = {
        PipelinePhase.PRE_PROCESSING: ExecutionState.COMPLETED,
        PipelinePhase.VF_COMPUTATION: ExecutionState.PENDING,
    }
    mock_get.return_value = sample_manifest

    mock_logic_block = MagicMock()
    context_data = {
        "user_id": sample_manifest.user_id,
        "simulation_id": sample_manifest.simulation_id,
    }

    phase = PipelinePhase.VF_COMPUTATION
    result = execute_pipeline_task(
        context_data=context_data,
        phase=phase,
        logic_execution_block=mock_logic_block,
    )

    mock_logic_block.assert_called_once_with(sample_manifest)
    assert sample_manifest.phase_statuses[phase] == ExecutionState.COMPLETED
    assert result["simulation_id"] == sample_manifest.simulation_id


@patch("app.workers.tasks.execute_pipeline_task")
def test_celery_routing_shells_forward_correct_parameters(
    mock_execute: MagicMock,
) -> None:
    """Verify routing shells pass correct parameters to executor.

    Asserts that all five public-facing shared_task asynchronous entry points accurately
    resolve their targeted PipelinePhase descriptors and bind to the correct isolated functional
    algorithm pointers inside app.core.pipeline_logic.
    """
    mock_context = {"user_id": "user_test", "simulation_id": "sim_test"}
    logic_mod = pytest.importorskip("app.core.pipeline_logic")

    # 1. Pre-Processing
    run_pre_processing(mock_context)
    mock_execute.assert_called_with(
        context_data=mock_context,
        phase=PipelinePhase.PRE_PROCESSING,
        logic_execution_block=logic_mod.compute_pre_processing,
    )

    # 2. View Factors
    run_vf_computation(mock_context)
    mock_execute.assert_called_with(
        context_data=mock_context,
        phase=PipelinePhase.VF_COMPUTATION,
        logic_execution_block=logic_mod.compute_view_factors,
    )

    # 3. LWR Pre-Processing
    run_lwr_pre_processing(mock_context)
    mock_execute.assert_called_with(
        context_data=mock_context,
        phase=PipelinePhase.LWR_PRE_PROCESSING,
        logic_execution_block=logic_mod.compute_lwr_pre_processing,
    )

    # 4. LWR Simulation
    run_lwr_simulation(mock_context)
    mock_execute.assert_called_with(
        context_data=mock_context,
        phase=PipelinePhase.LWR_SIMULATION,
        logic_execution_block=logic_mod.compute_lwr_simulation,
    )

    # 5. Post-Processing
    run_post_processing(mock_context)
    mock_execute.assert_called_with(
        context_data=mock_context,
        phase=PipelinePhase.POST_PROCESSING,
        logic_execution_block=logic_mod.compute_post_processing,
    )


@patch("app.workers.tasks.update_manifest")
@patch("app.workers.tasks.get_manifest")
def test_execute_pipeline_task_aborts_on_raised_exception(
    mock_get: MagicMock,
    mock_update: MagicMock,
    sample_manifest: SimulationManifest,
) -> None:
    """Verify algorithm exceptions bubble up to broker while failing state.

    Confirms that execution-level runtime exceptions inside core mathematical blocks are not
    silently swallowed by the task loop runner wrapper, forcing the state envelope into an
    explicit FAILED marker before re-raising.
    """
    sample_manifest.phase_statuses = {
        PipelinePhase.PRE_PROCESSING: ExecutionState.COMPLETED,
        PipelinePhase.VF_COMPUTATION: ExecutionState.PENDING,
    }
    mock_get.return_value = sample_manifest

    mock_broken_logic = MagicMock(side_effect=RuntimeError("Convergence crash"))
    context_data = {
        "user_id": sample_manifest.user_id,
        "simulation_id": sample_manifest.simulation_id,
    }

    phase = PipelinePhase.VF_COMPUTATION
    with pytest.raises(RuntimeError, match="Convergence crash"):
        execute_pipeline_task(
            context_data=context_data,
            phase=phase,
            logic_execution_block=mock_broken_logic,
        )

    assert sample_manifest.phase_statuses[phase] == ExecutionState.FAILED
    assert "Convergence crash" in str(sample_manifest.error_message)
