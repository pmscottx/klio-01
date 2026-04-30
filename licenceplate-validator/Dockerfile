FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
RUN pip install poetry --no-cache-dir
COPY pyproject.toml .
RUN poetry install --no-root --no-interaction
COPY app/ ./app/
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8015"]
