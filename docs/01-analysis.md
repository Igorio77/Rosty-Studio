# Rostify — Phase 1 Analysis: Reference Material Audit

Date: 2026-09-17
Scope: read-only audit of the two files in `reference/`. No architecture or
application code in this document — see CLAUDE.md for the locked stack and
rules, this file is only what the two sources actually contain.

Sources:
- `reference/CASINO_SCHEDULE_MASTER_2026_V3.6.xlsb` — real production casino
  schedule for Carnival Firenze (brand CCL), voyage `FN00305222026`, 7-day
  turnaround, dated 07/11/26 (v3.6, see its own in-file changelog).
- `reference/RostaStudioSchedule.jsx` — React UI prototype, 3989 lines, dated
  2026-09-17 (this is the newest of three copies found; see tooling note
  below).

## Tooling note (read before trusting "no formula text" below)

This environment has no Microsoft Excel and no LibreOffice installed, and the
only pure-Python `.xlsb` reader available (`pyxlsb`) exposes cell **values**
only — not formula tokens, not named-range definitions. Two consequences:

- Formula text below is **not extracted** — only the function names actually
  present were recovered indirectly (see 1.2).
- Named ranges below come from a best-effort UTF-16LE string scan of the raw
  `xl/workbook.bin` part, not a structured record parse. It reliably finds
  *names*; it cannot recover what range or formula each name points to.

If formula-level or named-range-target detail becomes necessary, the
practical fix is opening the file once in real Excel (or installing
LibreOffice) and re-exporting to `.xlsx`, which `openpyxl` reads in full
(formulas, named ranges, merged cells, print areas). Flagging this now rather
than presenting partial binary-scan output as if it were complete.

VBA macro source, by contrast, was fully recovered — `oletools`' `olevba`
extracts and deobfuscates VBA source from `xl/vbaProject.bin` directly, no
Excel needed. Everything in §1.3–§1.4 is the real source, not inferred.

---

## 1. `CASINO_SCHEDULE_MASTER_2026_V3.6.xlsb`

### 1.1 Sheet structure (37 sheets)

| Sheet(s) | Role |
|---|---|
| `HOME` | Voyage header form: Brand, Ship, Date, Duration, Voyage #, Time Step (dropdown-constrained to "15 minutes" / "20 minutes"), plus a read-only 3-week port/date preview strip fed from `ship position`. |
| `ship position` | Hidden. Raw import of an external ship-itinerary export (Tableau dashboard, CSV/XLS). Columns: `PORT_DATE, PORT_NAME, ETA, ETD, DAY_OF_VOYAGE, PORT_CATEGORY, BRAND_SHORT_NAME, SHIP_NAME, VOYAGE_CODE, VOYAGE_LENGTH, VOYAGE_START_DATE, VOYAGE_END_DATE, SUB_TRADE`. Refreshed via a macro, not live-linked. |
| `INF` | Hidden config/lookup sheet. Holds the effective day-count (`P2`) that everything else's row/column hiding is driven from, and computed ship/date/day values (`AR1:AR3`) that `HOME` pulls from after an itinerary import. |
| `Quotes` | Decorative list of ~50 motivational quotes, toggled on/off as a corner-cell formula on the print sheets. |
| `staff data` | Six side-by-side blocks, one per department, each `Last Name / First Name / id#` triplet: Dealers (A:D), Supervisors (J:M), Cashiers (O:R), Technicians (T:W), Hosts (Y:AB), Managers (AD:AG). Row **order carries meaning** — see rotation rule §1.4-R1. |
| `DLR`, `SPS`, `CSH`, `TCH`, `HST`, `MNG` | One schedule sheet per department (Dealers/Supervisors/Cashiers/Technicians/Hosts/Managers). Header carries voyage metadata; body is a per-person row × per-day 4-column block (shift-text cell, then Late-count / Work-hours / Rest-hours) repeated for up to 14 days. Rows are 1:1 with the matching `staff data` block, in the same order. |
| `Day1` … `Day14` | One sheet per cruise day. Per-dealer / per-supervisor row (rows split at a fixed offset — dealers first block, supervisors second) × 15-or-20-minute time columns (`L:DZ`, ~119 slots/day). Each working cell holds a free-typed **position code** (filled via the `RotaForm` floating palette, §1.4-R15, or typed directly). `K4` doubles as a per-day mode switch: `"Casino Closed"` / `"Data Lost"` short-circuits the whole day (§1.4-R6). |
| `dst`, `sst`, `cst`, `tst`, `hstt`, `mst` | Per-department shift-description lookup tables (Dealer/Supervisor/Cashier/Technician/Host/Manager Shift Tables) — feed the shift-text dropdowns on `DLR`/`SPS`/etc. |
| `COVERAGE` | Rolls worked-hours into a time-of-day coverage count, via a **color-based** custom function (§1.4-R17 — flagged as a design smell, not to be carried forward as-is). |
| `TIME OFF` | Per-department "date of last day off" / "expected next day off" tracker, plus a same-sheet rolling day-off calendar. `Expected Next` is copied into `Date of Last` by an explicit, confirmed, irreversible action (§1.4-R14). |
| `Abbreviation` | The canonical code table: Category / Task name / 2–3 letter code / entry-frequency rule (e.g. *"Specific code only"*, *"Enter once per 24-hour period"*, *"Enter for every 15-minute interval"*). This is the authoritative position/admin-code dictionary the whole workbook (and `RotaForm`) is built on. |

### 1.2 Formulas — functions in use (names only, see tooling note)

Recovered from the shared string table: `FILTER` (as `_xlfn._xlws.FILTER`),
`AGGREGATE`, `DAYS`, `MINIFS`, `VSTACK`, `LET`, plus `_xlfn._ONEDARRAY`. These
are modern Excel-365 dynamic-array functions — consistent with `COVERAGE` and
`TIME OFF` being computed roll-ups rather than static data. No formula body
text was recoverable with the tooling available (see note above).

### 1.3 Named ranges (best-effort, see tooling note)

`Autofill`, `COVcount`, `Flag`, `generate`, `Print_Area`, `PrintPage1`,
`PrintPage2`, `ReplaceDataInAllRanges`, `ROTATEifff`, `rotateiMNGffff`,
`rotateTCHiffff`, `Ship_inf`, `ShipPositionUpdate2`, `sps_data_pit`,
`sps_index`, `spslist`, `Supervisors`, `tch_index`, `tchlist`, `Technicians`,
`TimeList_15`, `TimeList_20`, `ToggleColumnsBasedOnDays`.

Most of these are button-assigned macro names (mirrors §1.4 1:1) rather than
pure data ranges. The genuine data ranges are `spslist` / `tchlist` /
`sps_index` / `tch_index` / `sps_data_pit` (dropdown source lists for
position pickers) and `TimeList_15` / `TimeList_20` (the two allowed
time-step values — see §1.4-R10). `Print_Area` + `PrintPage1` + `PrintPage2`
confirm an explicit print layout exists per relevant sheet; their exact cell
ranges were not recoverable (tooling note above). The `PrintActiveSheetAdvanced`
macro itself is trivial — `Application.SendKeys "^p"` — so all print layout
control lives in these named ranges plus 37 per-sheet `printerSettingsN.bin`
parts, not in VBA.

### 1.4 Scheduling rules hardcoded in VBA

Every rule below is real source code (see `xl/vbaProject.bin` via `olevba`),
not inferred from cell values.

| # | Rule | Where | What it does |
|---|---|---|---|
| R1 | Roster block rotation | `ROTATE_DLR_IF.bas`, `ROTATE_SUPS_IF.bas` | Moves the **top row(s)** of one department's `staff data` block to the **bottom** — a manual "who's up next" queue shift, one button per department. Dealers rotates 2 rows at a time; Supervisors/Cashiers/Technicians/Hosts/Managers rotate 1 row. Not automatic — a manager clicks it. |
| R2 | Day-column visibility by duration | `ManageColumns_SCHs`, `ToggleColumnsBasedOnDays` | Hides the day-columns on `DLR/SPS/HST/CSH/TCH/MNG` beyond the configured cruise duration (`INF!P2`), so exactly N days show. |
| R3 | Row visibility by headcount | `ManageRowss_SCHs` | Hides department-sheet rows past the last populated `staff data` row (+ small buffer), and Day-sheet rows past the last populated dealer/supervisor row. Also clears stale position-grid data past that row. |
| R4 | Day-tab visibility by duration | `UpdateSheetsVisibility` | Shows/hides `Day1..Day14` tabs so exactly the first N tabs (duration, capped at 14) are visible. |
| R5 | "Generate" pipeline | `GENERATE_btn.bas` | Single button: validates Ship/Date/#Days are filled on `HOME`, then runs R3 → R2 → R4 → re-protect. One action re-derives the workbook's visible shape from 3 header inputs + current headcounts. |
| R6 | Special-day short-circuit | `ExportDealerData`, keyed on Day-sheet `K4` | `"Casino Closed"` / `"Data Lost"` clears that day's entire position grid and stamps every visible dealer with a Crew ID with a single code (`CASCL` / `DTLST`) instead — bypasses per-slot entry entirely for that day. |
| R7 | Export data-integrity gate | `ExportDealerData` / `IsSuspectValue` / `IsAllDigits` / dup-Crew-ID check | Export is **blocked** (not just warned) if: Last Name / First Name / Location exceed 50 chars, a shift description exceeds 100 chars, a value looks like card-swipe track data (starts `%B`, or contains both `;` and `=`), Crew ID is non-numeric, or the same Crew ID appears twice on one Day tab. |
| R8 | Low-record soft check | `ExportDealerData`, `LOW_RECORD_THRESHOLD = 100` | A visible, non-special day with fewer than 100 position-grid entries triggers a Yes/No confirmation before export proceeds — soft, not blocking. |
| R9 | Itinerary import column check | `ValidateRequiredColumns` (`Ship_position_update.bas`) | An imported ship-position file is rejected unless its header row contains both an `ETA` and an `ETD` column. |
| R10 | Time-step whitelist | `ExportDealerData`, reads `HOME!C10` | Must be exactly `"15 minutes"` or `"20 minutes"`; export is blocked with a specific message otherwise. This is the current, narrower form of the "configurable time step" idea in CLAUDE.md/README (there: 5–60 min open range; here: exactly two hardcoded values). |
| R11 | Export timestamp rounding | `ExportDealerData` (`Version.bas` changelog calls this out as a v3.6 bugfix) | Every export timestamp (slot start, and computed end = start + time-step) is rounded to the nearest whole minute before being written, specifically to stop float drift from pushing a slot across midnight into the wrong day. |
| R12 | Location/position text normalization | `CleanLocation` | On export, a position/location cell is stripped to `[A-Za-z0-9 /\|]`, truncated at the first `/`, `\`, or `\|`, then upper-cased. Only the text *before* the first separator is the real position code; anything after is treated as an inline comment and dropped from the exported `LOCATION` field. |
| R13 | Global quotes toggle | `ToggleQuotesFormula` | One flag flips a `=Quotes!B1` formula on/off in the `F2` cell of every department print sheet simultaneously. |
| R14 | Day-off roll-forward | `DayOffPage_newcicle.bas` | Confirmed, irreversible: copies "Expected Next Time Off" into "Date of Last Time Off" across 5 fixed department blocks on `TIME OFF`, clearing the source. The workbook's only explicit state transition on rest-day cadence. |
| R15 | Position-code quick-fill palette | `RotaForm` (`SetValue`) | ~40 hardcoded buttons mapping a label to a 1–3 char code (`BJ01→B1` … `BJ10→B10`, `BREAK→X`, `Chipper→CH`, `Finish→F`, `FN01→F1`…`FN03→F3`, `HH01→H1`…`HH04→H4`, `Medical→MD`, `Office→OFC`, `RW01→R1`…`RW03→R3`, `TP01→T1`…`TP04→T4`, `Training→TR`, etc.) so a manager one-clicks a cell fill instead of typing. `FILLUP` additionally copies each selected cell from the cell to its left (fill-right). |
| R16 | Formula hiding + sheet protection | `hide_formulas.bas`, `Unprotect_Protect.bas` | Every visible sheet's formula cells get `FormulaHidden=True`; the 6 department sheets + 14 Day sheets are re-protected with a fixed permission set (format/sort/filter/pivot allowed, structural changes not) after every generate/import/export run. This is Excel sheet-protection standing in for a real role system. |
| R17 | Coverage counted by cell **color** | `Workinghours` UDF (`Coverage.bas`) | `COVERAGE` counts a cell as "worked" if its fill color matches a reference sample cell. Coverage totals therefore depend on someone consistently color-coding shift cells — **not** on any position/shift code. Flagged as a design smell to explicitly not carry forward; §4 has the recommendation. |

**Important finding:** none of R1–R17 is a classic *scheduling constraint*
(no double-booking check, no minimum-rest-between-shifts rule, no
max-hours/week cap, no qualification-to-position matching). The xlsb's rules
are almost entirely **data-integrity, visibility, and export-pipeline**
rules layered over a free-text grid — the actual "is this a legal roster"
judgment is made by the human filling the grid, not by the workbook. This
matters directly for CLAUDE.md's rule-engine design: there is no existing
catalog of real assignment-level constraints to port from either source (the
jsx has none either — see §2.3). That catalog will need to be defined with
the domain expert (the person who fills this workbook today), not inferred
from the files.

---

## 2. `RostaStudioSchedule.jsx`

### 2.1 Data model

Plain in-memory JS objects, no persistence layer, no schema validation:

```
STAFF[]            { id, firstName, lastName, department, position, email, name, archived }
TEMPLATES[]        { id, name, comments[], department, color, shifts[] }
  shift            { id, ranges: [{start,end}], role, color, comments }
ASSIGNMENTS        { "<dateKey>__<department>": templateId }        // Layer A: which template applies on a date
ROSTER             { "<personName>__<dateKey>": {shiftId, ranges} } // who is on which shift that date
positionCells       { "<dateKey>:<shiftId>:<personId>:<slotMinute>": "<code>" } // Layer B: free-text position per slot
```

`ASSIGNMENTS` and `ROSTER` are both keyed by composite string keys built with
`rk(name, dateKey)` / template literals — not normalized IDs, and person
identity in `ROSTER` is by `person.name`, not `person.id` (a latent bug: two
staff with the same display name would collide).

### 2.2 Shift / rotation logic

- `PORT_ROTATION` is a static `[dateKey, templateBase]` list (June–Aug 2026)
  used only to seed the demo data (`INITIAL_ASSIGNMENTS`, `INITIAL_ROSTER`).
  It is generator input, not a reusable port-rotation engine.
- `INITIAL_ROSTER` generation intentionally seeds gaps (`leaveOpen`, every
  6th day) and a rolling day-off (`(dayIdx + i) % 7 === 0`) purely so the
  demo data looks realistic — this is demo-data flavor, not product logic.
- **No "Rotate All" feature exists in this file.** ROADMAP_RU.md (Aug 2026,
  reviewing an earlier/smaller copy of this same prototype) describes a
  "Rotate All" button in the Week view; a full-text search of this (newer,
  3989-line) copy finds no such feature, button, or handler. Either it was
  removed, or ROADMAP_RU was describing something that was never actually
  implemented. Flagging as a documentation/code mismatch to resolve, not
  assuming either version is "right."
- Layer-B analog: `DayGridView` renders one row per shift-assignee ×
  15/20/60-min slot (`SLOT_MIN = 60` here, hardcoded, not read from any
  config) with a free-text `<input>` per working cell, backed by a
  `<datalist>` of `handlers.positions` — functionally the same shape as the
  xlsb's `Day1..Day14` grids + `RotaForm` palette (§1.1, §1.4-R15), just
  rendered as a native HTML datalist instead of a floating button panel.

### 2.3 Validation / conflict detection

**None.** No overlap check, no double-booking check, no rest-period logic, no
max-hours enforcement, no field-length or format validation anywhere in the
file (confirmed by search — no matches for `valid`, `conflict`, `overlap`,
`double` in any case). Drag-and-drop handlers (`onDrop` at three sites) only
reorder template shifts or move staff between roster cells; none of them
reject an incoming drop based on a rule.

### 2.4 Templates

`TEMPLATES[]` covers 5 ports (`Sea`, `Cozumel`, `Nassau`, `Grand Cayman`,
`St. Thomas`) × 3 departments (`Dealers`, `Supervisors`, `Managers`) = 15
static templates, each a fixed list of named shifts with start/end times and
a display color. This is materially narrower than the xlsb's real data: 3
departments here vs. 6 real ones (no Cashiers/Technicians/Hosts), and a
small closed set of generic position codes (`INITIAL_POSITIONS`: `B1–B3,
RW1–RW2, BJ1–BJ3, CR1, PK1, BRK, FLOAT` — 12 total) vs. the xlsb's ~40
codes tied to real station numbering (`Abbreviation` sheet, §1.1).

### 2.5 State shape / what's real vs. decorative

`DashboardTab` is **not** decorative — it genuinely derives fill-rate,
per-shift gap list, and per-person weekly-hours utilization from
`templates` + `assignments` + `roster` in `useMemo` blocks (`2362`–`2402`).
This is the one piece of business logic in the file worth reusing
conceptually: "derive coverage/utilization from templates+roster" is a
cleaner approach than the xlsb's color-based `COVERAGE` sheet (§1.4-R17) and
maps well onto CLAUDE.md's unified `Assignment` model. Everything else
(Print Center, Report Center, Off Tracker, Notifications, per ROADMAP_RU) was
not re-verified line-by-line in this pass since ROADMAP_RU already covers it
and the file has grown since that review — worth a quick re-check before
relying on that inventory if those tabs matter for the port.

---

## 3. Side-by-side comparison

| Aspect | `RostaStudioSchedule.jsx` (prototype) | `CASINO_SCHEDULE_MASTER_2026_V3.6.xlsb` (production) |
|---|---|---|
| Purpose | Clickable front-end demo | Real production schedule + its own authoring tool |
| Persistence | None (`useState` only, lost on refresh) | The Excel file itself is the store |
| Departments | 3 (Dealers, Supervisors, Managers) | 6 (+ Cashiers, Technicians, Hosts) |
| Layer A (shift/template) | `TEMPLATES` + `ASSIGNMENTS` (template per date × department) | `DLR/SPS/CSH/TCH/HST/MNG` (shift text + Late/Work/Rest hours per date × department × person) |
| Layer B (position rotation) | `DayGridView`, per-slot free-text + HTML datalist | `Day1–Day14`, per-slot free-text + `RotaForm` floating palette |
| Position codes | 12 generic (`B1–B3`, `RW1–RW2`, …) | ~40 real codes, centrally defined in `Abbreviation` |
| Roster ordering | Not meaningful | Meaningful — row order = rotation queue (R1) |
| Validation at entry | None | None (same gap — free-text grid both places) |
| Validation at export | N/A (no export) | Extensive, blocking (R7, R9, R10) + one soft check (R8) |
| Conflict / overlap detection | None | None |
| Rest/hours constraints | None (hours only displayed) | None (hours only displayed/computed) |
| Coverage/KPI | `DashboardTab` — real derived fill-rate/gaps/utilization | `COVERAGE` sheet — color-based cell counting (design smell) |
| Special/closed days | Not modeled | `K4` = Casino Closed / Data Lost short-circuit (R6) |
| Time granularity | Not enforced anywhere (freeform `hh:mm`) | Whitelisted to exactly "15 minutes" / "20 minutes" (R10) |
| Import | None | Itinerary CSV import (R9) + full cross-workbook copy tool |
| Export | None | CSV export, ID'd (`FL_...`, `CTS_...`) |
| Print | Not modeled (Print Center = stub per ROADMAP_RU) | `Print_Area`/`PrintPage1`/`PrintPage2` + per-sheet printer settings |
| Access control | `USER_ROLES` list exists but per ROADMAP_RU is decorative | Sheet protection (structural lock), not a real role system |

---

## 4. Candidate rule list for the plugin rule engine

As found in §1.4, **there is no existing catalog of true assignment-level
scheduling constraints** (double-booking, rest periods, max hours,
qualification matching) in either source — this list is therefore split into
what *is* directly portable (data-integrity/workflow rules, real in both
files' sense) versus what is a known gap to fill separately.

### 4.1 Directly portable (already real rules in the xlsb)

| Rule | Parameters | Default |
|---|---|---|
| Field length limits | `max_len` per field (Last Name 50, First Name 50, Location 50, Shift description 100) | **HARD** (matches current export-blocking behavior) |
| Card-swipe pattern detection | none (fixed pattern: starts `%B`, or contains both `;` and `=`) | **HARD** |
| Crew ID format | must be all-digits | **HARD** |
| Duplicate Crew ID per day | scope = one Day tab / one date | **HARD** |
| Low record count per day | `threshold` (currently 100), scope = visible non-special day | **SOFT** (currently a Yes/No confirm) |
| Time-step whitelist | `allowed_values` (currently `[15, 20]` minutes) | **HARD** — but see note: CLAUDE.md/README want this *open* (5–60 min), so the rule's real job going forward is validating against the *configured* step, not a fixed pair |
| Itinerary import column check | `required_columns` (currently `[ETA, ETD]`) | **HARD** (import-time gate, not assignment-time) |
| Special-day mode (Casino Closed / Data Lost) | `special_codes` map | Configuration/mode switch, not itself HARD/SOFT — but when active it should suppress R7-style per-slot validation for that day, matching current behavior |

### 4.2 Data-normalization logic (not rule-engine candidates — belongs in `io/`)

Timestamp rounding (R11) and location-text cleanup (R12) are fixed transforms
applied at export/import time, not user-adjustable constraints. They belong
in `io/exporters` / `io/importers`, not the pluggable rule engine.

### 4.3 Explicit gap — needs definition, not extraction

None of the following exist in either source and must be defined with the
domain expert before they can become rule-engine plugins:

- No double-booking (same person, overlapping time, any layer)
- Minimum rest between shifts
- Maximum consecutive working days / hours per week
- Qualification-to-position matching (e.g. only a trained dealer can be
  assigned a `BJ-0x` code)
- Any actual day-off cadence rule (the xlsb only *tracks* last/next day off
  as data — R14 is a manual copy action, not an enforced cadence rule)

---

## 5. Reusable vs. needs rework

**Reusable concepts (logic/shape, not code — neither source is Python/Qt):**
- The two-layer `Assignment(employee, start, end, resource, layer)` model
  CLAUDE.md already specifies maps cleanly onto both sources: Layer A =
  department shift assignment (`DLR`/`SPS`/… rows, `TEMPLATES`+`ASSIGNMENTS`
  in jsx), Layer B = per-slot position code (`Day1–14` grids, `DayGridView`).
- `Abbreviation` sheet as the canonical position/admin-code dictionary — this
  is exactly the kind of data-not-code table CLAUDE.md's rule-engine
  philosophy wants; port its contents as seed data.
- The roster-rotation *queue* concept (R1: "top of the list rotates to the
  bottom") is a real, currently-used scheduling convenience worth keeping,
  reimplemented as an explicit ordered field rather than physical row order.
- `DashboardTab`'s derive-from-source-data approach to fill-rate/gaps/
  utilization (§2.5) is a cleaner pattern than the xlsb's color-counting and
  is worth reusing conceptually for the future analytics service.
- The export-time validation catalog (§4.1) is real, tested-by-production
  logic — port the *rules*, not the VBA.

**Needs rework for Python/PySide6:**
- Everything UI-specific in the jsx (React components, CSS-in-JS, drag/drop
  handlers) — explicitly out of scope per CLAUDE.md, not portable regardless.
- Visibility rules R2–R4 (column/row/tab hiding by duration/headcount) are
  Excel-specific plumbing to compensate for a fixed-size grid; in a real data
  model (rows = actual employees, columns = actual days) these rules simply
  don't need to exist — don't port the mechanism, only note the *intent*
  (don't show days beyond the configured duration).
- Sheet protection / formula hiding (R16) — CLAUDE.md already defines a real
  access model (one editor, all viewers); this replaces R16 entirely rather
  than needing a port.
- Coverage-by-color (R17) — do **not** port as-is. Recompute coverage from
  explicit position/shift codes, the way `DashboardTab` already does it.
- Person identity keyed by display name (`rk(name, dateKey)` in jsx,
  Crew ID as loose text matched across sheets in xlsb) — needs a real
  employee ID as the join key from day one, since the `staff data` block
  already carries `id#` but the schedule sheets don't consistently
  cross-check against it.

---

## Open items for review

1. `.xlsb` formula text and exact named-range targets were not recoverable
   with the tooling available in this environment (see Tooling note). If
   needed, either open the file once in real Excel/LibreOffice and re-export
   to `.xlsx`, or say so and I'll write a minimal BIFF12 record parser.
2. R1 (roster rotation) rotates 2 rows for Dealers but 1 row for every other
   department — confirm this is intentional (e.g. Dealers are scheduled in
   pairs) before assuming it's a bug to "fix" during the port.
3. ROADMAP_RU's "Rotate All" feature was not found in the current jsx copy
   (§2.2) — confirm whether it should exist going forward, independent of
   whether it exists in this file.
