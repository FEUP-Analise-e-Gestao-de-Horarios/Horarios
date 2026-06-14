# Exporter Summary

## What was done

The project now has an exporter flow that turns timetable edits into a readable export plan. The backend compares each project's `initial_database.db` with its edited `general_database.db`, detects session additions/removals, finds resource conflicts, and builds ordered modification steps for changed sessions.

The main backend work lives in `backend/src/exporter/` and in the export endpoint at `backend/src/projects/views/export.py`. The endpoint returns:

- added and removed sessions;
- room conflicts;
- teacher conflicts;
- class conflicts;
- ordered modification steps.

Conflict detection was improved through `ConflictResourceDAO`, which clusters overlapping allocations by resource, week, weekday, start time, and duration. Repeated weekly conflicts are grouped together, with `weeks`, `session_ids`, and a `collisions` count included in the response.

The modification planner was implemented with graph logic in `ExportGraph`. It builds resource graphs for rooms, teachers, and classes, then derives a dependency graph between changed sessions. This lets the exporter order changes so a session that needs an occupied slot is shown after the blocking session has moved. Cycles that represent exact time swaps are classified as `exchange`; other changes are classified as `move`.

Recurring sessions are grouped by original block and shared changes. The export payload includes week ranges, whether a change applies to all weeks of the original block, dependencies, and a representative session snapshot for display.

The frontend now has an exporter page at `frontend/src/pages/ExporterPage.tsx` with UI components under `frontend/src/components/exporter/`. It shows export status, conflict summaries, modification steps, dependencies, and relation details in a clearer format.

A plain text export was added in `frontend/src/utils/exportPlainText.ts`. The UI exposes this through an `Exportar texto` button, generating a `.txt` file with:

- a summary of added/removed sessions and modification steps;
- added sessions;
- removed sessions;
- the ordered modification plan;
- dependencies between steps when relevant.

A helper script, `scripts/generate-exporter-changes.py`, was added to create artificial exporter-visible changes in a project's `general_database.db`. This is useful for testing the exporter with realistic added, removed, and modified sessions without changing the initial database.

Tests were added around exporter behavior in `backend/src/exporter/tests.py`, covering exchange classification and full-week vs partial-week recurring block detection.

## What is the exporter?

The exporter is the part of the system that explains how a timetable changed.

Instead of only saying that the database is different, it converts the difference between the original timetable and the edited timetable into structured, human-readable export data. Its job is to answer questions like:

- Which sessions were added?
- Which sessions were removed?
- Which sessions changed time, day, week, room, teacher, or class/subject relation?
- Are there conflicts after the changes?
- In what order should changes be applied?
- Are some changes simple moves or actual exchanges between sessions?
- Do repeated weekly sessions change in every week or only in some weeks?

The exporter starts from two databases:

- `initial_database.db`: the original imported timetable;
- `general_database.db`: the current edited timetable.

The backend compares those databases and produces an export payload. The frontend then renders that payload in the export page and can download it as plain text.

Conceptually, the exporter has four responsibilities:

1. **Diffing**
   It finds added, removed, and modified sessions by comparing the initial and current project databases.

2. **Conflict detection**
   It checks whether rooms, teachers, or classes are assigned to overlapping sessions. Overlaps are grouped into conflict windows and repeated weekly conflicts are clustered together.

3. **Change ordering**
   It builds dependency graphs so modification steps are shown in a useful order. If one changed session wants to move into a slot currently used by another changed session, that relationship becomes a dependency.

4. **Presentation data**
   It shapes the result for the frontend, including labels, week ranges, dependencies, session snapshots, and `move` or `exchange` step types.

The exporter does not directly publish the timetable to another external system. In the current implementation, it prepares the information needed for humans or another later integration to apply, inspect, or share the schedule changes safely.
