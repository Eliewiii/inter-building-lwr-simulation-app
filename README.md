# SimGateway-LWR: Enterprise Microservice Mesh for Urban Scale Inter-Buildings UBES coupled Long-Wave Radiation Simulation

![Python](https://img.shields.io/badge/python-3.12+-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Containerization-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-Distributed_Tasks-373737?style=for-the-badge&logo=celery&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-Cache_%26_Broker-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-v2_Validation-e92063?style=for-the-badge)
![EnergyPlus](https://img.shields.io/badge/EnergyPlus-V26.1.0-005587?style=for-the-badge&logo=energyplus&logoColor=white)
![pyenergyplus](https://img.shields.io/badge/pyenergyplus-API-005587?style=for-the-badge)
![Pytest](https://img.shields.io/badge/Pytest-Testing-0A9EDC?style=for-the-badge) ![GitHub
Actions](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)
![Ruff](https://img.shields.io/badge/Linter-Ruff-FCC21B?style=for-the-badge)
![HPC](https://img.shields.io/badge/HPC-Parallel%20Computing-blueviolet?style=for-the-badge)
![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)
[![CI - SimGateway-LWR Hybrid Pipeline](https://github.com/Eliewiii/inter-building-lwr-simulation-app/actions/workflows/ci.yml/badge.svg)](https://github.com/Eliewiii/inter-building-lwr-simulation-app/actions/workflows/ci.yml)

**SimGateway-LWR** is a production-grade backend gateway and distributed task architecture
engineered to orchestrate large-scale inter-building coupled UBES (urban building energy simulation)
and long-wave radition simulations. Built to transition complex formulations developed during PhD into a
cloud-native SaaS infrastructure, this framework exposes a robust, async REST API mesh capable of
ingestive preprocessing, tracking, and parallelizing longwave radiation exchange simulations across
hundreds of individual building instances simultaneously. 

---

## ⚠️ Project Status Notice

**Active Enterprise Transition Phase:** This framework represents the modern cloud infrastructure
backbone of ongoing operational R&D. 
* **Production-Ready Backbone:** The entire microservice layout, asynchronous API gateway routes,
  strict Pydantic data validation schemas, configurations, and internal messaging infrastructures
  are fully implemented, optimized, and verified.
* **Algorithmic Engine Integration (Coming Soon):** The core numerical execution layers are actively
  being translated from validated, existing scientific packages developed during doctoral research
  at the Technion. Native containerized end-to-end integration verification is scheduled for
  upcoming development sprints.

---

## 🚀 Architectural Matrix & Core Features

### 1. Asynchronous API Gateway Infrastructure (`api`)
* **FastAPI Routing Layer:** Exposes strict REST endpoints handling multi-file multipart form-data
  package injection (e.g., matching configurations alongside EnergyPlus `.idf` and `.epw` files).
* **Strict Pydantic V2 Contract Validation:** Implements multi-tiered, type-safe data modeling
  (`PipelineConfig`, `SimulationManifest`, and explicit execution flags) ensuring invalid
  algorithmic or geometrical properties are rejected at the application perimeter before eating up
  hardware resources.
* **Dependency-Injected Perimeter Control:** Features a modular security layer equipped with
  dedicated developer sandbox configuration capabilities (`DEV_MODE`), permitting instant local
  validation bypass and structural isolation mock routines.

### 2. Distributed Task Queue & Orchestration (`worker` + `redis`)
* **Decoupled Job Lifecycle Processing:** Leverages a highly scalable Celery worker distribution
  layer backed by a dedicated Redis message broker network lane to transition heavy scientific loops
  away from the main HTTP thread.
* **Finite State Machine Manifest Tracking:** Maintains a real-time, absolute source-of-truth status
  tracker over execution sub-phases (`INITIALIZING` -> `VF_COMPUTATION` -> `LWR_SIMULATION` ->
  `POST_PROCESSING`), capturing structural failure stack traces elegantly.

### 3. Scientific Foundations (The Ph.D. Inversion Core)
* **Radiosity Solver Infrastructure:** Orchestrates numerical calculation configurations for global
  radiation balances across dense urban canopy layers.
* **Equivalent Boundary Forcing Configuration:** Built to drive the calculation of **Equivalent
  Surrounding Surface Temperatures ($T_{eq}$)**, bypassing native single-building thermal balance
  limitations by dynamically forcing neighborhood heat reflections through the EnergyPlus API.

---

## 🐳 Containerized Infrastructure Layout

The system is engineered to deploy seamlessly via an isolated multi-container architecture,
encapsulating all scientific, network, and caching requirements into an optimized runtime topology.

```
[ Client / Frontend Request ] 
              │
              ▼ (HTTP POST /simulations)
   ┌─────────────────────────────────────┐
   │  FastAPI Gateway (sim_gateway_api)  │
   └──────────────────┬──────────────────┘
                      │ (Enqueue Task JSON payload)
                      ▼
         ┌─────────────────────────┐
         │ Redis Bus (sim_storage) │
         └────────────┬────────────┘
                      │ (De-serialize Job Package)
                      ▼
   ┌─────────────────────────────────────┐
   │  Celery Worker (sim_gateway_worker) │ ──> [ Launches Isolated Process Spawns ]
   └──────────────────┬──────────────────┘
                      │
                      ▼ (Shared Volumetric Workspace Mounted On Host Linux Kernel)
    [ Host File System Storage: Data Vault Volumes / Local Cache Paths ]
```

---

## 📂 Core Domain Models & Schemas

The architecture enforces highly strict structural tracking contracts via nested Pydantic types to
preserve analytical safety during parallel tasks:

```python
class PipelineConfig(BaseModel):
    """The central container grouping all algorithmic and execution parameters."""
    parameter_config: PipelineParametersConfig = Field(default_factory=PipelineParametersConfig)
    simulation_tag: str = Field(..., max_length=20, description="Short label used for directory isolation.")
    description: Optional[str] = Field(default=None, max_length=500)

class SimulationManifest(BaseModel):
    """The absolute source of truth for a single simulation workflow instance."""
    simulation_id: str = Field(..., description="Unique UUID for this simulation run.")
    user_id: str = Field(..., description="The owner of the simulation workspace.")
    phase_statuses: Dict[PipelinePhase, ExecutionState] = Field(default_factory=dict)
    error_message: Optional[str] = Field(default=None)
    last_updated: datetime = Field(default_factory=datetime.now)
```

---

## 🎓 Context & Research Attribution

**Author:** Elie Medioni, Ph.D.  
**Institution:** Technion – Israel Institute of Technology  
**Field of Research:** Computational Building Physics, Numerical Algorithm Engineering, Urban
Photovoltaic/Thermal Canopy Integration.  

This microservice application mesh represents the modernization step translating original doctoral
research—**Toward Fully Automated Inter-Building Coupling in Urban Energy Simulation: From Building
Models to Integrated Longwave Radiation Workflows**—into reliable, containerized cloud services
matching enterprise engineering standards.

---

## 📄 License

This project is licensed under the **MIT License**. It interfaces with `pyenergyplus`
configurations, subject to the original EnergyPlus™ license agreement rules.