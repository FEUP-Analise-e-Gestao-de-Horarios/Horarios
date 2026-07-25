# Production: builds frontend then serves everything from the Django/Daphne backend.

# ── Stage 1: Build frontend ───────────────────────────────────────────────────
FROM node:26-alpine AS frontend-builder

WORKDIR /workspace

COPY frontend/package*.json frontend/.npmrc ./frontend/
RUN cd frontend && npm ci --include=optional

COPY frontend/ ./frontend/

RUN cd frontend && npm run build

# ── Stage 2: Production backend ───────────────────────────────────────────────
FROM python:3.14-slim

ARG UV_VERSION=0.11.3
RUN python -m pip install --no-cache-dir "uv==${UV_VERSION}"

WORKDIR /workspace/backend

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-editable --no-install-project

RUN mkdir -p /workspace/databases/projects

COPY backend/ ./

# Inject the built frontend assets
COPY --from=frontend-builder /workspace/frontend/dist ./src/static/frontend


# Pre-collect static files into STATIC_ROOT so WhiteNoise can serve them
RUN DJANGO_SETTINGS_MODULE=src.config.settings.prod \
    SECRET_KEY=placeholder-for-collectstatic \
    uv run manage.py collectstatic --noinput

EXPOSE 8000

ENTRYPOINT ["/workspace/backend/entrypoint.sh"]
CMD ["uv", "run", "daphne", "-b", "0.0.0.0", "-p", "8000", "src.config.asgi:application"]
