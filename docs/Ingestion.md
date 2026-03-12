# Ingestion Pipeline

This document describes how schedule data is fetched from the institution's website and persisted into a project's SQLite database.

For domain terminology (Degree, Group, Subject, Session, Red Block, etc.) see [Glossary](Glossary.md).

---

## Overview

The ingestion pipeline is orchestrated by `IngestionManager` (`src/ingestion/manager.py`). Given a project ID, it:

1. Opens the project's SQLite database.
2. Drives a `Scraper` to fetch and parse HTML pages from the institution's schedule website.
3. Delegates persistence to the functions in `src/ingestion/ingestors/`.
4. Runs post-processing steps to clean up and enrich the stored data.

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

### Phase 2 — Pre-populate Red Blocks

`pre_insert_red_blocks()` fills the `blocosVermelhos` table with every possible (weekday, time) combination before any scraping begins:

- **Days:** Monday through Saturday (`Segunda` → `Sábado`)
- **Slots:** every 30 minutes from 08:00 to 22:30 (encoded as integers: `800`, `830`, …, `2230`)

This creates a fixed reference table so that later red-block links from teachers, groups, and rooms can be resolved with a simple foreign-key lookup.

---

### Phase 3 — Menu Parsing

`Scraper.read_menu()` drives a two-step fetch:

1. Fetches the root URL and extracts the `<frame name="links">` src to find the navigation menu page.
2. Fetches the menu page and locates three `<li>` sections — **Docentes**, **Turmas**, **Salas** — producing:
    - A flat list of teacher page URLs.
    - A structured `Degree → Year → Group → week URLs` hierarchy.
    - A list of room metadata + timetable URLs.

The three results are passed directly into Phases 4–6.

---

### Phase 4 — Ingest Teachers

For each teacher URL:

1. Fetch the teacher page (`Scraper.get_teacher_page`).
2. Parse the `<td class="cabtitulo">` element to extract acronym, full name, and numeric code.
3. Parse red blocks (cells with class `td_vermelha`).
4. Insert the teacher into `docentes` (skipping duplicates).
5. For each red block, look up its ID in `blocosVermelhos` and insert into `blocoDocente`.

---

### Phase 5 — Ingest Groups

**5a — Degrees and groups**

All degrees are inserted into `curso` first. Then, for each degree → year → group:

- The group is inserted into `turmas`.
- All weekly schedule pages are fetched (`Scraper.get_group_page`), one URL per week range.

**5b — Red blocks** (from the first page only)

Red blocks are the same across all weeks for a given group, so only the first page is parsed for them. Each block is linked via `blocoTurma`.

**5c — Subjects and sessions** (for every page)

- Subjects are parsed from table index 4 and inserted into `uc` (skipping duplicates).
- Sessions (cells matching `td_tipologia_*`) are parsed from the main timetable:
    - Each session block contains: subject acronym, weekday, start time, duration (rowspan), teacher acronyms, group codes, and room names.
    - Teacher acronyms are resolved to numeric codes via the teachers table (index 3) on the same page.
    - Each session is inserted into `aula`, then linked into:
        - `aulaUC` (session ↔ subject)
        - `aulaDocente` (session ↔ teacher, one row per teacher)
        - `aulaTurmas` (session ↔ group, one row per group)
        - `aulaSala` (session ↔ room, one row per room)
        - `turmaUC` (group ↔ subject membership)
    - Theoretical sessions (CSS class `td_tipologia_19`) are also recorded in the in-memory `subject_shifts_map` for shift assignment in Phase 7.

---

### Phase 6 — Ingest Rooms

For each room entry from the menu:

1. Insert the room into `salas` using static metadata from the `ROOMS` registry (`src/ingestion/rooms.py`). Rooms not present in the registry default to `"Desconhecido"` for type, size, and seat count.
2. For each timetable URL, fetch the page and extract red blocks.
3. Link each red block via `salaBloco`.

---

### Phase 7 — Ingest Subject Shifts

The `subject_shifts_map` (built during Phase 5c) is structured as:

```
degree_acronym → year → subject_code → shift_number → [group_codes]
```

Each unique group of groups attending the same theoretical session for a subject constitutes one shift. Shifts are numbered 1..N in ascending order of each shift's minimum group code.

`_ingest_subject_shifts()` flushes this map into the `turno` table, skipping (group, subject) pairs that already have a row.

---

### Phase 8 — Post-processing

#### 8a — Fix groups without shifts (`_fix_groups_without_shifts`)

Queries for every (group, subject) pair present in `turmaUC` that has no corresponding row in `turno`. For each gap, a placeholder shift with `numero = 0` is inserted. This ensures every group–subject pair has at least one shift record.

#### 8b — Clean up duplicate sessions (`_cleanup_sessions`)

Scraping multiple weekly pages for the same group often produces duplicate session records — identical in schedule attributes but covering different (sometimes overlapping) week ranges. This step merges them:

1. Fetches all distinct session signatures: `(day, time, duration, type, teacher, subject, group)`.
2. For each signature, collects all matching `aula` rows.
3. While any two rows overlap in date range (or fall within one week of each other), the pair with the earliest start date is merged into a single record spanning the union of both ranges. The redundant row is deleted from `aula`, `aulaDocente`, `aulaUC`, `aulaSala`, and `aulaTurmas`.

#### 8c — Find simultaneous classes (`_find_simultaneous_classes`)

Detects pairs of sessions that share the same teacher, room, weekday, start time, and overlapping week ranges but belong to **different subjects**. Each such pair is inserted into `aulasSimultaneas`. Pairs `(A, B)` and `(B, A)` are deduplicated at the SQL level using `a2.id > a1.id`.

---

### Phase 9 — Teardown

**On success:**

- `general_database.db` is copied to `initial_database.db` as a read-only baseline snapshot.
- `finished_ingestion_at` is stamped on the `Project` record.

**On failure (any exception):**

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
├── utils.py            # pre_insert_red_blocks, check_date_range_overlap
│
├── parsers/            # HTML → Python data structures
│   ├── menu.py         # extract_menu_link, extract_menu_tags,
│   │                   # extract_teacher_links, extract_sessions_info,
│   │                   # extract_rooms_info
│   ├── teacher_page.py # extract_teacher_info
│   ├── section_page.py # extract_week_dates, extract_subjects, extract_sessions
│   ├── red_blocks.py   # extract_red_blocks
│   └── utils.py        # matrix_from_html_table, get_cell_column,
│                       # get_weekday_at_column
│
├── ingestors/          # Python data structures → SQLite
│   ├── teachers.py     # ingest_teacher, ingest_teacher_red_blocks
│   ├── sections.py     # ingest_degree, ingest_group,
│   │                   # ingest_group_red_blocks, ingest_subject,
│   │                   # ingest_session
│   └── rooms.py        # ingest_room, ingest_room_red_blocks
│
└── schemas/            # TypedDict / type alias definitions
    ├── misc.py         # Matrix, Time, WeekDay, RedBlock, TurnosMap
    ├── sections.py     # Degree, Year, GroupLinks, GroupPage,
    │                   # Subject, Session
    ├── rooms.py        # RoomLinks
    └── teachers.py     # TeacherPage
```

---

## Database Tables Written

| Table              | Written by                   | Content                                      |
| ------------------ | ---------------------------- | -------------------------------------------- |
| `blocosVermelhos`  | `pre_insert_red_blocks`      | All (weekday, time) slot combinations        |
| `docentes`         | `ingest_teacher`             | Teacher records                              |
| `blocoDocente`     | `ingest_teacher_red_blocks`  | Teacher ↔ unavailable slot links             |
| `curso`            | `ingest_degree`              | Degree records                               |
| `turmas`           | `ingest_group`               | Group records                                |
| `blocoTurma`       | `ingest_group_red_blocks`    | Group ↔ unavailable slot links               |
| `uc`               | `ingest_subject`             | Subject (UC) records                         |
| `aula`             | `ingest_session`             | Session records                              |
| `aulaUC`           | `ingest_session`             | Session ↔ subject links                      |
| `aulaDocente`      | `ingest_session`             | Session ↔ teacher links                      |
| `aulaTurmas`       | `ingest_session`             | Session ↔ group links                        |
| `aulaSala`         | `ingest_session`             | Session ↔ room links                         |
| `turmaUC`          | `ingest_session`             | Group ↔ subject membership                   |
| `salas`            | `ingest_room`                | Room records                                 |
| `salaBloco`        | `ingest_room_red_blocks`     | Room ↔ unavailable slot links                |
| `turno`            | `_ingest_subject_shifts`     | Subject shift assignments                    |
| `aulasSimultaneas` | `_find_simultaneous_classes` | Pairs of simultaneous cross-subject sessions |
