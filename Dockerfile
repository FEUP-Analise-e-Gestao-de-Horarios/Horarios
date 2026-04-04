# Production: builds frontend then serves everything from the Django/Daphne backend.

# ── Stage 1: Build frontend ───────────────────────────────────────────────────
FROM node:24-alpine AS frontend-builder

WORKDIR /workspace

COPY frontend/package*.json ./frontend/
RUN cd frontend && npm ci

COPY frontend/ ./frontend/

RUN cd frontend && npm run build

# ── Stage 2: Production backend ───────────────────────────────────────────────
FROM python:3.14-slim

RUN useradd --uid 1000 --create-home appuser
COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /uvx /bin/

WORKDIR /workspace/backend

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-editable --no-install-project

RUN mkdir -p /workspace/databases/projects
RUN chown -R appuser /workspace/databases

COPY backend/ ./

# Inject the built frontend assets
COPY --from=frontend-builder /workspace/frontend/dist ./src/static/frontend


# Pre-collect static files into STATIC_ROOT so WhiteNoise can serve them
RUN DJANGO_SETTINGS_MODULE=src.config.settings.prod \
    SECRET_KEY=placeholder-for-collectstatic \
    uv run manage.py collectstatic --noinput

EXPOSE 8000
USER appuser

ENTRYPOINT ["/workspace/backend/entrypoint.sh"]
CMD ["uv", "run", "daphne", "-b", "0.0.0.0", "-p", "8000", "src.config.asgi:application"]
