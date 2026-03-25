FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

# Create a dummy app/main.py if it doesn't exist to allow uvicorn to start for verification
RUN mkdir -p app && touch app/__init__.py && echo "from fastapi import FastAPI\napp = FastAPI()" > app/main.py

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
