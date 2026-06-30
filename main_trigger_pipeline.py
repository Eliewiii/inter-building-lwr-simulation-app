import json
import os
import tempfile
import zipfile

import requests

# --- ENDPOINT CONFIGURATION ---
API_URL = "http://localhost:8000/api/v1/simulations/upload"  # Adjust to your exact target endpoint

# --- CONSTRUCT PIPELINE CONFIG DATA (Matches PipelineConfig schema) ---
pipeline_config_payload = {
    "parameter_config": {
        "vf_comp": {},  # Maps to empty defaults for ViewFactorComputationConfig
        "lwr": {},  # Maps to empty defaults for LWRConfig
        "post_processing": {},  # Maps to empty defaults for PostProcessingConfig
    },
    "simulation_tag": "baseline-urban-01",
    "description": "Automated pipeline trigger testing with mock IDF and EPW assets",
}

# --- MOCK SIMULATION DATA STRUCTURES ---
mock_idf_content = """! EnergyPlus Input Data File (IDF) Mock Baseline
Version, 23.2;
Building,
  Urban Block Simulation,  !- Name
  0.0,                     !- North Axis {deg}
  Suburbs,                 !- Terrain
  0.04,                    !- Loads Convergence Tolerance Value {W}
  0.4,                     !- Temperature Convergence Tolerance Value {deltaC}
  FullInteriorAndExterior, !- Solar Distribution
  25,                      !- Maximum Number of Warmup Days
  6;                       !- Minimum Number of Warmup Days
"""

mock_epw_content = """#LOCATION,Haifa,ISR,Israel,Typical Design Year,401840,32.79,35.00,2.0,5.0
#DATA PERIODS,1,1,Data,Sunday, 1/ 1,12/31
2026,1,1,1,60,X,X,X,X,X,X,X,X,X,X,X,X,X,X,14.2,11.5,84,101300,0,0,0,0,0,180,2.5,0,0,0,0,0
2026,1,1,2,60,X,X,X,X,X,X,X,X,X,X,X,X,X,X,13.9,11.4,85,101290,0,0,0,0,0,190,2.2,0,0,0,0,0
"""


def assemble_and_trigger():
    # 1. Allocate isolated OS safe space
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, "simulation_payload.zip")

        print(f"📦 Generating multi-file target archive at: {zip_path}")

        # 2. Package the configuration payload and structural computational files
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            # Write Pydantic-compliant PipelineConfig schema
            zipf.writestr("config.json", json.dumps(pipeline_config_payload, indent=4))

            # Write geometric and weather boundary condition files
            zipf.writestr("building.idf", mock_idf_content)
            zipf.writestr("weather.epw", mock_epw_content)

        print("🚀 Dispatching multipart data block payload over the gateway...")

        # 3. Stream binary structures over HTTP layer
        with open(zip_path, "rb") as f:
            files = {"file": ("simulation_payload.zip", f, "application/zip")}

            # Matches PipelineRunRequest parameter fields if passed alongside files
            data = {"config_str": pipeline_config_payload}
            headers = {"Authorization": "Bearer development_bypass_token"}

            try:
                response = requests.post(
                    API_URL, files=files, data=data, headers=headers, timeout=30
                )

                print(f"\n📡 [Status Code]: {response.status_code}")
                print("📝 [API Response Manifest Extraction]:")
                print(json.dumps(response.json(), indent=2))

            except requests.exceptions.ConnectionError:
                print("\n❌ Connectivity failure: The API container is unreachable on port 8000.")
            except Exception as e:
                print(f"\n❌ Execution pipeline dropped an unhandled exception: {str(e)}")


if __name__ == "__main__":
    assemble_and_trigger()
