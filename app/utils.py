from datetime import datetime
from pathlib import Path

from app.schemas import SimulationManifest


def update_manifest(filepath: Path, **kwargs):
    """Utility to safely update the state file."""
    # 1. Read existing state
    with open(filepath, "r") as f:
        current_state = SimulationManifest.model_validate_json(f.read())

    # 2. Update the fields
    for key, value in kwargs.items():
        setattr(current_state, key, value)
    current_state.last_updated = datetime.now()

    # 3. Write it back
    with open(filepath, "w") as f:
        f.write(current_state.model_dump_json(indent=4))
