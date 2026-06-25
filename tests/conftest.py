"""Fixtures for unit tests, including temporary storage isolation and sample data generation."""

import zipfile
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.schemas import PipelineConfig, PipelineParametersConfig, SimulationManifest

# ==========================================
# Test Environment and API
# ==========================================


@pytest.fixture(scope="session")
def mock_user_id():
    """Provides a centralized session-wide mock user string constant."""
    return "user_dev_42"


@pytest.fixture
def mock_storage_env(tmp_path, monkeypatch):
    """Isolate storage operations by patching the global container data path variable.

    Automatically cleans up all directory contents on disk after the test runs finish.
    """
    # Create a temporary sandbox root inside pytest's isolated directory framework
    fake_storage_root = tmp_path / "mock_container_data"
    fake_storage_root.mkdir()

    # Use monkeypatch to swap out settings safely for the duration of the test run
    monkeypatch.setattr(settings, "container_data_path", str(fake_storage_root))
    monkeypatch.setattr(settings, "storage_quota_mb", 50)

    return fake_storage_root


@pytest.fixture
def api_client(mock_user_id):
    """Provides a pristine test client pointing to the isolated workspace with mocked auth."""
    from app.main import app
    from app.services.auth import get_current_user_id

    # Override the dependency globally for the test app instance
    app.dependency_overrides[get_current_user_id] = lambda: mock_user_id

    yield TestClient(app)

    # Clean up overrides after tests finish so it doesn't leak
    app.dependency_overrides.clear()


# ==========================================
# Sample Manifest
# ==========================================


@pytest.fixture
def sample_manifest():
    """Generate a valid, fully populated SimulationManifest instance for validation runs."""
    return SimulationManifest(
        simulation_id="baseline_20260625_1200_a1b2c3d4",
        user_id="user_test_99",
        user_tag="baseline",
        description="Integration testing state manifest scenario description.",
        creation_time=datetime.now(timezone.utc),
        parameter_config=PipelineParametersConfig(),
    )


# ==========================================
# Mock Input Files
# ==========================================


@pytest.fixture
def valid_zip_payload(tmp_path):
    """Generate a structurally valid simulation zip containing exactly 1 .idf and 1 .epw file."""
    zip_dir = tmp_path / "payloads"
    zip_dir.mkdir(exist_ok=True)
    zip_file_path = zip_dir / "valid_simulation.zip"

    with zipfile.ZipFile(zip_file_path, "w") as zf:
        zf.writestr("model.idf", "Version, 23.2;\nBuilding, Urban Block Scenario;")
        zf.writestr("weather.epw", "EPW DATA, HAIFA ISRAEL, 2026;")

    return zip_file_path


@pytest.fixture
def zip_bomb_payload(tmp_path):
    """Generate a perfectly valid, non-corrupt ZIP file structure."""
    zip_dir = tmp_path / "payloads"
    zip_dir.mkdir(exist_ok=True)
    zip_file_path = zip_dir / "zip_bomb.zip"

    # Write a perfectly normal, tiny, healthy archive
    with zipfile.ZipFile(zip_file_path, "w") as zf:
        zf.writestr("model.idf", "Version, 23.2;")

    return zip_file_path


@pytest.fixture
def illegal_extension_payload(tmp_path):
    """Generate an archive holding a disallowed file extension execution risk."""
    zip_dir = tmp_path / "payloads"
    zip_dir.mkdir(exist_ok=True)
    zip_file_path = zip_dir / "backdoor.zip"

    with zipfile.ZipFile(zip_file_path, "w") as zf:
        zf.writestr("exploit.py", "print('Malicious script execution block')")
        zf.writestr("model.idf", "Version, 23.2;")
        zf.writestr("weather.epw", "EPW DATA;")

    return zip_file_path


@pytest.fixture
def valid_config_form_string():
    """Provide a serialized production-compliant PipelineConfig form input payload string."""
    config = PipelineConfig(
        simulation_tag="baseline-run",
        description="Integration validation pipeline run description metadata.",
    )
    return config.model_dump_json()


# ==========================================
# URLs
# ==========================================


@pytest.fixture
def upload_url(api_client):
    """Dynamically resolve the workspace initialization endpoint URL path."""
    return api_client.app.url_path_for("initialize_simulation")


@pytest.fixture
def run_url_factory(api_client):
    """Provide a factory function to dynamically resolve the execution endpoint URL path.

    Since the execution endpoint requires a dynamic path parameter (sim_id),
    this fixture returns a function that accepts the sim_id at runtime.
    """

    def _run_url(sim_id: str) -> str:
        return api_client.app.url_path_for("execute_simulation", sim_id=sim_id)

    return _run_url
