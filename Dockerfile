FROM python:3.14-slim-bookworm

# Install uv using the official binary image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set environment variables for optimization
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy dependency files to leverage layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies into the virtual environment using cache mounts
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy the rest of your Django application code
COPY . .

# Expose Django's default port
EXPOSE 8000

# Run the application server
CMD ["gunicorn", "myproject.wsgi:application", "--bind", "0.0.0.0:8000"]