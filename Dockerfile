FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps kept minimal; psycopg[binary] ships its own libpq.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
# Install runtime deps. We read them straight from pyproject via pip.
RUN pip install --upgrade pip && pip install \
    "fastapi>=0.111" "uvicorn[standard]>=0.30" "jinja2>=3.1" \
    "python-multipart>=0.0.9" "itsdangerous>=2.2" "sqlalchemy>=2.0" \
    "alembic>=1.13" "psycopg[binary]>=3.1" "pydantic>=2.7" \
    "pydantic-settings>=2.3" "python-telegram-bot>=21.0"

COPY . .

# Create the uploads dir; in production this is a mounted volume.
RUN mkdir -p /data/uploads

EXPOSE 8000

# Default command runs the web service; the bot service overrides it.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
