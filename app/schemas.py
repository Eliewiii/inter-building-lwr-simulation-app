"""Schemas."""

from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, Field


class PipelineRunRequest(BaseModel):
    """The strict payload accepted by the API to trigger steps."""

    priority_queue: bool = Field(default=False, description="Routes to fast_lane if true")

    # Flags for which specific steps to execute
    run_pre_processing: bool = False
    run_vf_computation: bool = False
    run_lwr_pre_processing: bool = False
    run_lwr_simulation: bool = False
    run_post_processing: bool = False


class TaskContext(BaseModel):
    """The context passed to each Celery task, containing all necessary metadata."""

    user_id: str
    simulation_id: str


# ==========================================
# 1. Individual Step Configurations
# ==========================================


class ViewFactorComputationConfig(BaseModel):
    """Configuration for the spatial data processing and grid generation phase."""

    # TODO


class LWRConfig(BaseModel):
    """Configuration for the core numerical/coupled simulation engine."""

    # TODO


class PostProcessingConfig(BaseModel):
    """Configuration for parsing simulation outputs and generating data visualization exports."""

    # TODO


# ==========================================
# 2. The Step Container (The Namespace Group)
# ==========================================


class PipelineParametersConfig(BaseModel):
    """The central container grouping all algorithmic and execution parameters."""

    vf_comp: ViewFactorComputationConfig = Field(default_factory=ViewFactorComputationConfig)
    lwr: LWRConfig = Field(default_factory=LWRConfig)
    post_processing: PostProcessingConfig = Field(default_factory=PostProcessingConfig)


class PipelineConfig(BaseModel):
    """The central container grouping all algorithmic and execution parameters."""

    parameter_config: PipelineParametersConfig = Field(default_factory=PipelineParametersConfig)
    simulation_tag: str = Field(
        ...,
        max_length=20,
        description=(
            "A short, concise alphanumeric label (e.g., 'baseline', 'variant-a') used for "
            "directory naming."
        ),
    )
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description=(
            "Detailed notes or context describing this specific simulation scenario execution."
        ),
    )


class PipelinePhase(str, Enum):
    """The discrete phases of the simulation workflow."""

    INITIALIZING = "initializing"
    PRE_PROCESSING = "pre_processing"
    VF_COMPUTATION = "vf_computation"
    LWR_PRE_PROCESSING = "lwr_pre_processing"
    LWR_SIMULATION = "lwr_simulation"
    POST_PROCESSING = "post_processing"


class ExecutionState(str, Enum):
    """Possible execution states."""

    UNSTARTED = "unstarted"  # <-- Clean, explicit state for "not run yet"
    PENDING = "pending"  # Means: Enqueued in the message broker lane
    RUNNING = "running"  # Means: Active thread/process execution
    COMPLETED = "completed"
    FAILED = "failed"
    INVALIDATED = "invalidated"


# ==========================================
# 3. The Master State Object (The Manifest)
# ==========================================


class SimulationManifest(BaseModel):
    """The absolute source of truth for a single simulation workflow instance."""

    simulation_id: str = Field(..., description="Unique UUID for this simulation run.")
    user_id: str = Field(..., description="The owner of the simulation workspace.")

    user_tag: str = Field(
        ...,
        max_length=20,
        description=(
            "A short, concise alphanumeric label (e.g., 'baseline', 'variant-a') used for "
            "directory naming."
        ),
    )
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description=(
            "Detailed notes or context describing this specific simulation scenario execution."
        ),
    )
    creation_time: datetime = Field(
        ..., description="Timestamp when the simulation was first created."
    )

    # State tracking attributes
    # We replace the single string with a mapped dictionary
    phase_statuses: Dict[PipelinePhase, ExecutionState] = Field(
        default_factory=lambda: {phase: ExecutionState.UNSTARTED for phase in PipelinePhase}
    )
    error_message: Optional[str] = Field(
        default=None, description="Detailed error log if execution fails."
    )
    last_updated: datetime = Field(default_factory=datetime.now)

    # The clean, nested configuration object
    parameter_config: PipelineParametersConfig = Field(default_factory=PipelineParametersConfig)

    # Map of successful outputs generated on the host file system
    # e.g., {"meshing": "grid.json", "solver": "raw_thermal_deltas.bin"}
    output_files: Dict[str, str] = Field(default_factory=dict)

    # TODO: add verifications for simulation and user id
    #
