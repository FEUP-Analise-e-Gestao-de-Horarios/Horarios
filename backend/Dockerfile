FROM python:3.14-slim

RUN useradd --uid 1000 --create-home appuser
COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /uvx /bin/

WORKDIR /workspace/backend

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-editable --no-install-project

RUN mkdir -p /workspace/databases/projects
RUN chown -R appuser /workspace/databases

COPY . .

EXPOSE 8000
USER appuser

ENTRYPOINT ["/workspace/backend/entrypoint.sh"]
CMD ["uv", "run", "manage.py", "runserver", "0.0.0.0:8000"]
