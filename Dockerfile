# ==============================================================================
# STAGE 1: Builder
# ==============================================================================
FROM python:3.12-slim AS builder

# Define the APP_HOME once
ENV APP_HOME=/code
WORKDIR $APP_HOME

RUN apt-get update && apt-get install -y --no-install-recommends \
    git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Use the APP_HOME variable for paths
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install . 

# ==============================================================================
# STAGE 2: Final Runner
# ==============================================================================
FROM python:3.12-slim AS runner

# Use the same APP_HOME variable
ENV APP_HOME=/code
WORKDIR $APP_HOME

# Copy from builder using the variable
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder $APP_HOME $APP_HOME

# Create data folder and adjust ownership
RUN mkdir -p /app/data && chown -R 1001:1001 /app/data $APP_HOME
USER 1001

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]