"""Router module for simulation-related endpoints in the FastAPI application."""

from fastapi import APIRouter, Header, HTTPException

from app.schemas import PipelineRunRequest
from app.services import orchestrator

router = APIRouter(prefix="/simulations", tags=["Execution"])


@router.post("/{sim_id}/run", status_code=201)
async def execute_simulation(
    sim_id: str, request: PipelineRunRequest, x_user_id: str = Header(...)
) -> dict[str, str]:
    """Asynchronously schedule a sequential multi-phase simulation pipeline execution workflow.

    Args:
        sim_id: Unique string identifier matching the targeted workspace workspace.
        request: Pydantic parsing matrix mapping which computational blocks to activate.
        x_user_id: Request header authenticating the calling client context.

    Returns:
        A dictionary containing the confirmation status message and the parent canvas tracking
        chain_id token emitted by the message broker.

    Raises:
        HTTPException: 400 bad request if prerequisite schema matrix rules fail validation.
        HTTPException: 404 resource missing if the workspace directory manifest is not found.
    """
    try:
        # Hand off the validated Pydantic configuration parameters directly to orchestration
        chain_id = orchestrator.schedule_pipeline(x_user_id, sim_id, request)

        return {
            "message": "Pipeline validation successful. Computation chain queued.",
            "chain_id": chain_id,
        }
    except ValueError as e:
        # Catches sequential dependency structural violations (e.g., skipping a prereq phase)
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Simulation workspace manifest not found.")
