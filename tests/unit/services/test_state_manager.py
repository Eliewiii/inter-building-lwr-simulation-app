"""Unit tests for the state_manager service."""

import pytest
from fastapi import HTTPException

from app.services import state_manager


def test_get_workspace_resolves_correctly(mock_storage_env):
    """Verify that workspace paths match the expected structure within our isolated sandbox."""
    user_id = "user_abc"
    sim_id = "sim_xyz"

    expected_path = mock_storage_env / user_id / sim_id
    resolved_path = state_manager.get_workspace(user_id, sim_id)

    assert resolved_path == expected_path


def test_update_manifest_success(mock_storage_env, sample_manifest):
    """Confirm we can save a manifest cleanly when the target workspace directory exists."""
    user_id = sample_manifest.user_id
    sim_id = sample_manifest.simulation_id

    # 1. Manually provision the directory to mimic operational behavior
    workspace = state_manager.get_workspace(user_id, sim_id)
    workspace.mkdir(parents=True, exist_ok=True)

    # 2. Persist state tracking data
    state_manager.update_manifest(user_id, sim_id, sample_manifest)

    # 3. Read it back via the service to confirm disk I/O accuracy
    saved_manifest = state_manager.get_manifest(user_id, sim_id)
    assert saved_manifest.simulation_id == sim_id
    assert saved_manifest.user_tag == sample_manifest.user_tag


def test_update_manifest_raises_http_500_if_workspace_missing(mock_storage_env, sample_manifest):
    """Verify the defensive check throws an HTTPException if the workspace folder does not exist."""
    user_id = sample_manifest.user_id
    sim_id = sample_manifest.simulation_id

    # Intentionally avoid creating the directory
    with pytest.raises(HTTPException) as exc_info:
        state_manager.update_manifest(user_id, sim_id, sample_manifest)

    assert exc_info.value.status_code == 500
    assert "Active workspace directory missing" in exc_info.value.detail


def test_get_manifest_raises_file_not_found_if_missing(mock_storage_env):
    """Ensure accessing a non-existent state manifest drops a hard FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        state_manager.get_manifest("ghost_user", "non_existent_sim")
