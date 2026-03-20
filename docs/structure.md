# Project Structure

For canonical naming of domain concepts (Degree, Class, Subject, Session, etc.) see [Glossary](glossary.md).

## Repository Layout

```
Horarios/
├── docs/                     # Project documentation
├── databases/                # SQLite databases
│   ├── db.sqlite3            # Django meta-database (users, projects, groups)
│   └── projects/             # Per-project schedule databases
│       └── <id>/
│           ├── general_database.db   # Live working database
│           └── initial_database.db   # Snapshot taken after ingestion
├── frontend/                 # React + TypeScript frontend (Vite)
│   ├── src/                  # Application source
│   ├── package.json
│   └── Dockerfile
├── backend/                  # Django backend
│   ├── src/                  # All Python source code
│   │   ├── manage.py         # Django management entry point
│   │   ├── config/           # Django project configuration
│   │   ├── templates/        # Global HTML templates
│   │   ├── static/           # Source static files
│   │   ├── staticfiles/      # Collected static files (DEBUG=False)
│   │   └── <apps>/           # Django application packages (see below)
│   ├── Pipfile               # Python dependency declarations
│   ├── Pipfile.lock
│   ├── .env.template         # Environment variable template
│   ├── entrypoint.sh         # Container entrypoint (runs migrations)
│   └── Dockerfile
├── scripts/                  # Mirror service scripts
│   └── Dockerfile
├── docker-compose.dev.yml    # Development stack
├── docker-compose.prod.yml   # Production stack
├── Dockerfile                # Production multi-stage build
└── Makefile                  # Common task shortcuts
```

## Django Applications

| Directory             | Purpose                                                                             |
| --------------------- | ----------------------------------------------------------------------------------- |
| `config/`             | Project-wide settings, root URL config (`urls.py`), ASGI entry point                |
| `core/`               | Core API endpoints for the schedule editor                                          |
| `ingestion/`          | Schedule data ingestion pipeline (see [Ingestion](internals/ingestion-pipeline.md)) |
| `login/`              | Authentication views and session management                                         |
| `parser/`             | Legacy schedule parsing views                                                       |
| `projects/`           | `Project` and `Group` models, project management views                              |
| `users/`              | Custom `User` model and user management                                             |
| `getHorariosFromDB/`  | Schedule query helpers and conflict-detection logic                                 |
| `FeupScheduleEditor/` | Shared utilities and template tags                                                  |

Within each application the following files are most relevant:

- `models.py` — Django ORM model definitions
- `views.py` — Request handlers (render pages or return JSON)
- `urls.py` — URL-to-view mappings
- `schemas.py` — Pydantic schemas for request/response validation

## Ingestion Package Layout

```
backend/src/ingestion/
├── manager.py          # IngestionManager — top-level pipeline orchestration
├── scraper.py          # Scraper — HTTP client for schedule pages
├── rooms.py            # ROOMS — static room metadata registry
├── utils.py            # Shared utility functions
├── parsers/            # HTML → Python: one module per page type
│   ├── menu.py
│   ├── teacher_page.py
│   ├── class_page.py
│   ├── red_blocks.py
│   └── utils.py
├── ingestors/          # Python → SQLite: one module per entity type
│   ├── teachers.py
│   ├── classes.py
│   └── rooms.py
└── schemas/            # Shared TypedDict / type alias definitions
    ├── misc.py
    ├── classes.py
    ├── rooms.py
    └── teachers.py
```

See [Ingestion](internals/ingestion-pipeline.md) for a detailed description of the pipeline.

## Settings Modules

| Module                        | Used when                                         |
| ----------------------------- | ------------------------------------------------- |
| `src/config/settings/base.py` | Shared base — never used directly                 |
| `src/config/settings/dev.py`  | `DJANGO_SETTINGS_MODULE=src.config.settings.dev`  |
| `src/config/settings/prod.py` | `DJANGO_SETTINGS_MODULE=src.config.settings.prod` |

The active module is selected via the `DJANGO_SETTINGS_MODULE` environment variable, which is set in the Docker Compose files.
