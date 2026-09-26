# Rostify (working name) / Rosta Studio

A fully customizable web-based scheduling and workforce-management application, designed to adapt to any industry instead of forcing users into a fixed data model.

Most scheduling tools impose their own rules: what an employee record looks like, what a shift is, what time step is allowed, and what language the interface speaks. Rostify inverts this — the data model, time granularity, calendar content, and view layout are all defined by the user, not the vendor.

The product originates from a rotational, offline-prone environment (cruise-ship casino operations), where scheduling means continuously rotating staff across positions throughout the day. That origin drives four core decisions:

- **Customizable data model** — user-defined employee fields, stored in a schema-less structure.
- **Customizable time granularity** — admin-configurable time step (5 min to 1 hour+), not fixed at 15/30 minutes.
- **Customizable views** — the same schedule can be viewed as a paintable day grid, a rotation-focused week view, a Gantt chart, or a month calendar with industry-specific cell content.
- **Local-first architecture** — the app always reads from local storage first and syncs in the background, so it stays fast and works offline.

> Note: this README reflects the project's development plan (July 2026 draft). Implementation may already be ahead of what's described here.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React (recommended over Vue — larger talent pool and ecosystem; UI design doesn't depend on the choice) |
| Local storage | RxDB over IndexedDB (reactive queries + built-in replication protocol) |
| Backend database | PostgreSQL with JSONB (dynamic, schema-less custom fields) |
| Desktop packaging | Capacitor (installable `.exe`, seamless offline mode with background sync on reconnect) |
| Data sync | Background sync over API, revision-based conflict resolution |
| Integrations | REST API (real-time) + scheduled CSV import (batch) for external operational systems, e.g. fleet management |

## Architecture

**Client:** React web app, local-first. All reads/writes go through RxDB/IndexedDB first for instant UI response regardless of network state; changes sync to the server asynchronously in the background.

**Server:** PostgreSQL with three core data entities:
- **People** — base identity fields + a JSONB document of user-defined custom fields, validated against a configured field template.
- **Templates** — schedule templates with metadata, including the configured time step and attached comments (comments live with the template and migrate with it).
- **Schedule entries** — interval-level records: one row per employee per time step, storing assignee, start time, end time, and assigned role/position. This interval model is the analytical backbone of the product.

At a 5-minute step and ~200 staff, this produces tens of thousands of rows per day — manageable for PostgreSQL, but requires:
- date-based partitioning
- composite indexes on `(date, employee)` and `(date, position)`
- an archiving policy

**Integration layer:** two lanes — a real-time API lane for external operational databases (e.g. fleet management systems), and a scheduled CSV import lane for systems that only export files. Both should pass through a validation layer before writing to live data.

**Security (not yet detailed in the original plan, but required):** encryption in transit and at rest, role-based access control aligned with the admin/user distinction, and a change log for schedule edits (near-free to add given the interval model).

**Desktop packaging:** the same React codebase is wrapped with Capacitor into an installable desktop app with full offline capability and sync-on-reconnect.

## Setup & Installation

*(Draft — to be finalized once Phase 0 prototypes are built; capturing intended setup flow based on the planned stack.)*

### Prerequisites
- Node.js (LTS)
- PostgreSQL (with JSONB support — any recent version)
- npm or yarn

### Steps
1. Clone the repository.
2. Install frontend dependencies: `npm install`
3. Configure environment variables (database connection string, API base URL).
4. Set up PostgreSQL: create the database and run the initial schema migration (People, Templates, Schedule entries tables, with JSONB columns for custom fields).
5. Start the local dev server: `npm run dev`
6. (Optional) Build the desktop package via Capacitor once the web app is stable: `npx cap add electron` (or the target desktop platform), then build.

## Development Roadmap / Basic Tasks

The plan favors phases with clear exit criteria over fixed dates. Guiding rule: prove the riskiest and most distinctive elements first — the paintable interval grid and local-first storage with sync.

### Phase 0 — Foundations
- Design the schedule-editor grid and team database UI
- Build the PostgreSQL + JSONB data model
- Prototype RxDB local storage
- Set up a Capacitor build pipeline, verified on a basic desktop build

**Exit criteria:** working prototypes for the riskiest parts.

### Phase 1 — Working Core
- Team database with custom fields + Excel/CSV import
- Day editor: templates, time step, paint-to-create shifts, comments
- Fully functional local-first on a single device

**Exit criteria:** a real team's real schedule is built and maintained daily — the product already replaces Excel.

### Phase 2 — Views & Rotation
- Week view: drag-to-reassign, pick-from-list, "Rotate All"
- Gantt chart view
- Month calendar with customizable per-day cell content
- KPI dashboard

**Exit criteria:** the full cycle — describe, plan, rotate, review — is closed.

### Phase 3 — Sync & Multi-user
- Server API + background sync
- User accounts and roles
- Packaged desktop `.exe` with offline mode and reconnect sync

**Exit criteria:** a team of managers works on shared data across multiple devices, online and offline.

### Phase 4 — Integrations & Expansion
- API integrations with external operational databases
- Scheduled CSV import
- Backlog items (prioritize by real early-customer demand): employee mobile view + publish notifications, availability/time-off tracking, shift-swap requests with manager approval, automatic rotation generator, labor-cost/coverage KPIs

### Suggested early team
- 1 strong frontend developer
- 1 backend developer (or a full-stack pair)
- Part-time UI/UX designer (focused on the grid editor)
- QA as a dedicated role once sync/multi-user work begins

### Recommended first move
Run Phase 1 in a real casino-operation setting, with a design partner, so every later decision is shaped by daily use rather than assumptions.

---
*Source: Rostify development & business plan, draft v1, July 2026.*
