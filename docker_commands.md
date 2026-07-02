# Docker Compose Management Guide

This guide contains the essential commands for managing the multi-container simulation stack. 

---

## Phase 1: Initial Setup & First Boot

Use these commands when setting up the environment for the very first time on a new machine or terminal context.

### 1. Fix Linux Socket Permissions (Run once per terminal session if needed)
# If you hit a "permission denied" socket error on Linux, force the current terminal tab to register your user's docker group membership:
```bash
exec sg docker -c "$SHELL"
```
# *(Note: To fix this permanently across your entire desktop environment, log out of your Linux user session and log back in).*

### 2. First-Time Environment Build
# Compile the core image layers, build internal dependencies, and start the cluster in background (detached) mode:
```bash
docker compose up -d --build
```

---

## Phase 2: Active Code Development & Updates

# Because your code is built statically into the image, Docker cannot see host file changes automatically unless a development mount is configured. Use these commands to push updates.

### 1. Force Image Rebuild on Code Changes
# Whenever you modify your Python scripts, Pydantic schemas, or .env configuration files, force Docker to re-read your local directory and compile a fresh image snapshot:
```bash
docker compose up -d --build
```

### 2. Nuclear Reset (Bypass Stale Build Caching)
# If Docker aggressively caches layers and fails to register code modifications or system package updates, wipe the slate clean and rebuild from scratch without using the cache:
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

---

## Phase 3: Cluster Monitoring & Verification

# Use these commands to verify that the cluster components (api, worker, redis) are active and communicating properly.

### 1. Stream Real-Time Application Logs
# Watch your FastAPI gateway incoming traffic or track your numerical simulation execution routines inside the Celery queue:
# Stream everything
```bash
docker compose logs -f
```

# Stream only the background worker calculations
```bash
docker compose logs -f worker
```

# Stream only the FastAPI endpoints
```bash
docker compose logs -f api
```

### 2. Verify Internal Container Settings
# Inspect exactly how Pydantic parses your runtime configuration inside the running container's environment scope:
```bash
docker compose exec api python -c "from app.core.config import settings; print('DEV_MODE Status:', settings.dev_mode)"
```

### 3. Check System Resource Consumption
# Monitor exactly how much CPU, memory, and networking traffic your parallel computational processes are drawing from your host machine:
```bash
docker stats
```

---

## Phase 4: Powering Down & Clean Up

# Use these commands when you are done developing or running simulation workloads to free up local hardware memory.

### 1. Stop and Remove the Cluster Infrastructure
# Safely shut down the running processes and dismantle the virtual bridge network. Your simulation data vault is fully preserved on your local machine:
```bash
docker compose down
```

### 2. Clean Up Dangling System Storage (Optional)
# If you have run multiple --no-cache builds, old unused image fragments can take up local disk space. Free up cached layers safely:
```bash
docker system prune -f
```