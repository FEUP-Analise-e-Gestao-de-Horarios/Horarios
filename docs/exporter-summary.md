# Exporter Summary

## Overview

The exporter is the feature that turns timetable edits into a structured change report. Instead of only knowing that the current project database differs from the imported timetable, the system computes a domain-specific export payload that answers four practical questions:

- what sessions were added or removed;
- which resources are now in conflict;
- which modified sessions must move before others;
- how those changes should be presented to a user reviewing the timetable.

In this project, the exporter is not yet a direct integration with an external scheduling system. Its current role is to generate a reliable, human-readable description of timetable changes that can be inspected in the UI and downloaded as plain text.

The end-to-end flow is:

1. the frontend calls `POST /api/projects/<project_id>/export`;
2. the backend compares `general_database.db` against `initial_database.db`;
3. the backend computes added/removed sessions, resource conflicts, and ordered modification steps;
4. the backend compacts and caches the payload;
5. the frontend requests the compact payload, expands it client-side, and renders the exporter page;
6. the same frontend data model also powers the plain-text download.

## Data Sources

The exporter works from the two timetable databases stored per project:

- `initial_database.db`: the imported baseline timetable;
- `general_database.db`: the current editable timetable after user changes.

The comparison is always relative to those two databases. That matters because the exporter is not reconstructing history from a log of edits. It infers the current change set by diffing the baseline and edited states.

## Backend Entry Point

The main HTTP entry point is `backend/src/projects/views/export.py`, implemented by `ProjectExportView`.

Its responsibilities are:

- verify that the user is authenticated;
- verify that the project exists;
- parse the JSON request body;
- read `recalculate_export_graph` to decide whether to reuse cached exporter data or recompute it;
- read `payload_format` and return either compact or expanded output, defaulting to compact;
- load and store exporter cache entries in the project database.

The frontend currently sends:

```json
{
  "recalculate_export_graph": false,
  "payload_format": "compact"
}
```

If a valid cached payload already exists and recalculation is not requested, the view returns it immediately with the message `"Project export loaded from cache"`. If not, it recomputes the export, stores the compact result in cache, and returns the formatted payload.

## Backend Pipeline

### 1. Project database setup

The exporter initializes the SQLAlchemy engine for the project's `general_database.db` and opens a session on that database. Inside that session it also attaches `initial_database.db` under a SQLite alias so both copies of the timetable can be queried from the same connection.

This attached-database strategy is what allows the exporter to compare the same tables across the baseline and edited states using direct SQLite `EXCEPT` queries and per-record diffs.

### 2. Added and removed sessions

Added and removed sessions are computed by `SessionDAO.get_added_removed_records()`.

This logic compares the `sessions` table in `main` and the attached initial database and returns:

- `added`: session ids present only in `general_database.db`;
- `removed`: session ids present only in `initial_database.db`.

At this layer the exporter intentionally keeps the added/removed payload minimal. For sessions it currently returns only ids, which is enough for the UI counts and for later expansion if needed.

### 3. Field-level modifications

Modified sessions are computed by `SessionDAO.get_changes_only()`. This starts from the generic record diffing logic in `BaseDAO.get_changes_only()`, which:

- matches rows present in both databases by primary key;
- compares non-primary-key columns;
- records only fields whose values differ;
- stores each field diff as `{ "old": ..., "new": ... }`.

`SessionDAO` then enriches that base diff with session-specific relation changes:

- room changes from `session_rooms`;
- teacher changes from `session_teachers`;
- class-subject relation changes from `session_class_subjects`.

Those relation changes are reshaped into exporter-friendly buckets:

- `rooms: { added: [...], removed: [...] }`
- `teachers: { added: [...], removed: [...] }`
- `class_subjects: { added: [...], removed: [...] }`

The enrichment step also resolves display data from related tables, such as:

- room name, type, size, and seats;
- teacher number, acronym, and name;
- class code and shift;
- subject number, code, acronym, and name.

The class-subject pair is kept together deliberately so the exporter does not misreport a subject reassignment as separate unrelated class and subject changes.

### 4. Conflict detection

Conflict detection is delegated to resource-specific DAOs backed by the shared `ConflictResourceDAO` in `backend/src/projects/projects_db/dao/conflict_resource_dao.py`.

The exporter computes three conflict families:

- `rooms_conflicts`;
- `teacher_conflicts`;
- `classes_conflicts`.

The shared conflict algorithm works in several passes:

1. query all scheduled allocations for one resource kind;
2. bucket rows by resource identity, week, and weekday;
3. convert timetable slots into minute ranges;
4. cluster overlapping rows into one conflict window;
5. discard clusters that contain only one session;
6. group equivalent weekly conflicts across recurring weeks;
7. add `subject_labels` so the frontend can show useful subject context inside the conflict card.

Each grouped conflict row carries:

- the resource identity and display label;
- a representative `week`;
- optional `weeks` for recurring grouped conflicts;
- `weekday`, `start_time`, and `duration`;
- `session_ids` participating in the overlap;
- `collisions`, representing the maximum number of simultaneous sessions in the grouped window;
- `subject_labels`, used to make the UI more readable.

This design is important because the exporter does not simply flag pairwise overlaps. It tries to present resource conflicts as a single human-readable time window, even when the same pattern repeats across multiple weeks.

### 5. Modification ordering with dependency graphs

The most specialized backend logic lives in `backend/src/exporter/export_graph.py`.

Its job is not just to list changed sessions, but to answer the harder question: in what order should the user conceptually apply those changes?

To do that, `ExportGraph`:

- loads the current session snapshots for all changed sessions from `general_database.db`;
- loads the initial snapshots for the same sessions from `initial_database.db`;
- loads all weeks that belong to the original recurring block of each changed session;
- builds movement information for time and resources;
- loads only the current resource occupancy nodes that are relevant to the changed sessions;
- builds dependency graphs over rooms, teachers, and classes;
- condenses those graphs into ordered change groups.

#### Session snapshots and scoped loading

Snapshot loading is handled by `ExportGraphSnapshotLoader` in `backend/src/exporter/export_graph_loaders.py`.

For each changed session, the loader builds a public snapshot that includes:

- id and original block id;
- week, weekday, start time, and duration;
- room names;
- teacher public details;
- class codes;
- subject details.

Internally, it also keeps normalized room, teacher, and class ids so graph construction can reason about resource occupancy without exposing those helper fields in the final API response.

`ResourceOccupancyLoader` then loads only the resource/time nodes that the dependency algorithm actually needs. This is an optimization: the exporter does not build occupancy for the whole timetable, only for the specific old slots touched by changed sessions.

#### Movement edges

For each changed session, the exporter reconstructs:

- the old time placement from the diff plus the initial snapshot;
- the new time placement from the current snapshot;
- the old and new resource sets for rooms, teachers, and classes.

It then creates directed movement edges inside three resource graphs:

- room graph;
- teacher graph;
- class graph.

An edge encodes that a session is leaving one occupied slot and wants to occupy another slot for that resource.

#### Dependency graph

After the resource graphs are built, the exporter derives a session-level dependency graph.

The edge direction is:

- `moving_change -> blocking_change`

That means session A depends on session B when A wants to move into a slot that B currently occupies. This makes the graph meaningful for export ordering:

- if there is no cycle, a topological order gives a safe sequence of moves;
- if there is a cycle, the exporter checks whether it is an exact time-slot exchange.

#### `move` versus `exchange`

Strongly connected components are grouped together. A group becomes:

- `exchange` if all sessions in the cycle swap exact old and new time placements;
- `move` otherwise.

This distinction is what allows the frontend to present a genuine timetable swap differently from a normal relocation.

#### Grouping recurring changes

The exporter does not always emit one step per changed row. If multiple changed rows belong to the same recurring block and share the same meaningful modifications, they are grouped into a single export step.

That grouping key is based on:

- `original_block_id`;
- the set of groupable changes, excluding the raw `week` diff.

This is a deliberate presentation choice. Different weeks inside the same recurring block naturally differ by date, so keeping `week` in the grouping key would split a recurring modification back into separate rows even when the user expects one grouped change.

Each final modification step includes:

- `type`: `move` or `exchange`;
- `original_block_id`;
- `session_ids` participating in the grouped step;
- `weeks`;
- `week_range` with `start`, `end`, and `contiguous`;
- `applies_to_all_weeks`;
- `modifications`;
- `dependencies`;
- a representative `session` snapshot for display.

`week_range` is considered contiguous only when consecutive weeks are exactly seven days apart.

### 6. Cached modification steps

The exporter has two caching layers inside the project database.

The first is the full export payload cache, managed by `ExportCacheDAO`:

- cache key: `project_export`;
- payload stored as JSON text;
- table created automatically if the project database predates the cache model.

The second is the cached modification-step table, managed by `ModifiedSessionDAO`:

- it stores rendered modification steps per session;
- it de-duplicates steps by `step_key`;
- it preserves export order through `modification_number`.

In the current flow, if `recalculate_export_graph` is false, `ProjectExportView` first attempts to reuse the full cached payload. If it must recompute, it may still reuse cached modification steps from `modified_sessions` unless recalculation was explicitly requested.

This split exists because modification ordering used to be a significant portion of exporter cost. Caching the final rendered steps and the full transport payload prevents repeated graph work on warm loads.

## Payload Shape and Compact Transport

The canonical API schemas live in `backend/src/exporter/schemas.py`.

There are two payload shapes:

- `ProjectExportPayload`: the expanded, legacy frontend-facing view model;
- `CompactProjectExportPayload`: the compact transport/cache format used by the current request path.

### Expanded payload

The expanded payload contains:

- `added_removed_sessions`;
- `rooms_conflicts`;
- `teacher_conflicts`;
- `classes_conflicts`;
- `modification_steps`.

This is the easiest shape to understand, because all repeated display data is already embedded directly in each record.

### Compact payload

The compact format is implemented in `backend/src/exporter/compact_payload.py` and marked with:

- `format: "compact_export_v1"`

Instead of repeating room, teacher, class, subject, and session data in every conflict row and every modification step, the compact payload separates that information into entity maps:

- `entities.rooms`
- `entities.teachers`
- `entities.classes`
- `entities.subjects`
- `entities.sessions`

Conflicts then become compact tuples of:

- resource kind;
- resource id;
- week;
- recurring weeks;
- weekday;
- start time;
- duration;
- collisions;
- session ids;
- optional subject labels.

Modification steps also become lighter because the full representative session snapshot is moved into `entities.sessions`.

This compact representation serves two purposes:

- reduce repeated payload size over the API;
- make the cached exporter payload the same structure that the backend already wants to store.

The backend can still expand compact payloads again when a caller requests `payload_format: "expanded"`.

## Frontend Fetch and Data Expansion

The frontend exporter page lives in `frontend/src/pages/ExporterPage.tsx`.

The page uses:

- `useProject()` to load project metadata for the page title and navbar;
- `useProjectExport()` to fetch exporter data.

`useProjectExport()` is defined in `frontend/src/api/hooks/useDashboard.ts`. It always requests the compact payload:

```ts
api.post(`/api/projects/${projectId}/export`, {
  recalculate_export_graph: shouldRecalculate,
  payload_format: "compact",
});
```

After the response arrives, the hook converts it into the expanded frontend model with `compactExportToProjectExportPayload()` from `frontend/src/utils/exporter/exportCompact.ts`.

That client-side expansion:

- splits compact conflicts back into room, teacher, and class arrays;
- resolves referenced entities from the compact maps;
- restores representative session snapshots for modification steps;
- expands relation-change payloads for rooms, teachers, and class-subject pairs.

The practical result is that the React UI can continue working with a rich, readable `ProjectExportPayload` while the network and cache layers stay compact.

## Frontend Rendering Flow

### 1. Page shell

`ExporterPage.tsx` renders the page shell and passes the export query state into `ExportStatusSection`.

It also persists exporter scroll position in `sessionStorage`, keyed by project id. That state is only restored when returning to the page without a more specific selected-conflict target.

### 2. Status section

`frontend/src/components/exporter/ExportStatusSection.tsx` is the top-level UI wrapper for the exporter content.

It handles:

- loading state;
- error state;
- success state;
- the `Recalcular` button;
- the `Exportar texto` button.

On success it renders `ExportResults`.

### 3. Results composition

`frontend/src/components/exporter/ExportResults.tsx` assembles the main exporter sections:

- summary stats;
- conflicts;
- added/removed sessions;
- modification plan.

Before rendering, it derives several helper structures from the payload:

- grouped modification-plan items with `buildModificationPlanItems()`;
- dependency lookup with `buildDependencyLookup()`;
- set of session ids involved in conflicts with `buildConflictSessionIds()`;
- lookup from changed session id to the first matching conflict card with `buildConflictLookup()`.

These helpers allow the UI to cross-link change steps and conflicts without changing the backend payload.

### 4. Summary stats

`ExporterStats.tsx` renders top-level counts for:

- steps;
- changes;
- added sessions;
- removed sessions;
- conflicts.

This gives the user an immediate high-level read of the export result before they inspect details.

### 5. Conflicts section

`ExporterConflictsSection.tsx` renders separate columns for:

- room conflicts;
- teacher conflicts;
- class conflicts.

Each conflict row is rendered by `ConflictRows.tsx` as a real clickable `Link`, not just a styled card. The card shows:

- the resource label;
- optional subject labels;
- recurring week label;
- weekday;
- start time;
- number of impacted sessions.

Each card links to the corresponding timetable detail view for the affected resource, using helpers from `frontend/src/utils/exporter/conflictLinks.ts`.

Those helpers build URLs for:

- room detail route;
- teacher detail route;
- class detail route.

They also append query parameters describing the conflicting weeks and sessions so the destination timetable can open on the correct context and highlight the relevant sessions.

### 6. Exporter-specific navigation state

Exporter navigation state is handled by `useExporterNavigationState()` plus utility helpers in `frontend/src/utils/exporter/pageState.ts`.

This layer persists:

- whether the conflicts section is open;
- which conflict card was clicked before navigation away from the exporter;
- the exporter scroll position.

It also provides smooth-scroll highlighting for:

- jumping from a dependency reference to another modification step;
- jumping from a modification step with an unresolved conflict to the matching conflict card;
- restoring the previously selected conflict card when the user returns from a timetable detail page.

That navigation work matters because the exporter is meant to be investigatory. A user often clicks from a conflict card into a timetable, then needs to come back to the same card and continue reviewing the export.

### 7. Modification plan rendering

The modification plan UI lives mainly in `ModificationPlanSection.tsx` and related components under `frontend/src/components/exporter/modification-plan/`.

It renders one card per plan item, where a plan item is either:

- a single step;
- a clustered exchange group.

`buildModificationPlanItems()` groups exchange steps that depend on each other into one UI cluster. This prevents a multi-session swap from being shown as unrelated separate cards.

Each step card shows:

- whether it is `Mover` or `Troca`;
- the representative session title built from classes, subjects, weekday, and start time;
- whether it applies only to selected weeks;
- the session attributes in a collapsible detail block;
- field-by-field modifications;
- dependency links to later steps;
- an unresolved conflict warning if the changed session still appears in a conflict group.

Dependency links use anchor ids derived from session ids, so clicking a dependency highlights and scrolls to the relevant step card. Conflict warnings likewise jump back to the relevant conflict card inside the conflicts section.

### 8. Added and removed sessions

The exporter renders added and removed session groups in `AddedRemovedSessions.tsx`.

These rows are simpler than the modification-plan cards because they describe sessions that only exist on one side of the diff. They still serve an important role in the report because they cover changes that are not expressible as a move or exchange.

## Plain-Text Export

The downloadable text export is generated entirely on the frontend by `frontend/src/utils/exporter/exportPlainText.ts`.

It reuses the same computed helpers as the visual exporter:

- grouped modification-plan items;
- dependency lookup;
- conflict lookup;
- unresolved-conflict detection.

The text file currently contains:

- a title and generation timestamp;
- added-session and removed-session sections;
- the ordered modification plan;
- per-step detail lines for week scope, duration, visible dependencies, unresolved conflicts, and field-level changes.

The UI exposes this through the `Exportar texto` button in `ExportStatusSection.tsx`, which creates a Blob and downloads a file named like:

- `alteracoes-horario-YYYY-MM-DD.txt`

This is useful because the human-readable export is not tied to the browser view. The user can generate a shareable snapshot of the current timetable change set without a separate backend export format.

## Important Design Decisions

Several implementation choices define how the exporter behaves:

### Baseline-versus-current diffing

The exporter compares two full timetable states, not a mutation log. That keeps the feature robust even if edits happened through multiple UI paths, but it also means the export always describes the net effect, not the exact chronological history of user actions.

### Scoped dependency loading

The graph algorithm only loads resource occupancy for relevant nodes, which keeps graph construction focused on changed sessions instead of the entire timetable.

### Grouped recurring changes

Recurring sessions are grouped by original block and shared modifications, with explicit week metadata. This makes the report read more like timetable operations and less like raw row diffs.

### Compact transport

The compact payload avoids repeated transport of room, teacher, class, subject, and session display data. The frontend expands it back into a richer model for rendering.

### Dual caching

Caching exists both for the full transport payload and for rendered modification steps. This reduces repeated exporter cost on warm loads and avoids rebuilding the dependency graph unnecessarily.

## Supporting Files

Beyond the main request/response and UI files, a few supporting files are relevant to understanding or testing the exporter:

- `backend/src/exporter/export_graph_loaders.py`: loads snapshots and scoped occupancy for graph construction;
- `backend/src/exporter/export_graph_types.py`: shared typed structures for placements, resource movements, and graph nodes;
- `frontend/src/types/exporter.ts`: frontend type definitions for expanded and compact payloads;
- `frontend/src/utils/exporter/conflicts.ts`: conflict lookups and anchor generation;
- `frontend/src/utils/exporter/modificationPlan.ts`: exchange clustering and dependency label mapping;
- `frontend/src/utils/exporter/dashboardNavigation.ts`: detail-page helpers for conflict highlighting;
- `scripts/generate-exporter-changes.py`: helper script for creating exporter-visible changes in `general_database.db` for testing.

There are also exporter-focused tests in both backend and frontend utility files, including tests around compact expansion, conflict navigation helpers, modification-plan grouping, and plain-text generation.

## Current Scope and Limitations

The exporter is already a full end-to-end feature, but its scope is still bounded:

- it describes the current diff between baseline and edited timetable state, not an audit trail of user actions;
- it is designed for internal review and text export, not yet for direct publication into an external scheduling platform;
- added and removed sessions are currently represented more minimally than modification steps;
- dependency ordering is strongest for changed sessions that interact through rooms, teachers, or classes, which is exactly the domain the export graph models.

## Conclusion

From a backend perspective, the exporter is a pipeline that compares two timetable databases, detects conflicts, builds a dependency-aware change graph, groups recurring modifications, and stores a compact cached representation.

From a frontend perspective, it is a page that fetches the compact export, expands it into a rich view model, renders summaries, conflicts, and modification steps, preserves navigation state while the user investigates timetable details, and produces a downloadable plain-text report from the same data.

Taken together, the exporter is the project's explanation layer for timetable edits: it translates low-level database differences into an ordered, inspectable, report-ready description of schedule change.
