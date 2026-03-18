# Ingestion Pipeline

This document describes how schedule data is fetched from the institution's website and persisted into a project's SQLite database.

For domain terminology (Degree, Class, Subject, Session, Red Block, etc.) see [Glossary](Glossary.md).

---

## Overview

The ingestion pipeline is orchestrated by `IngestionManager` (`src/ingestion/manager.py`). Given a project ID, it:

1. Opens the project's SQLite database.
2. Drives a `Scraper` to fetch and parse HTML pages from the institution's schedule website.
3. Delegates persistence to DAO classes from `src/projects/projects_db/dao/`.
4. Runs a shift-assignment step to enrich the stored data.

The pipeline is triggered once per project and its output is a fully populated `general_database.db` file. On success, the database is also snapshotted as `initial_database.db`.

---

## Pipeline Phases

### Phase 1 — Setup

`IngestionManager.__init__` opens the SQLite database at:

```
PROJECTS_DB_PATH/<project_id>/general_database.db
```

and creates a `Scraper` pointed at the project's configured URL.

`_setup()` stamps `started_ingestion_at` on the `Project` record and clears any previous `finished_ingestion_at` / `failed_ingestion_at` timestamps.

---

### Phase 2 — Menu Parsing

`Scraper.read_menu()` drives a two-step fetch:

1. Fetches the root URL and extracts the `<frame name="links">` src to find the navigation menu page.
2. Fetches the menu page and locates three `<li>` sections — **Docentes**, **Turmas**, **Salas** — producing:
   - A flat list of teacher page URLs.
   - A structured `Degree → Year → Class → week URLs` hierarchy.
   - A list of room metadata + timetable URLs.

The three results feed into the subsequent phases.

---

### Phase 3 — Fetch Class Pages

Before any database writes begin, `run()` iterates over every class in the degree hierarchy and fetches all of its weekly schedule pages via `Scraper.get_class_page()`. The parsed `ClassPage` data (dates, teachers, subjects, sessions, red blocks) is stored in-memory on each `Class`'s `pages` list.

A flat list of teachers found across all class pages is also extracted here. This is necessary because some teachers have no red blocks and therefore no links in the menu — these would otherwise be missed.

---

### Phase 4 — Ingest Teachers (`_ingest_teachers`)

1. For each teacher URL from the menu, fetch the teacher page (`Scraper.get_teacher_page`).
2. Parse the `<td class="cabtitulo">` element to extract acronym, full name, and numeric code.
3. Parse red blocks (cells with class `td_vermelha`).
4. Merge in any teachers from class pages (Phase 3) that were not present in the menu (i.e. those without red blocks).
5. Insert each teacher via `TeacherDAO.create()`.
6. Insert each of the teacher's red blocks via `TeacherRedBlockDAO.create()`.

---

### Phase 5 — Ingest Classes (`_ingest_classes`)

Inserts the degree/year/class hierarchy into the database:

1. Each degree is inserted via `DegreeDAO.create()`.
2. Each year is inserted via `YearDAO.create()`, linked to its degree.
3. Each class is inserted via `ClassDAO.create()`, linked to its year, with an initial shift value of `0`.

No subjects, sessions, or red blocks are written in this phase.

---

### Phase 6 — Ingest Rooms (`_ingest_rooms`)

For each room entry from the menu:

1. Fetch the room's timetable page via `Scraper.get_room_page()` to collect red blocks.
2. Insert the room via `RoomDAO.create()` using static metadata from the `ROOMS` registry (`src/ingestion/rooms.py`). Rooms not present in the registry default to `"Desconhecido"` for type, size, and seat count.
3. Insert each red block via `RoomRedBlockDAO.create()`.

---

### Phase 7 — Ingest Sessions (`_ingest_sessions`)

Iterates over every class page within the degree hierarchy and persists subjects and sessions:

**Subjects:**

- For each class page, subjects not yet in the database are inserted via `SubjectDAO.create()`, linked to their year.

**Sessions:**

- For each session on a class page, the method resolves the subject, teachers, classes, and rooms to their database entries via the respective DAOs.
- Weekly session records are created spanning the page's date range (one per week, advancing by 7 days from `start_date` to `end_date`).
- If a session already exists for the same week, weekday, time, and classes, its subject list is extended rather than creating a duplicate.
- Sessions are created via `SessionDAO.create()` with linked subject, teacher, class, and room IDs.
- Sessions without a physical room are stored without room associations (the raw data uses `"Online"` as a sentinel).
- Session type is set to `"T"` for theoretical sessions (CSS class `td_tipologia_19`) and `"TP"` otherwise.

---

### Phase 8 — Ingest Shifts (`_ingest_shifts`)

Calculates and assigns shift numbers to classes based on their theoretical sessions:

1. Retrieves all subjects from the database via `SubjectDAO.get_all()`.
2. For each subject, fetches all `"T"` type sessions via `SessionDAO.get_by_subject_type()`.
3. For each session, identifies classes that have not yet been assigned a shift (tracked via a visited set).
4. Assigns the current shift counter value to each unvisited class's `shift` attribute.
5. Increments the shift counter only after processing a session with new classes.
6. Commits all changes in a single transaction.

---

### Phase 9 — Teardown

**On success (`_teardown_success`):**

- `general_database.db` is copied to `initial_database.db` as a baseline snapshot.
- `finished_ingestion_at` is stamped on the `Project` record.

**On failure (`_teardown_failure`, any exception):**

- `failed_ingestion_at` is stamped on the `Project` record.
- The exception is re-raised after cleanup.

In both cases the database connection and HTTP session are closed.

---

## Module Map

```
src/ingestion/
├── manager.py          # IngestionManager — pipeline orchestration
├── scraper.py          # Scraper — HTTP client + page dispatcher
├── rooms.py            # ROOMS — static room metadata registry
│
├── parsers/            # HTML → Python data structures
│   ├── menu.py         # extract_menu_link, extract_menu_tags,
│   │                   # extract_teacher_links, extract_sessions_info,
│   │                   # extract_rooms_info
│   ├── teacher_page.py # extract_teacher_info
│   ├── class_page.py   # extract_week_dates, extract_teachers,
│   │                   # extract_subjects, extract_sessions
│   ├── red_blocks.py   # extract_red_blocks
│   └── utils.py        # matrix_from_html_table, get_cell_column,
│                       # get_weekday_at_column
│
└── schemas/            # TypedDict / type alias definitions
    ├── misc.py         # Matrix, Time, RedBlock, TurnosMap
    ├── classes.py      # Degree, Year, Class, ClassPage, Teacher,
    │                   # Subject, Session
    ├── rooms.py        # RoomInfo
    └── teachers.py     # TeacherInfo
```

---

## DAO Classes Used

Persistence is handled through DAO (Data Access Object) classes from `src/projects/projects_db/dao/`, each accessed via a SQLAlchemy session obtained from `get_session()`:

| DAO                  | Used in                               | Purpose                                       |
| -------------------- | ------------------------------------- | --------------------------------------------- |
| `TeacherDAO`         | `_ingest_teachers`                    | Create teacher records                        |
| `TeacherRedBlockDAO` | `_ingest_teachers`                    | Create teacher unavailability slots           |
| `DegreeDAO`          | `_ingest_classes`                     | Create degree records                         |
| `YearDAO`            | `_ingest_classes`, `_ingest_sessions` | Create year records, look up years by degree  |
| `ClassDAO`           | `_ingest_classes`, `_ingest_sessions` | Create class records, look up classes by code |
| `RoomDAO`            | `_ingest_rooms`, `_ingest_sessions`   | Create room records, look up rooms by name    |
| `RoomRedBlockDAO`    | `_ingest_rooms`                       | Create room unavailability slots              |
| `SubjectDAO`         | `_ingest_sessions`, `_ingest_shifts`  | Create/look up subject records                |
| `SessionDAO`         | `_ingest_sessions`, `_ingest_shifts`  | Create/look up session records                |
