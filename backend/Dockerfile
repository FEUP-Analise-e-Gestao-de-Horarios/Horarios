FROM python:3.14-slim

RUN useradd --uid 1000 --create-home appuser
ARG UV_VERSION=0.11.3
RUN python -m pip install --no-cache-dir "uv==${UV_VERSION}"

WORKDIR /workspace/backend

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-editable --no-install-project

RUN mkdir -p /workspace/databases/projects
RUN chown -R appuser /workspace/databases
RUN chown -R appuser /workspace/backend

COPY . .

EXPOSE 8000
USER appuser

ENTRYPOINT ["/workspace/backend/entrypoint.sh"]
CMD ["uv", "run", "manage.py", "runserver", "0.0.0.0:8000"]
