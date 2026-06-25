"""API main file."""

import logging

from fastapi import FastAPI

from app import __version__
from app.config import settings
from app.routers import initialization, simulations

# 1. Initialize the App
app = FastAPI(title="LWR coupled UBES simulation API", version=__version__)

"""
Start the server : uvicorn app.main:app --reload ot --workers 4
Stop the server : Ctrl + C in the terminal
Request example : curl -X POST "http://127.0.0.1:8000/process" \
                       -H "Content-Type: application/json" \
                       -d '{"file_path": "data/test_numbers.txt"}' or -d @path_to_json.json
"""

# 1. Setup Logging
logging.basicConfig(level=logging.INFO)

# 2. Initialize App
app = FastAPI(title="Algorithm R&D API", version=__version__)

# 3. Plug in the endpoints
# Ingestion/Workspace Initialization Endpoints
app.include_router(initialization.router, prefix=settings.api_v1_prefix)

# Computational Core Execution Endpoints
app.include_router(simulations.router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health_check():
    """Health check."""
    return {"status": "online", "version": __version__}
