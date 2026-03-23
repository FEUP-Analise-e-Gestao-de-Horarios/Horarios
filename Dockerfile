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

WORKDIR /workspace

RUN pip install --no-cache-dir pipenv

COPY backend/Pipfile backend/Pipfile.lock ./backend/
RUN cd backend && pipenv install --system

COPY backend/ ./backend/

RUN mkdir -p /workspace/databases/projects

# Inject the built frontend assets
COPY --from=frontend-builder /workspace/frontend/dist \
     ./backend/src/static/frontend

WORKDIR /workspace/backend

# Pre-collect static files into STATIC_ROOT so WhiteNoise can serve them
RUN DJANGO_SETTINGS_MODULE=src.config.settings.prod \
    SECRET_KEY=placeholder-for-collectstatic \
    python manage.py collectstatic --noinput

EXPOSE 8000
ENTRYPOINT ["/workspace/backend/entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "src.config.asgi:application"]
