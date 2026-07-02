# ==============================================================================
# STAGE 1: Builder
# ==============================================================================
FROM python:3.12-slim AS builder
WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Remove the --target flag. This installs into the standard location for this stage
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install .

# ==============================================================================
# STAGE 2: Final Runner (Production Image)
# ==============================================================================
FROM python:3.12-slim AS runner
WORKDIR /code

# Copy the entire standard site-packages from the builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
# Copy the binary scripts as well
COPY --from=builder /usr/local/bin /usr/local/bin

RUN mkdir -p /app/data && chown -R 1001:1001 /app/data /code
USER 1001

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]