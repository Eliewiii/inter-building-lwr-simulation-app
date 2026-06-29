# app/workers/__init__.py

from .task_lwr_preprocessing import run_lwr_pre_processing
from .task_lwr_simulation import run_lwr_simulation
from .task_postprocessing import run_post_processing
from .task_pre_processing import run_pre_processing
from .task_vf_comp import run_vf_computation

# This makes them available as 'from app.workers import run_pre_processing'
__all__ = [
    "run_pre_processing",
    "run_lwr_pre_processing",
    "run_vf_computation",
    "run_lwr_simulation",
    "run_post_processing",
]
