# Backend test suite

Pytest + `pytest-django`. Everything runs against a dedicated settings module,
`src.config.settings.test` (from `base.py`, a fixed `SECRET_KEY`, `DEBUG=False`,
no `livereload`), configured under `[tool.pytest.ini_options]` in
`pyproject.toml`.

## Layout

```
tests/
  conftest.py            # shared fixtures (user, auth_client, project, project_db)
  factories.py           # make_* row builders for the per-project SQLAlchemy DB
  unit/                  # fast, pure-logic tests — no DB, no HTTP
    ingestion/           # scraper + HTML parser tests (built HTML, no network)
    exporter/            # exporter graph/compact/schemas/legacy/benchmark logic
  integration/           # real HTTP requests through the Django test client
    conftest.py          # export_dbs fixture (initial + general project DBs)
    _export_seed.py      # fixed-id reference data + session seeding for the exporter
```

- **Unit** tests import a module and assert on its behavior directly. They do
  not touch a database and should stay fast. Example: `unit/test_smoke.py`
  exercises `build_candidate_components`.
- **Ingestion unit** tests (`unit/ingestion/`) cover the parsers and scraper.
  `unit/ingestion/_html.py` builds the minimal FEUP schedule/menu/teacher HTML
  each parser expects (indexed tables, the weekday header row, `td_tipologia_*`
  session cells, ...), so no captured pages or network are needed. The scraper
  tests swap in a fake `requests.Session`.
- **Exporter unit** tests (`unit/exporter/`) cover `src.exporter` as pure logic:
  the graph utilities/types, the `ExportGraph` algorithm (built via `__new__`),
  the compact⇄expanded payload round-trip, the pydantic schemas, the legacy
  conflict/comparator helpers and the benchmark statistics.
- **Integration** tests drive endpoints end to end via the Django test client,
  backed by a real, seeded, per-project SQLite file. Example:
  `integration/test_smoke_endpoint.py`. `integration/test_ingestion_manager.py`
  drives the whole `IngestionManager` pipeline with only the `Scraper` faked.
  The exporter pipeline is covered by `integration/test_export_endpoint.py`
  (`POST /export` end to end), `integration/test_export_graph_pipeline.py`
  (`ExportGraph` against real initial/general databases) and
  `integration/test_export_legacy_and_benchmark.py` (legacy `Comparator` and the
  benchmark mutation/run helpers). These use the `export_dbs` fixture, which
  provisions *both* the initial and general project databases.

## How to run

All commands run from `backend/`:

```bash
cd backend

# whole suite
uv run pytest

# with coverage
uv run pytest --cov=src --cov-report=term-missing

# a subset
uv run pytest tests/unit
uv run pytest tests/integration/test_smoke_endpoint.py -k unknown_project
```

## The two data layers

The backend has two independent databases, and the fixtures cover both.

1. **Django ORM** (default sqlite, managed by `pytest-django`). The custom user
   model, `Project`, sessions/auth. Any test needing it must depend — directly
   or transitively — on the `db` fixture; the `user`/`project` fixtures already
   do.
2. **Per-project SQLAlchemy SQLite file**, one per `Project.pk` under
   `settings.PROJECTS_DB_PATH`. This is where the timetable data lives (degrees,
   years, subjects, classes, sessions, parallel-block groups). Endpoints open
   their _own_ SQLAlchemy session against
   `paths.general_db(project_id)` at request time.

### Fixtures (`conftest.py`)

| Fixture       | Gives you                                                          |
| ------------- | ------------------------------------------------------------------ |
| `user`        | an active `users.User` (created via the custom manager)            |
| `auth_client` | a `django.test.Client` already `force_login`-ed as `user`          |
| `project`     | a `projects.Project` row owned by `user`; use `project.pk` in URLs |
| `project_db`  | the per-project SQLAlchemy DB, provisioned + a live `Session`      |

`project_db` is the key integration fixture. It:

1. overrides `settings.PROJECTS_DB_PATH` to a unique `tmp_path` (so
   `paths.general_db`, read at call time, resolves under it — no cross-test
   collisions since each test gets its own tmp dir),
2. creates the project directory and builds the ORM schema via
   `init_engine(general_db(project.pk))`,
3. yields a live `Session` for seeding, and
4. on teardown closes the session and `evict_engine`-s the cached engine.

Because the endpoint opens a **separate** session against the same file, seeded
rows must be **committed** before the request. The factories commit by default.

### Factories (`factories.py`)

Plain `make_*` functions insert rows with sensible defaults and accept keyword
overrides. They commit by default; pass `commit=False` to batch several inserts
and commit once. Parents are auto-created when omitted (e.g. `make_class`
creates a `Year`, which creates a `Degree`).

- `make_degree`, `make_year`, `make_subject` (links to a year via the
  `subject_years` m2m), `make_class`, `make_session`,
  `make_session_class_subject`, `make_group_member`
- `make_room`, `make_teacher`, and the red-block builders
  `make_teacher_red_block` / `make_room_red_block` / `make_class_red_block`
- `link_session_teacher` / `link_session_room` — attach a session to a teacher
  or room via the m2m tables (so it shows up in that entity's stats and blocks)
- `make_parallel_candidate_pair(session, ...)` — high-level helper that seeds
  the minimum rows for two blocks to be detected as parallel candidates for one
  subject (two blocks sharing the same `(week, weekday, start_time, subject)`
  slot). Returns the two `original_block_id`s, sorted.

Typical integration test shape:

```python
def test_something(auth_client, project, project_db):
    block_a, block_b = make_parallel_candidate_pair(project_db)  # commits

    response = auth_client.get(
        f"/api/projects/{project.pk}/parallel-blocks/candidates",
    )

    assert response.status_code == 200
    assert len(response.json()["data"]) == 1
```
