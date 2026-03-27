FROM python:3.11-slim

WORKDIR /

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create backend directory
RUN mkdir -p /backend

# Add non-root user
RUN useradd -m appuser && chown -R appuser:appuser /backend

COPY pyproject.toml /backend/

# Install dependencies
RUN pip install --no-cache-dir /backend/

COPY . /backend/
RUN chown -R appuser:appuser /backend

USER appuser

ENV PYTHONPATH=/

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
