# Project Structure

For canonical naming of domain concepts (Degree, Section, Subject, Session, etc.) see [Glossary](Glossary.md).

## Repository Layout

```
PI/
├── docs/               # Project documentation
├── databases/          # SQLite databases
│   ├── db.sqlite3      # Django meta-database (users, projects, groups)
│   ├── criar.sql       # DDL for a project's schedule database
│   └── projects/       # Per-project schedule databases
│       └── <id>/
│           ├── general_database.db   # Live working database
│           └── initial_database.db   # Snapshot taken after ingestion
├── scripts/            # Utility shell scripts
├── src/                # All application source code
│   ├── manage.py       # Django management entry point
│   ├── config/         # Django project configuration
│   ├── templates/      # Global HTML templates
│   ├── static/         # Source static files (JS, CSS) — served in DEBUG=True
│   ├── staticfiles/    # Collected static files — served in DEBUG=False
│   └── <apps>/         # Django application packages (see below)
├── Pipfile             # Python dependency declarations
└── pyproject.toml      # Linter / formatter configuration
```

## Django Applications

| Directory            | Purpose                                                                 |
| -------------------- | ----------------------------------------------------------------------- |
| `config/`            | Project-wide settings (`settings.py`), URL root (`urls.py`), ASGI entry |
| `core/`              | Core views and API endpoints for the schedule editor                    |
| `ingestion/`         | Schedule data ingestion pipeline (see [Ingestion](Ingestion.md))        |
| `login/`             | Authentication views and session management                             |
| `parser/`            | Legacy schedule parsing views                                           |
| `projects/`          | `Project` and `Group` models, project management views                  |
| `users/`             | `User` model and user management                                        |
| `getHorariosFromDB/` | Auxiliary functions for querying schedule data from the database        |

Within each application, the following files are most relevant:

- `models.py` — Django ORM model definitions
- `views.py` — Request handlers (render pages or return JSON)
- `urls.py` — URL-to-view mappings
- `schemas.py` — Pydantic or TypedDict schemas for request/response validation

## Ingestion Package Layout

The `src/ingestion/` package is organized into four sub-packages:

```
src/ingestion/
├── manager.py      # IngestionManager — top-level pipeline orchestration
├── scraper.py      # Scraper — HTTP client for schedule pages
├── rooms.py        # ROOMS — static room metadata registry
├── utils.py        # Shared utility functions
├── parsers/        # HTML → Python: one module per page type
├── ingestors/      # Python → SQLite: one module per entity type
└── schemas/        # Shared TypedDict / type alias definitions
```

See [Ingestion](Ingestion.md) for a detailed description of the pipeline.

## Templates

HTML templates live in `src/templates/` and are organized by feature:

```
templates/
├── admin/      # Admin overrides
├── common/     # Shared partials (nav, layout)
├── editTurnos/ # Shift editing views
├── export/     # Export views
├── login/      # Authentication pages
└── starter/    # Landing / project selection pages
```
