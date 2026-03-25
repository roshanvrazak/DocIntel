FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Add non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app

COPY pyproject.toml .

# Create a dummy app/main.py if it doesn't exist to allow uvicorn to start and pip install to find a package
RUN mkdir -p app && touch app/__init__.py && \
    echo "from fastapi import FastAPI\napp = FastAPI()" > app/main.py

# Install dependencies and the project
RUN pip install --no-cache-dir .

COPY . .
RUN chown -R appuser:appuser /app

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
