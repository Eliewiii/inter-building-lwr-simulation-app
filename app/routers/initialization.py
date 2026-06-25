"""Router module for simulation-related endpoints in the FastAPI application."""

import re
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from json import JSONDecodeError
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError

from app.config import settings
from app.schemas import (
    ExecutionState,
    PipelineConfig,
    PipelinePhase,
    SimulationManifest,
)
from app.services import state_manager
from app.services.auth import get_current_user_id  # Import our new security helper

router = APIRouter(prefix="/simulations", tags=["Initialization"])


@router.post("/upload")
async def initialize_simulation(
    file: UploadFile = File(...),
    # The client sends the Pydantic JSON config as a plain form string
    config_str: str = Form(...),
    x_user_id: str = Depends(get_current_user_id),
):
    """Initialize a unified simulation workspace by uploading an asset archive and configuration.

    This endpoint streams a single compressed archive (.zip) containing all raw spatial and climatic
    simulation primitives (e.g., EnergyPlus .idf models, weather profiles .epw) directly into an
    isolated user-specific directory. It concurrently parses a stringified JSON parameter payload
    into a strictly validated Pydantic `PipelineConfig` schema.

    **Cybersecurity Safeguards Incorporated:**
    - **Path Traversal Protection:** Extraction relies on `zipfile.extractall` combined with
      explicit `pathlib.Path` structures (leveraging Python 3.12+'data' filtering standards),
      preventing maliciously crafted filenames from escaping the allocated directory sandbox.
    - **Decompression Denial of Service (Zip Bomb Mitigation):** Inspects the uncompressed target
      sizes declared in the headers via `zip_ref.infolist()` before committing extraction writes.
      Rejects and cleans payloads exceeding the configured `storage_quota_mb`.

    **Future Optimization Path:**
    - *Upgrade Candidate:* Consider migrating the ingestion pipeline format to `.tar.gz` (Tarball
      compressed via Gzip). While `.zip` provides optimal compatibility for testing and end-user
      direct API consumers, a `.tar.gz` archive compresses the consolidated binary stream at once
      rather than file-by-file. This achieves significantly higher compression ratios for
      text-dense, highly repetitive energy models (.idf), drastically reducing ingress network
      overhead while retaining native Unix permission metadata inside minimal Docker base images.

    Args:
        file (UploadFile): A binary stream of a valid, non-corrupted .zip archive.
        config_str (str): A stringified JSON object matching the `PipelineConfig` Pydantic model.
        x_user_id (str): Cryptographically verified user unique identification injected via JWT
          validation.

    Returns:
        dict: A success message, the unique generated `simulation_id`, and count of extracted raw
        inputs.
    """
    # 1. Validate it is a ZIP archive
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid file or missing filename. Please upload a single "
                ".zip archive containing all simulation assets."
            ),
        )

    # 2. Safely parse the incoming JSON configuration string into our Pydantic model
    try:
        config = PipelineConfig.model_validate_json(config_str)
    except (JSONDecodeError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid configuration JSON format provided in 'config_str'.",
        )

    # 3. Provision the secure workspace with Tag, Timestamp, and UUID Suffix
    sim_id, creation_time = _generate_simulation_id(config.simulation_tag)
    workspace = state_manager.get_workspace(x_user_id, sim_id)
    workspace.mkdir(parents=True, exist_ok=True)

    # 4. Stream the zip archive safely to disk
    zip_path = workspace / "bundle.zip"
    with open(zip_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 5. CYBERSECURITY GUARDRAIL: Prevent a "Zip Bomb" DoS attack
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            file_info_list = _verify_archive_security(
                zip_ref=zip_ref, workspace_dir=workspace, storage_quota_mb=settings.storage_quota_mb
            )
            _ = _validate_simulation_primitives(
                file_info_list=file_info_list, workspace_dir=workspace
            )

            # 6. Secure Extraction
            # zip_ref.extractall automatically protects against path traversal vulnerabilities.
            extraction_dir = workspace / "inputs"
            extraction_dir.mkdir(exist_ok=True)
            zip_ref.extractall(path=extraction_dir)

    except zipfile.BadZipFile:
        shutil.rmtree(workspace)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is a corrupted or invalid zip archive.",
        )
    finally:
        # Clean up the raw .zip file to preserve disk space after extraction is completed
        if zip_path.exists():
            zip_path.unlink()

    # 7. Collect the extracted file names to map into your manifest outputs
    extracted_files = [f.name for f in (workspace / "inputs").iterdir() if f.is_file()]

    # 8. Generate the finalized INITIALIZING manifest
    manifest = SimulationManifest(
        simulation_id=sim_id,
        user_id=x_user_id,
        user_tag=config.simulation_tag,
        description=config.description,
        creation_time=creation_time,
        parameter_config=config.parameter_config,
    )
    manifest.phase_statuses = {PipelinePhase.INITIALIZING: ExecutionState.COMPLETED}

    state_manager.update_manifest(x_user_id, sim_id, manifest)

    return {
        "message": "Simulation workspace initialized and validated successfully.",
        "simulation_id": sim_id,
        "files_received": len(extracted_files),
    }


def _generate_simulation_id(simulation_tag: str) -> tuple[str, datetime]:
    """Generate a human-readable, unique, and secure identifier.

    Example output: 'baseline_20260625_1145_a1b2c3d4'
    """
    now = datetime.now(timezone.utc)
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")

    # Clean the user tag for safe Linux directory paths
    clean_tag = simulation_tag.strip().lower()
    clean_tag = re.sub(r"\s+", "-", clean_tag)
    clean_tag = re.sub(r"[^a-z0-9\-_]", "", clean_tag)

    # Append the unique 8-character random UUID token string
    unique_suffix = uuid.uuid4().hex[:8]

    sim_id = f"{clean_tag}_{timestamp_str}_{unique_suffix}"
    return sim_id, now


def _verify_archive_security(
    zip_ref: zipfile.ZipFile, workspace_dir: Path, storage_quota_mb: int
) -> list[zipfile.ZipInfo]:
    """Layer 1: Enforces infrastructure and system security rules on the raw archive.

    Mitigates Decompression Denial of Service attacks (Zip Bombs) and validates basic
    integrity constraints before allowing downstream processing.
    """
    file_info_list = zip_ref.infolist()

    # 1. Zip Bomb Mitigation: Verify uncompressed target bounds
    total_uncompressed_size_bytes = sum(f.file_size for f in file_info_list)
    quota_bytes = storage_quota_mb * 1024 * 1024

    if total_uncompressed_size_bytes > quota_bytes:
        shutil.rmtree(workspace_dir)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Extraction rejected. Uncompressed payload exceeds the {storage_quota_mb}MB quota."
            ),
        )

    return file_info_list


def _validate_simulation_primitives(
    file_info_list: list[zipfile.ZipInfo], workspace_dir: Path
) -> list[str]:
    """Layer 2: Enforces scientific domain rules specific to the simulation engine.

    Validates file extension white-lists and ensures structural dependencies
    (geometry files and weather data) are fully present.
    """
    ALLOWED_EXTENSIONS = {".idf", ".epw"}
    has_epw = False
    has_idf = False
    verified_files = []

    for file_info in file_info_list:
        if file_info.is_dir():
            continue

        filename = Path(file_info.filename).name
        ext = Path(filename).suffix.lower()

        # Cybersecurity Boundary: Whitelist filtering
        if ext not in ALLOWED_EXTENSIONS:
            shutil.rmtree(workspace_dir)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Disallowed file extension detected: '{filename}'. Only simulation"
                    " primitives are supported."
                ),
            )

        if ext == ".epw":
            if has_epw:
                shutil.rmtree(workspace_dir)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Multiple weather profile files detected. Only one '.epw' file is "
                        "allowed per simulation."
                    ),
                )
            has_epw = True

        if ext == ".idf":
            has_idf = True

        verified_files.append(filename)

    # Scientific dependency checks
    if not has_idf:
        shutil.rmtree(workspace_dir)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Missing building model data. The archive must contain at least one '.idf' file."
            ),
        )
    if not has_epw:
        shutil.rmtree(workspace_dir)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Missing climatic context data. The archive must contain at least one weather"
                " profile '.epw' file."
            ),
        )

    return verified_files
