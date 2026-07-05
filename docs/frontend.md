# Frontend

The frontend is a single-page React application that serves every user-facing page of the
schedule editor. Django is a pure JSON API (`/api/`) plus admin panel (`/admin/`); React
Router owns all other navigation. For the history of how the app moved from Django templates
to React, and how the two are wired together in dev and prod, see
[Frontend Migration](refactors/frontend.md).

For canonical naming of domain concepts (Degree, Class, Subject, Session, etc.) see the
[Glossary](glossary.md).

## Tech Stack

| Tool                      | Version | Role                                                       |
| ------------------------- | ------- | ---------------------------------------------------------- |
| React                     | 19      | UI library                                                 |
| TypeScript                | 6       | Language, strict typing                                    |
| Vite                      | 8       | Dev server (HMR) and production bundler                    |
| React Router              | 7       | Client-side routing (`createBrowserRouter`)                |
| TanStack Query            | 5       | Server-state caching, fetching, and mutations             |
| TanStack Virtual          | 3       | Row virtualization for large tables                        |
| Tailwind CSS              | 4       | Styling (via `@tailwindcss/vite`, no separate PostCSS)     |
| lucide-react              | 1       | Icon set                                                   |
| Vitest                    | 4       | Unit tests (`node` environment)                            |
| ESLint + Prettier         | 9 / 3   | Linting (type-aware) and formatting                        |

There is no global client-state library (Redux, Zustand, etc.). Server state lives in
TanStack Query; the small amount of UI state lives in component hooks and the URL.

## Directory Structure

All application code lives under `frontend/src/`:

```
frontend/src/
├── main.tsx              # App entry: mounts RouterProvider + QueryClientProvider
├── router.tsx            # Route table (createBrowserRouter)
├── routes.ts             # ROUTES path-template constants
├── index.css             # Tailwind entry + global styles
├── api/                  # Data-fetching layer (see "API & Data Fetching")
│   ├── client.ts         # Typed fetch wrapper (CSRF, JSON, error unwrapping)
│   ├── auth.ts           # Router loaders: requireAuth / redirectIfAuthenticated
│   ├── queryClient.ts    # Configured TanStack QueryClient
│   ├── queryKeys.ts      # Centralized query-key factory
│   └── hooks/            # React-query hooks
│       ├── useAuth.ts    # login / logout / change & forgot password mutations
│       ├── useProjects.ts# project list + create/rename/delete mutations
│       └── project/      # per-resource hooks (degree, year, subject, class,
│                         #   teacher, room, sessions, project)
├── pages/                # One component per route
│   ├── HomePage.tsx
│   ├── SchedulePage.tsx
│   ├── auth/             # LoginPage, ForgotPasswordPage, ChangePasswordPage
│   └── dashboard/        # DashboardPage + {Degree,Teacher,Room,Subject,Class}DetailPage
├── components/           # Reusable UI, grouped by feature
│   ├── AltClickCopy.tsx  # Global Alt+click-to-copy-id helper (mounted at root)
│   ├── auth/             # Auth form building blocks (FormCard, PasswordField, …)
│   ├── home/             # Project list cards + new-project modal
│   ├── dashboard/        # Navbar, tabs, stat cards, week grid, session popup
│   └── schedule/         # Schedule grid, drawers, dropdowns, and their hooks
├── types/                # TypeScript domain & API types
│   ├── api.ts            # ApiResponse<T>, ApiError codes, ApiRequestError
│   ├── user.ts
│   └── project/          # degree, year, subject, class, teacher, room,
│                         #   sessions, conflicts, red_block, weekday, project
├── utils/                # Framework-agnostic helpers (date, time, weekdays,
│                         #   search, scheduleEvents, scheduleView, routes)
└── assets/               # Static images bundled by Vite (hero.png, …)
```

Most non-trivial behaviour in `components/schedule/` is split into custom hooks
(`useEventEditor`, `useScheduleFilters`, `useScheduleViewUrl`, `useTurnoTurmaSync`,
`useColumnResize`, …) so the page components stay declarative. Pure logic that is unit
tested lives next to its consumer as `*.ts` with a sibling `*.test.ts` (e.g.
`scheduleGrid.ts` / `scheduleGrid.test.ts`).

The `@` import alias resolves to `frontend/src/` (configured in both `vite.config.ts` and
`tsconfig`), so modules are imported as `@/api/client`, `@/components/schedule/WeekGrid`, etc.

## Routing

Routes are declared in two files so that the path strings have a single source of truth:

- `src/routes.ts` exports the `ROUTES` object — path templates such as
  `"/projects/:projectId/dashboard/degrees/:degreeId"`.
- `src/router.tsx` builds the `createBrowserRouter` table, mapping each `ROUTES` entry to a
  page component and a loader.

| Route key         | Path                                                  | Page                  |
| ----------------- | ----------------------------------------------------- | --------------------- |
| `HOME`            | `/`                                                   | `HomePage`            |
| `LOGIN`           | `/login`                                              | `LoginPage`           |
| `FORGOT_PASSWORD` | `/forgot-password`                                    | `ForgotPasswordPage`  |
| `CHANGE_PASSWORD` | `/change-password`                                    | `ChangePasswordPage`  |
| `SCHEDULE`        | `/projects/:projectId`                                | `SchedulePage`        |
| `DASHBOARD`       | `/projects/:projectId/dashboard`                      | `DashboardPage`       |
| `DEGREE_DETAIL`   | `/projects/:projectId/dashboard/degrees/:degreeId`    | `DegreeDetailPage`    |
| `TEACHER_DETAIL`  | `/projects/:projectId/dashboard/teachers/:teacherId`  | `TeacherDetailPage`   |
| `ROOM_DETAIL`     | `/projects/:projectId/dashboard/rooms/:roomId`        | `RoomDetailPage`      |
| `SUBJECT_DETAIL`  | `/projects/:projectId/dashboard/subjects/:subjectId`  | `SubjectDetailPage`   |
| `CLASS_DETAIL`    | `/projects/:projectId/dashboard/classes/:classId`     | `ClassDetailPage`     |

To build a concrete URL from a template, use `buildPath` from `src/utils/routes.ts`, which
is type-safe in its parameter names:

```ts
buildPath(ROUTES.DEGREE_DETAIL, { projectId, degreeId });
```

> Every path delegated to Django's `spa_view` in `backend/src/config/urls.py` must have a
> matching entry here, and vice versa. A mismatch renders a blank page with no error.

## Authentication

Auth is **Django session cookies**, not JWT — the frontend and backend share an origin in
both dev and prod, so the session cookie just works (see
[Frontend Migration](refactors/frontend.md)).

Route protection is enforced by **React Router loaders** defined in `src/api/auth.ts`:

| Loader                     | Used on                  | Behaviour                                                              |
| -------------------------- | ------------------------ | --------------------------------------------------------------------- |
| `requireAuth`              | All authenticated pages  | `GET /api/auth/me`; redirects to `/login` if not authenticated        |
| `redirectIfAuthenticated` | Login / forgot-password  | Redirects to `/` if already authenticated; otherwise primes the CSRF cookie |

Auth mutations live in `src/api/hooks/useAuth.ts`: `useLogin`, `useLogout`,
`useChangePassword`, `useForgotPassword`. Each hits the corresponding `/api/auth/*`
endpoint and is typed with the specific `ApiError` codes it can return.

### CSRF

`src/api/client.ts` reads the `csrftoken` cookie that Django sets and attaches it as the
`X-CSRFToken` header on every mutating request (`POST`/`PUT`/`PATCH`/`DELETE`). All requests
are sent with `credentials: "same-origin"` so the session cookie is included.

## API & Data Fetching

### The fetch wrapper (`src/api/client.ts`)

A small typed wrapper around `fetch` exposes `api.get/post/put/patch/delete` plus
`api.getData`. It:

- serializes the body to JSON and sets the `Content-Type` / `X-CSRFToken` headers,
- on a non-2xx response, parses the error body and throws an `Error` augmented with
  `{ code, apiMessage, status }` (shaped as `ApiRequestError` in `src/types/api.ts`),
- `getData` additionally unwraps the standard `{ data: ... }` envelope (`ApiResponse<T>`)
  so call sites receive the payload directly.

### TanStack Query

`src/api/queryClient.ts` configures a single `QueryClient` (provided at the app root in
`main.tsx`) with these defaults:

| Option                 | Value     | Meaning                                        |
| ---------------------- | --------- | ---------------------------------------------- |
| `staleTime`            | 2 min     | Data considered fresh for 2 minutes            |
| `gcTime`               | 5 min     | Unused cache entries garbage-collected after 5 min |
| `retry` (queries)      | 1         | One retry on failure                           |
| `refetchOnWindowFocus` | `true`    | Refetch when the tab regains focus             |
| `retry` (mutations)    | `false`   | Mutations are not retried                      |

### Query keys

All query keys are produced by the factory in `src/api/queryKeys.ts` (`queryKeys.projects.*`)
rather than written inline, which keeps cache invalidation consistent. Keys are hierarchical
(`["projects", id, "degrees", degreeId]`), so invalidating `queryKeys.projects.all` cascades.
The `sessions` key folds the active filters into the key and **sorts** the id/weekday arrays
so that filter order does not fragment the cache.

### Hooks

Data access is wrapped in feature hooks under `src/api/hooks/`:

- `useProjects.ts` — `useProjects` (list, with adaptive `refetchInterval`: polls every 5 s
  while any project is still being ingested), plus `useCreateProject`, `useRenameProject`,
  `useDeleteProject` mutations that invalidate the project list `onSuccess`.
- `useAuth.ts` — the auth mutations described above.
- `hooks/project/*` — one module per resource (`degree`, `year`, `subject`, `class`,
  `teacher`, `room`, `sessions`, `project`) exposing list/detail query hooks, e.g.
  `useProjectDegrees`, `useProjectDegree`, `useProjectSessions`.

`useProjectSessions` is representative of a filtered query: it builds the query string from
`SessionsQueryFilters`, calls `api.getData`, and is `enabled` only once `projectId` and a
selected `yearId` are present.

## Building & Running

The frontend is part of the Docker dev stack — see the [Setup Guide](setup.md) for the
recommended `make dev` workflow that runs frontend and backend together. To work on the
frontend directly:

```sh
cd frontend
npm install        # or: make local-setup at the repo root
npm run dev        # Vite dev server on http://localhost:5173
```

In dev, Vite proxies `/api/` to the Django backend (`http://localhost:8000`, or the
`BACKEND_HOST` env var inside Docker — see `vite.config.ts`); everything else is served by
Vite so React Router and asset paths resolve from the root.

### npm scripts

| Script                | Command                | Purpose                                         |
| --------------------- | ---------------------- | ----------------------------------------------- |
| `npm run dev`         | `vite`                 | Start the dev server with HMR                   |
| `npm run build`       | `tsc -b && vite build` | Type-check, then produce the production bundle  |
| `npm run preview`     | `vite preview`         | Serve the production build locally              |
| `npm run typecheck`   | `tsc -b --noEmit`      | Type-check without emitting                     |
| `npm run lint`        | `eslint .`             | Lint (fails on any warning)                     |
| `npm run lint:fix`    | `eslint . --fix`       | Lint and auto-fix                               |
| `npm run format`      | `prettier --write .`   | Format the codebase                             |
| `npm run test`        | `vitest run`           | Run the unit test suite once                    |
| `npm run test:watch`  | `vitest`               | Run tests in watch mode                         |

### Production build

`npm run build` emits to `frontend/dist/` with a `/static/frontend/` base path (set in
`vite.config.ts`). The project Dockerfile copies that output into Django's static directory,
where `collectstatic` picks it up and `spa_view` serves the resulting `index.html`. The full
dev/prod integration is described in [Frontend Migration](refactors/frontend.md).
