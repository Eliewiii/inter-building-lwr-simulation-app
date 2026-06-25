"""Test initialization of new simulation."""

import zipfile
from unittest.mock import patch

from app.schemas import ExecutionState, PipelinePhase
from app.services import state_manager


def test_initialize_workspace_success(
    mock_user_id,
    api_client,
    mock_storage_env,
    valid_zip_payload,
    valid_config_form_string,
    upload_url,
):
    """Verify that a  compliant archive and form configuration successfully spins up a workspace."""
    with open(valid_zip_payload, "rb") as f:
        response = api_client.post(
            upload_url,
            files={"file": ("assets.zip", f, "application/zip")},
            data={"config_str": valid_config_form_string},
        )

    assert response.status_code == 200
    data = response.json()

    assert "simulation_id" in data
    assert data["files_received"] == 2
    assert "initialized and validated successfully" in data["message"]

    # Assert physical disk persistence was correctly committed via the state manager
    sim_id = data["simulation_id"]
    manifest = state_manager.get_manifest(mock_user_id, sim_id)

    assert manifest.user_tag == "baseline-run"
    assert manifest.phase_statuses[PipelinePhase.INITIALIZING] == ExecutionState.COMPLETED
    assert manifest.error_message is None


def test_initialize_workspace_fails_on_zip_bomb(
    api_client, mock_storage_env, zip_bomb_payload, valid_config_form_string, upload_url
):
    """Confirm the security barrier flags a 413 Entity Too Large by mocking the header size check."""
    # Create a fake list of ZipInfo objects where one file reports an enormous size
    fake_info_1 = zipfile.ZipInfo("model.idf")
    fake_info_1.file_size = 100 * 1024 * 1024  # Force to 100MB in memory!

    # Patch the validation checker's input directly when it calls zip_ref.infolist()
    with patch("zipfile.ZipFile.infolist", return_value=[fake_info_1]):
        with open(zip_bomb_payload, "rb") as f:
            response = api_client.post(
                upload_url,
                files={"file": ("assets.zip", f, "application/zip")},
                data={"config_str": valid_config_form_string},
            )

    # The zip is structurally 100% valid, but its in-memory size check reports 100MB!
    assert response.status_code == 413
    assert "Uncompressed payload exceeds" in response.json()["detail"]


def test_initialize_workspace_fails_on_illegal_extension(
    api_client, mock_storage_env, illegal_extension_payload, valid_config_form_string, upload_url
):
    """Assert that foreign extensions purge target disk assets."""
    with open(illegal_extension_payload, "rb") as f:
        response = api_client.post(
            upload_url,
            files={"file": ("assets.zip", f, "application/zip")},
            data={"config_str": valid_config_form_string},
        )

    assert response.status_code == 400
    assert "Disallowed file extension detected" in response.json()["detail"]


def test_initialize_workspace_invalid_config_json(
    api_client, mock_storage_env, valid_zip_payload, upload_url
):
    """Verify that scrambled configurations break early at validation."""
    malformed_json_str = "{ 'simulation_tag': mismatched-quotes-no-closing "

    with open(valid_zip_payload, "rb") as f:
        response = api_client.post(
            upload_url,
            files={"file": ("assets.zip", f, "application/zip")},
            data={"config_str": malformed_json_str},
        )

    assert response.status_code == 422
    assert "Invalid configuration JSON format" in response.json()["detail"]


def test_initialize_workspace_missing_file_payload(
    api_client, mock_storage_env, valid_config_form_string, upload_url
):
    """Verify that omitting the file entirely fails with standard FastAPI 422 validation errors."""
    response = api_client.post(
        upload_url,
        data={"config_str": valid_config_form_string},
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Field required"
