# Backend

The backend is a [Django](https://www.djangoproject.com/) application that
ingests FEUP timetable data, stores it in per-project SQLite databases, and
exposes a JSON API consumed by the React frontend. It serves both the API
(under `/api/`) and the compiled React single-page application (every other
route renders the SPA's `index.html`).

For repository layout see [Structure](structure.md); for domain terminology see
[Glossary](glossary.md); for the scrape-and-persist flow see
[Ingestion Pipeline](internals/ingestion-pipeline.md).

---

## Tech Stack

| Concern              | Choice                                                         |
| -------------------- | -------------------------------------------------------------- |
| Language / runtime   | Python ≥ 3.14                                                   |
| Web framework        | Django 6                                                       |
| ASGI server          | Daphne                                                         |
| Static file serving  | WhiteNoise (serves the built React app in production)          |
| Meta-database ORM    | Django ORM (SQLite)                                            |
| Project-database ORM | SQLAlchemy 2 (one SQLite file per project)                     |
| Validation           | Pydantic 2 (request bodies and response payloads)             |
| Scraping             | `requests` + `beautifulsoup4`                                  |
| Dependency manager   | [`uv`](https://docs.astral.sh/uv/) (`pyproject.toml` + `uv.lock`) |
| Lint / format        | Ruff; type checking via Pyright (`strict`)                     |

All Python code lives under `backend/src/`. The Django project package is
`src.config`, so settings, ASGI, and the root URLconf are referenced as
`src.config.*`.

---

## Django Applications

| App                | Routes            | Responsibility                                                                 |
| ------------------ | ----------------- | ------------------------------------------------------------------------------ |
| `src.config`       | root URLconf      | Settings, ASGI entry point, SPA + API URL routing                              |
| `src.core`         | —                 | Shared API infrastructure: `require_auth`/`require_project` decorators, `ApiError`/`ErrorResponse` helpers, Pydantic base schemas, request-body validation |
| `src.users`        | —                 | Custom `User` model (`AUTH_USER_MODEL = "users.User"`) and its manager         |
| `src.login`        | `/api/auth/`      | Session-based authentication (login, logout, current user, password flows)     |
| `src.projects`     | `/api/projects/`  | `Project`/`Group` Django models, the per-project SQLite database layer, and all project/schedule resource endpoints |

`src.core` and `src.users` register no HTTP routes; the API is served entirely
by `src.login` and `src.projects`. The `ingestion` package (`src.ingestion`)
is plain Python — it is **not** a Django app and has no models or migrations;
it is invoked by `src.projects` to populate a project's database.

---

## Databases

The backend uses two distinct database layers.

### Meta-database (Django ORM)

A single SQLite file at `databases/db.sqlite3` holds Django's own tables plus
the application's account and project metadata:

- `users.User` — accounts (custom user model).
- `projects.Project` — one row per schedule project: `name`, `url`, ingestion
  lifecycle timestamps (`ingestion_started_at` / `ingestion_finished_at` /
  `ingestion_failed_at`), `creator`, and many-to-many links to users and groups.
- `projects.Group` — named groups of users that can be assigned to projects.

This layer is managed with normal Django migrations
(`uv run manage.py migrate`).

### Per-project databases (SQLAlchemy)

Each project's scraped timetable data lives in its **own** SQLite file, created
when the project is created — never in the meta-database. The files live under
`databases/projects/<project_id>/`:

| File                  | Purpose                                                       |
| --------------------- | ------------------------------------------------------------- |
| `general_database.db` | Live working database (read and edited by the API)            |
| `initial_database.db` | Snapshot taken right after a successful ingestion (baseline)  |

These databases are **not** Django-managed. They are defined with SQLAlchemy
models under `src/projects/projects_db/models/` (tables: `rooms`, `teachers`,
`degrees`, `years`, `subjects`, `classes`, their red-block tables, `sessions`
with `session_rooms` / `session_teachers` / `sessions_classes_subject`
association tables, and the parallel-block tables). A reference DDL is kept at
`src/projects/projects_db/models/db_schema.sql` for documentation only.

Supporting modules:

- `projects_db/registry.py` — caches one SQLAlchemy `Engine` per database path
  and hands out sessions via `get_session(path)`. Every connection enables
  `journal_mode=WAL`, `foreign_keys=ON`, and a busy timeout.
- `projects_db/paths.py` — resolves `general_db()` / `initial_db()` paths from a
  project id (rooted at `settings.PROJECTS_DB_PATH`).
- `projects_db/dao/` — one Data Access Object per model, used by both the
  ingestion pipeline and the API views.
- `services/project_db.py` — `create_project_db()` / `delete_project_db()`
  create the directory and engine for a new project and tear them down on
  delete.

---

## API Surface

All endpoints return JSON. Successful resource responses are wrapped in a
`SuccessResponse` envelope (`{"message": ..., "data": ...}`); errors use
`ErrorResponse` (`{"error": <code>, "message": ...}`) with a stable error code
from `ApiError`. Authentication is session/cookie based; protected views use the
`@require_auth` decorator (and `@require_project` where a `project_id` is in the
URL).

### Auth — `src/login/urls.py` (mounted at `/api/auth/`)

| Method | Path                       | Description                                  |
| ------ | -------------------------- | -------------------------------------------- |
| GET    | `/api/auth/me`             | Current authenticated user (sets CSRF cookie) |
| POST   | `/api/auth/login`          | Log in with username + password              |
| POST   | `/api/auth/logout`         | Log out the current session                  |
| POST   | `/api/auth/forgot-password`| Send a password-reset email                  |
| POST   | `/api/auth/change_password`| Change the current user's password           |

### Projects — `src/projects/urls.py` (mounted at `/api/projects/`)

| Method | Path                                                  | Description                                          |
| ------ | ----------------------------------------------------- | ---------------------------------------------------- |
| GET    | `/api/projects/`                                      | List all projects                                    |
| POST   | `/api/projects/`                                      | Create a project; starts ingestion on a background thread (returns `202`) |
| GET    | `/api/projects/<id>`                                  | Retrieve a single project                            |
| PATCH  | `/api/projects/<id>`                                  | Rename a project                                     |
| DELETE | `/api/projects/<id>`                                  | Delete a project and its databases                   |
| GET    | `/api/projects/<id>/stats`                            | Overview statistics for a project                    |
| GET    | `/api/projects/<id>/rooms/`, `.../rooms/<uuid>`       | List rooms / single room                             |
| GET    | `/api/projects/<id>/teachers/`, `.../teachers/<uuid>` | List teachers / single teacher                       |
| GET    | `/api/projects/<id>/degrees/`, `.../degrees/<uuid>`   | List degrees / single degree                         |
| GET    | `/api/projects/<id>/years/`, `.../years/<uuid>`       | List years / single year                             |
| GET    | `/api/projects/<id>/subjects/`, `.../subjects/<uuid>` | List subjects / single subject                       |
| GET    | `/api/projects/<id>/classes/`, `.../classes/<uuid>`   | List classes / single class                          |
| GET    | `/api/projects/<id>/sessions/`                        | List sessions                                        |

The schedule resource endpoints are read-only today (GET only); each resource
has its own module under `src/projects/views/` with a matching Pydantic
response schema under `src/projects/views/schemas/`. Project ids are integers;
all per-project schedule resources are identified by UUIDs.

Django's admin site is also mounted at `/admin/`.

---

## Settings Modules

Settings are split so the shared base is never used directly:

| Module                        | Selected via `DJANGO_SETTINGS_MODULE`             | Notes                                                  |
| ----------------------------- | ------------------------------------------------- | ------------------------------------------------------ |
| `src.config.settings.base`    | (imported by the others)                          | Apps, middleware, databases, email, static config      |
| `src.config.settings.dev`     | `src.config.settings.dev`                          | `DEBUG = True`, livereload, Vite CSRF origins; default in `manage.py` |
| `src.config.settings.prod`    | `src.config.settings.prod`                         | `DEBUG = False`, WhiteNoise manifest static storage    |

Key environment variables (see `backend/.env.template`): `SECRET_KEY`,
`ALLOWED_HOSTS`, and the `EMAIL_*` group. `manage.py` defaults the settings
module to `src.config.settings.dev`; the Docker images set it explicitly.

---

## Running the Backend

The backend is normally run as part of the full stack (`make dev`); see the
[Setup Guide](setup.md). To run it on its own with `uv`:

```sh
cd backend
uv sync                              # install dependencies from uv.lock
uv run manage.py migrate             # apply migrations to the meta-database
uv run manage.py runserver           # start the dev server on :8000
```

`backend/entrypoint.sh` (used by the Docker image) creates the
`databases/projects` directory, runs `migrate --noinput`, and then execs the
container command (`uv run manage.py runserver 0.0.0.0:8000` in dev). In
production a single multi-stage image serves the API via Daphne/ASGI and the
built React app via WhiteNoise — see the [Deployment Guide](deployment.md).
