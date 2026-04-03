FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN useradd --uid 1000 --create-home appuser

WORKDIR /workspace

COPY backend/pyproject.toml backend/uv.lock ./backend/
RUN cd backend && uv sync --frozen --no-editable --no-install-project

COPY backend/ ./backend/

ENV PATH="/workspace/backend/.venv/bin:$PATH"

RUN mkdir -p /workspace/databases/projects \
 && chown -R appuser /workspace
USER appuser

WORKDIR /workspace/backend
EXPOSE 8000
ENTRYPOINT ["/workspace/backend/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
