from celery import chain

from app.schemas import (
    ExecutionState,
    PipelinePhase,
    PipelineRunRequest,
    SimulationManifest,
    TaskContext,
)
from app.services.state_manager import get_manifest, update_manifest
from app.workers.tasks import run_lwr_pre, run_lwr_sim, run_post, run_preproc, run_vf

PREREQUISITES = {
    PipelinePhase.PRE_PROCESSING: None,  # Base step, needs nothing
    PipelinePhase.VF_COMP: PipelinePhase.PRE_PROCESSING,
    PipelinePhase.LWR_PREPROCESSING: PipelinePhase.VF_COMP,
    PipelinePhase.LWR_SIMULATION: PipelinePhase.LWR_PREPROCESSING,
    PipelinePhase.POST_PROCESSING: PipelinePhase.LWR_SIMULATION,
}


def validate_execution_request(manifest: SimulationManifest, requested_phases: list[PipelinePhase]):
    """_summary_

    Args:
        manifest (SimulationManifest): _description_
        requested_phases (List[PipelinePhase]): _description_

    Raises:
        ValueError: _description_
        ValueError: _description_
        ValueError: _description_

    Returns:
        _type_: _description_
    """
    if not requested_phases:
        raise ValueError("No phases requested.")

    # 1. Check if ANYTHING is currently running in Celery for this simulation.
    # We block new requests if Celery is already working on this simulation
    # to prevent the "Race Condition" crash mentioned earlier.
    for phase, state in manifest.phase_statuses.items():
        if state in [ExecutionState.PENDING, ExecutionState.RUNNING]:
            raise ValueError(
                f"Simulation is currently locked because '{phase.value}' is in progress. "
                f"Please wait for it to finish before scheduling new steps."
            )

    # 2. Check the prerequisite of the FIRST requested step
    first_step = requested_phases[0]
    required_previous_step = PREREQUISITES[first_step]

    if required_previous_step is not None:
        # If the prerequisite isn't COMPLETED, we reject the request.
        if manifest.phase_statuses[required_previous_step] != ExecutionState.COMPLETED:
            raise ValueError(
                f"Cannot start '{first_step.value}'. "
                f"It requires '{required_previous_step.value}' to be completely finished first."
            )

    # If we get here, it is 100% safe to build the chain!
    return True


TASK_MAP = {
    PipelinePhase.PRE_PROCESSING: run_preproc,
    PipelinePhase.VF_COMP: run_vf,
    PipelinePhase.LWR_PREPROCESSING: run_lwr_pre,
    PipelinePhase.LWR_SIMULATION: run_lwr_sim,
    PipelinePhase.POST_PROCESSING: run_post,
}


def schedule_pipeline(user_id: str, sim_id: str, requested_phases: PipelineRunRequest):
    """_summary_

    Args:
        user_id (str): _description_
        sim_id (str): _description_
        requested_phases (PipelineRunRequest): _description_

    Returns:
        _type_: _description_
    """
    manifest = get_manifest(user_id, sim_id)  # Your file reader

    # 1. Validate (This ensures the first step is allowed)
    validate_execution_request(manifest, requested_phases)

    # 2. Update the Manifest to show these are now in the queue
    for phase in requested_phases:
        manifest.phase_statuses[phase] = ExecutionState.PENDING
    update_manifest(user_id, sim_id, manifest)

    # 3. Build the Chain
    context = TaskContext(user_id=user_id, simulation_id=sim_id)
    celery_chain_tasks = []

    for i, phase in enumerate(requested_phases):
        task_func = TASK_MAP[phase]
        if i == 0:
            # The first task gets the context IDs injected
            celery_chain_tasks.append(task_func.s(context.model_dump()))
        else:
            # Subsequent tasks inherit context from the previous task automatically
            celery_chain_tasks.append(task_func.s())

    # 4. Fire to Celery
    workflow = chain(*celery_chain_tasks)
    result = workflow.apply_async()

    return result.id
