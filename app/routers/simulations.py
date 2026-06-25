"""Router module for simulation-related endpoints in the FastAPI application."""

from fastapi import APIRouter, Header, HTTPException

from app.schemas import (
    PipelineRunRequest,
)

# from app.services import orchestrator

router = APIRouter(prefix="/simulations", tags=["Execution"])


@router.post("/{sim_id}/run")
async def execute_simulation(
    sim_id: str, request: PipelineRunRequest, x_user_id: str = Header(...)
):
    """_summary_.

    Args:
        sim_id (str): _description_
        request (PipelineRunRequest): _description_
        x_user_id (str, optional): _description_. Defaults to Header(...).

    Raises:
        HTTPException: _description_
        HTTPException: _description_

    Returns:
        _type_: _description_
    """
    try:
        None
        task_id = 0
        # Hand off the Pydantic object directly to the service layer
        # task_id = orchestrator.schedule_pipeline(x_user_id, sim_id, request)

        return {
            "message": "Pipeline validation successful. Computation queued.",
            "task_id": task_id,
        }
    except ValueError as e:
        # Catches dependency rule failures (e.g., trying to run solver early)
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Simulation manifest not found.")
