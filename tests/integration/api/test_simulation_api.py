"""Integration tests verifying HTTP route entry points, payload validation, and task dispatch."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.schemas import SimulationManifest

pytestmark = [pytest.mark.integration]


def test_pipeline_execution_via_http_post_route(
    mock_user_id: str,
    sample_manifest: SimulationManifest,
    api_client: TestClient,
    run_url_factory,
) -> None:
    """Submit an execution request via HTTP POST and verify successful route dispatching.

    Patches the internal orchestrator storage hooks and dispatch boundary to deliver an
    immediate tracking token, validating HTTP translation layers cleanly.
    """
    # 1. Align manifest ownership with the fixture's authenticated user identity
    sample_manifest.user_id = mock_user_id

    # 2. Patch both state persistence layers and the dispatch boundary inside the orchestrator
    with (
        patch("app.services.orchestrator.get_manifest", return_value=sample_manifest),
        patch("app.services.orchestrator.update_manifest") as mock_update,
        patch("app.services.orchestrator._dispatch_chain", return_value="mock-celery-chain-id"),
    ):
        # 3. Construct the standard API execution payload match parameters
        api_payload = {
            "run_pre_processing": True,
            "run_vf_computation": True,
            "run_lwr_pre_processing": False,
            "run_lwr_simulation": False,
            "run_post_processing": False,
            "priority_queue": False,
        }

        # 4. Resolve the endpoint string dynamically using the factory fixture
        url = run_url_factory(sim_id=sample_manifest.simulation_id)

        # 5. Dispatch the network call through the test client router
        response = api_client.post(
            url, json=api_payload, headers={"X-User-ID": sample_manifest.user_id}
        )

        # 6. Assert HTTP transport boundaries resolved successfully
        assert response.status_code == 201
        response_data = response.json()

        assert "chain_id" in response_data
        assert response_data["chain_id"] == "mock-celery-chain-id"
        assert (
            response_data["message"] == "Pipeline validation successful. Computation chain queued."
        )

        # 7. Ensure validation checks and manifest locking routines were triggered
        mock_update.assert_called()
