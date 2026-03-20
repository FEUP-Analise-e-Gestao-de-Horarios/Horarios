FROM python:3.14-slim

RUN useradd --uid 1000 --create-home appuser

WORKDIR /workspace

RUN pip install --no-cache-dir pipenv

COPY backend/Pipfile backend/Pipfile.lock ./backend/
RUN cd backend && pipenv install --system --dev

COPY backend/ ./backend/

RUN mkdir -p /workspace/databases/projects \
 && chown -R appuser /workspace
USER appuser

WORKDIR /workspace/backend
EXPOSE 8000
ENTRYPOINT ["/workspace/backend/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
