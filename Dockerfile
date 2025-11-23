# Use a slim Python image
FROM python:3.12-slim

# Where the app will live in the container
WORKDIR /app

# Install system-level deps (curl, etc. if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python deps definition
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code into the image
COPY backend /app/backend

# Expose the port Fly will hit
EXPOSE 8080

# Run the FastAPI app with uvicorn
# (module: backend.main_service, variable: app)
CMD ["uvicorn", "backend.main_service:app", "--host", "0.0.0.0", "--port", "8080"]
