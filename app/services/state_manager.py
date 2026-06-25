"""Manage the state of simulations, including workspace directories and status manifests."""

from pathlib import Path

from fastapi import HTTPException, status

from app.config import settings
from app.schemas import SimulationManifest

MANIFEST_FILENAME = "manifest.json"


def get_workspace(user_id: str, sim_id: str) -> Path:
    """Safely constructs the directory path."""
    return Path(settings.container_data_path) / user_id / sim_id


def get_manifest_path(user_id: str, sim_id: str) -> Path:
    """Resolve the location of the localized state tracking manifest file."""
    return get_workspace(user_id, sim_id) / MANIFEST_FILENAME


def get_manifest(user_id: str, sim_id: str) -> SimulationManifest:
    """Reads and validates the current state."""
    manifest_path = get_manifest_path(user_id, sim_id)
    if not manifest_path.exists():
        raise FileNotFoundError("Simulation not found.")

    with open(manifest_path, "r") as f:
        return SimulationManifest.model_validate_json(f.read())


def update_manifest(user_id: str, sim_id: str, manifest: SimulationManifest) -> None:
    """Overwrites or saves the manifest.json with the latest state.

    Raises:
        HTTPException: 500 error if the workspace directory does not exist.
    """
    workspace = get_workspace(user_id, sim_id)

    if not workspace.exists() or not workspace.is_dir():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"State sync failed. Active workspace directory missing for simulation: {sim_id}"
            ),
        )

    manifest_path = get_manifest_path(user_id, sim_id)
    manifest_path.write_text(manifest.model_dump_json(indent=4), encoding="utf-8")
