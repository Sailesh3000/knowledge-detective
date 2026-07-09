FROM python:3.11-slim

WORKDIR /workspace

# Copy requirements file first to take advantage of Docker layer caching
COPY requirements.txt /workspace/

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set PYTHONPATH so python can locate our 'app' module correctly
ENV PYTHONPATH=/workspace/backend

# Default entry point runs the ingestion test
CMD ["python", "backend/scripts/test_pipeline.py"]
