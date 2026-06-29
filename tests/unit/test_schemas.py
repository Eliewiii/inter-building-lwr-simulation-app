"""Test cases for the schemas."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas import (
    ExecutionState,
    PipelineConfig,
    PipelineParametersConfig,
    PipelinePhase,
    SimulationManifest,
)

# ==========================================
# 1. PipelineConfig Validation Tests
# ==========================================


def test_pipeline_config_parsing_success():
    """Verify that a complete, valid JSON payload structure initializes successfully."""
    valid_data = {
        "simulation_tag": "baseline-run",
        "description": "Running geometry validations for the primary urban block.",
        "parameter_config": {},  # Fall back entirely to inner schema defaults
    }

    config = PipelineConfig.model_validate(valid_data)

    assert config.simulation_tag == "baseline-run"
    assert config.description
    assert "primary urban block" in config.description
    assert isinstance(config.parameter_config, PipelineParametersConfig)


def test_pipeline_config_missing_required_tag():
    """Verify that omitting the required `simulation_tag` throws a ValidationError."""
    invalid_data = {"description": "Missing tag field completely"}

    with pytest.raises(ValidationError) as exc_info:
        PipelineConfig.model_validate(invalid_data)

    assert "Field required" in str(exc_info.value)
    assert "simulation_tag" in str(exc_info.value)


def test_pipeline_config_tag_exceeds_max_length():
    """Verify that a simulation_tag longer than 20 characters triggers a validation failure."""
    invalid_data = {
        "simulation_tag": "this-tag-is-way-too-long-for-the-limit",
        "description": "Testing character bounds boundary check",
    }

    with pytest.raises(ValidationError) as exc_info:
        PipelineConfig.model_validate(invalid_data)

    assert "String should have at most 20 characters" in str(exc_info.value)


def test_pipeline_config_optional_description_defaults_to_none():
    """Confirm that the configuration defaults to None when a description is omitted."""
    minimal_data = {"simulation_tag": "variant-a"}

    config = PipelineConfig.model_validate(minimal_data)
    assert config.description is None


# ==========================================
# 2. SimulationManifest Integrity Tests
# ==========================================


def test_simulation_manifest_initializes_with_correct_phase_map():
    """Verify that a new manifest automatically populates all pipeline phases as UNSTARTED."""
    now = datetime.now(timezone.utc)

    manifest = SimulationManifest(
        simulation_id="test_sim_2026_abc123",
        user_id="user_dev_88",
        user_tag="variant-b",
        description="Core integration manifest layer confirmation",
        creation_time=now,
    )

    assert manifest.simulation_id == "test_sim_2026_abc123"
    assert manifest.user_id == "user_dev_88"
    assert manifest.creation_time == now

    # Assert that all declared phases exist and default to UNSTARTED status tracking
    assert len(manifest.phase_statuses) == len(PipelinePhase)
    for phase in PipelinePhase:
        assert manifest.phase_statuses[phase] == ExecutionState.UNSTARTED

    # Assert tracking dicts and attributes default safely
    assert manifest.error_message is None
    assert isinstance(manifest.output_files, dict)
    assert len(manifest.output_files) == 0


def test_simulation_manifest_serialization():
    """Confirm the manifest can round-trip serialize to stringified JSON and back cleanly."""
    now = datetime.now(timezone.utc)

    manifest = SimulationManifest(
        simulation_id="sim_dump_test", user_id="user_123", user_tag="baseline", creation_time=now
    )

    # 1. Dump to raw JSON string representation
    json_str = manifest.model_dump_json()

    # 2. Re-instantiate directly from string input
    hydrated_manifest = SimulationManifest.model_validate_json(json_str)

    assert hydrated_manifest.simulation_id == manifest.simulation_id
    assert hydrated_manifest.user_tag == "baseline"
    # Note: Pydantic normalizes timezones cleanly to string timestamps
    assert (
        hydrated_manifest.phase_statuses[PipelinePhase.VF_COMPUTATION] == ExecutionState.UNSTARTED
    )


# TODO : add tests for the paramters if it makes sense.
