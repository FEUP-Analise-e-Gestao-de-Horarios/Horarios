# Frontend Migration to React

The frontend was originally built using Django templates with vanilla JavaScript. As the
application grew this approach became increasingly difficult to maintain — UI state was
managed by manually querying and mutating DOM elements, interactive features like schedule
editing required large amounts of brittle JavaScript, and there was no component reuse
across templates. Fixing a visual inconsistency or adding a new interactive feature meant
touching many unrelated files with no clear structure.

React was chosen as the replacement because its component model maps naturally onto the
domain: a schedule is a composition of rooms, time slots, and course assignments, all of
which translate cleanly into a tree of components with local state. It also has first-class
TypeScript support and a mature ecosystem for the kinds of UI patterns this project needs
(drag-and-drop, data tables, form management).

Vite was chosen as the build tool over Create React App, which is effectively abandoned.
Vite has near-instant HMR during development and produces optimized, content-hashed bundles
for production.

## How React is integrated

There were three realistic options for integrating React into an existing Django project.

**Option 1 — Fully decoupled.** React lives as a completely separate project deployed
independently from Django. Django becomes a pure API server. The two services communicate
over HTTP from different origins, which means CORS configuration is mandatory and
cross-origin session cookie auth is complex (requires `SameSite=None; Secure`, i.e. HTTPS
only, or a switch to JWT). It also makes a page-by-page migration awkward since you cannot
easily have some pages on Django templates and others on React without infrastructure-level
routing. The payoff is independent deployability and CDN-friendliness, neither of which
is a current requirement.

**Option 2 — Django serves the React build.** React is still a standalone Vite project but
its build output is placed inside Django's static files directory. Django has explicit URL
entries for each migrated page that return a single `index.html` shell, and React Router
handles client-side navigation from there. In development, the Vite dev server runs a
catch-all proxy: pages that have been migrated to React are intercepted by Vite, and
everything else is forwarded transparently to Django. The browser only ever sees one origin.
In production, `npm run build` outputs into Django's static directory, `collectstatic` picks
it up, and one server handles everything.

**Option 3 — django-vite.** A package that integrates Vite's dev server and build manifest
directly into Django's template system via template tags. Its strength is mounting React
components into parts of an existing Django template rather than replacing templates
entirely, which is not the direction this migration is going.

**Option 2 was chosen.** The reasons are practical:

- There is no CORS complexity because everything runs on the same origin in both dev and
  prod. Django's session cookie auth works with zero changes — no JWT, no `SameSite=None`.
- It is a single deployment. One server, one domain, no separate infrastructure to manage.
- It supports a gradual migration. Old Django template pages and new React pages coexist on
  the same domain. Pages are migrated one at a time without any infrastructure changes.
- It requires no additional Django packages. Option 1 would need `django-cors-headers`,
  Option 3 would need `django-vite`. Option 2 needs neither.

If independent frontend deployment ever becomes necessary in the future, the transition from
Option 2 to Option 1 is straightforward — the frontend is already a fully independent Vite
project, so the main work would be adding CORS headers and changing the auth approach.

## Current state

The migration is complete. All user-facing pages are served by React — Django only handles
API endpoints (`/api/`) and the admin panel (`/admin/`). The Vite dev server proxies `/api/`
requests to Django; everything else is handled by React Router.

Adding a new page involves:

1. Building the React component in `frontend/src/pages/`.
2. Adding it to the React Router in `frontend/src/router.tsx`.
3. Adding a `spa_view` entry for it in `backend/src/config/urls.py`.

## Conventions

All API calls from React go through a typed fetch wrapper in `frontend/src/api/client.ts`
that automatically reads the `csrftoken` cookie Django sets and attaches it as the
`X-CSRFToken` header on every mutating request. This is required because React makes
requests via `fetch` rather than Django form submissions, so Django's CSRF middleware would
otherwise reject them.

The Vite build outputs to `backend/src/static/frontend/`. Django's `STATICFILES_DIRS`
includes `backend/src/static/` so `collectstatic` picks up the build automatically.
`spa_view` in `urls.py` serves `index.html` from this location using Django's standard
`TemplateView` wrapped in `ensure_csrf_cookie` to guarantee the CSRF cookie is always set
when a React page is first loaded.

In development, all traffic goes through `localhost:5173`. Django on `:8000` is an internal
detail and is never opened directly in the browser. Both servers must be running — see the
`Makefile` at the project root for the `make dev` command that starts them together.

React Router and Django `urls.py` must stay in sync. Every path that Django delegates to
`spa_view` must have a matching route in the React router, and vice versa. A mismatch
produces a blank page with no error, which can be confusing to debug.
