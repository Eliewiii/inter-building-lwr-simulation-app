# ==============================================================================
# STAGE 1: Builder
# ==============================================================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Keep git installation so hatch-vcs can read your tags during build
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install them to a specific target folder
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/build/deps -r requirements.txt

# Copy the entire project context (including your pyproject.toml and .git folder)
COPY . .

# Install your app package itself into the deps folder.
# This forces hatch-vcs to read the .git folder and bake the version into the metadata.
RUN pip install --no-cache-dir --target=/build/deps .

# ==============================================================================
# STAGE 2: Final Runner (Production Image)
# ==============================================================================
FROM python:3.12-slim AS runner

WORKDIR /code

# Copy the compiled Python dependencies and app package from the builder stage
COPY --from=builder /build/deps /usr/local/lib/python3.12/site-packages

# Create the dedicated data folder matching your .env value and adjust ownership
RUN mkdir -p /app/data && chown -R 1001:1001 /app/data /code
USER 1001

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]