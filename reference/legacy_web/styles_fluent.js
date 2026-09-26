export const STYLES = `
/* 1. Root */
.rosta-app {
  --bg-app: #181818;
  --bg-surface: #1f1f1f;
  --bg-surface-alt: #242424;
  --bg-hover: #2a2a2a;
  --bg-active: #333333;
  --border-subtle: rgba(255,255,255,0.06);
  --border-default: rgba(255,255,255,0.10);
  --border-strong: rgba(255,255,255,0.16);
  --text-primary: #ffffff;
  --text-secondary: #b3b3b3;
  --text-tertiary: #737373;
  --accent: #0fa36b;
  --accent-hover: #0c8a5a;
  --accent-soft: rgba(15,163,107,0.12);
  --accent-on: #ffffff;
  --tpl-teal-bg: rgba(42,162,160,0.15);
  --tpl-teal-fg: #5ec4c2;
  --tpl-teal-dot: #2aa2a0;
  --tpl-amber-bg: rgba(192,154,62,0.15);
  --tpl-amber-fg: #dbb85a;
  --tpl-amber-dot: #c09a3e;
  --tpl-burgundy-bg: rgba(158,59,74,0.15);
  --tpl-burgundy-fg: #c46b7a;
  --tpl-burgundy-dot: #9e3b4a;
  --tpl-blue-bg: rgba(74,127,212,0.15);
  --tpl-blue-fg: #7da8e4;
  --tpl-blue-dot: #4a7fd4;
  --tpl-purple-bg: rgba(139,108,193,0.15);
  --tpl-purple-fg: #b198d9;
  --tpl-purple-dot: #8b6cc1;
  --danger: #d44040;
  --danger-on: #ffffff;
  --danger-soft: rgba(212,64,64,0.12);
  --shadow-sm: 0 2px 4px rgba(0,0,0,0.24);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.32);
  --shadow-lg: 0 8px 24px rgba(0,0,0,0.48);

  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-app);
  color: var(--text-primary);
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  color-scheme: dark;
  overflow: hidden;
  box-sizing: border-box;
}

.rosta-app *, .rosta-app *::before, .rosta-app *::after {
  box-sizing: border-box;
}

/* 2. Command Ribbon */
.cmd-ribbon {
  height: 48px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  background-color: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
  padding: 0 16px;
  flex-shrink: 0;
}

.cmd-ribbon-left, .cmd-ribbon-center, .cmd-ribbon-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.cmd-ribbon-left {
  width: 260px;
}

.cmd-toggle-sidebar {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  width: 32px;
  height: 32px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color 120ms ease-out, color 120ms ease-out;
}
.cmd-toggle-sidebar:hover {
  background-color: var(--bg-hover);
  color: var(--text-primary);
}

.cmd-app-name {
  font-weight: 600;
  font-size: 16px;
  color: var(--text-primary);
}

.view-switcher {
  display: flex;
  background-color: var(--bg-surface-alt);
  border-radius: 6px;
  padding: 2px;
  border: 1px solid var(--border-subtle);
}

.view-switcher button {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  transition: background-color 120ms ease-out, color 120ms ease-out;
}
.view-switcher button:hover {
  background-color: var(--bg-hover);
  color: var(--text-primary);
}
.view-switcher button.is-active {
  background-color: var(--bg-active);
  color: var(--text-primary);
  font-weight: 500;
}

.period-nav {
  display: flex;
  align-items: center;
  gap: 4px;
}

.period-nav button {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  width: 28px;
  height: 28px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color 120ms ease-out, color 120ms ease-out;
}
.period-nav button:hover {
  background-color: var(--bg-hover);
  color: var(--text-primary);
}
.period-nav span {
  font-size: 14px;
  font-weight: 500;
  padding: 0 8px;
}

.date-box-wrap {
  position: relative;
}

.date-box {
  display: flex;
  align-items: center;
  gap: 6px;
  background-color: var(--bg-surface-alt);
  border: 1px solid var(--border-default);
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: border-color 120ms ease-out;
}
.date-box:hover {
  border-color: var(--border-strong);
}

.week-start-trigger {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: background-color 120ms ease-out;
}
.week-start-trigger:hover {
  background-color: var(--bg-hover);
  color: var(--text-primary);
}

.cta-btn {
  background-color: var(--accent);
  color: var(--accent-on);
  border: none;
  font-weight: 600;
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 120ms ease-out;
}
.cta-btn:hover {
  background-color: var(--accent-hover);
}

/* 3. App body */
.app-body {
  display: flex;
  flex-direction: row;
  flex: 1;
  overflow: hidden;
}

/* 4. Nav Rail */
.nav-rail {
  width: 48px;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-surface-alt);
  border-right: 1px solid var(--border-default);
  align-items: center;
  padding-top: 8px;
  padding-bottom: 8px;
  flex-shrink: 0;
}

.nav-rail-item {
  width: 48px;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  cursor: pointer;
  transition: color 120ms ease-out, background-color 120ms ease-out;
  border-left: 2px solid transparent;
  position: relative;
}
.nav-rail-item:hover {
  color: var(--text-primary);
  background-color: var(--bg-hover);
}
.nav-rail-item.is-active {
  border-left: 2px solid var(--accent);
  color: var(--accent);
  background-color: var(--accent-soft);
}
.nav-rail-item[title]:hover::after {
  content: attr(title);
  position: absolute;
  left: 56px;
  background: var(--bg-surface-alt);
  border: 1px solid var(--border-default);
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  white-space: nowrap;
  z-index: 1000;
  color: var(--text-primary);
}

.nav-rail > :last-child {
  margin-top: auto;
}

.nav-rail-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background-color: var(--accent-soft);
  color: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
  cursor: pointer;
}

/* 5. Side Panel */
.side-panel {
  width: 260px;
  background-color: var(--bg-surface);
  border-right: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: width 200ms ease, opacity 200ms ease;
  overflow-y: auto;
  overflow-x: hidden;
}
.side-panel.is-collapsed {
  width: 0;
  opacity: 0;
  border-right: none;
}

.side-panel-section {
  padding: 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.side-panel-heading {
  text-transform: uppercase;
  font-size: 10px;
  color: var(--text-tertiary);
  font-weight: 600;
  margin-bottom: 12px;
  letter-spacing: 0.5px;
}

.mini-cal {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.mini-cal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  font-weight: 500;
}
.mini-cal-header button {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
}
.mini-cal-weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  text-align: center;
  font-size: 10px;
  color: var(--text-tertiary);
  margin-bottom: 4px;
}
.mini-cal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
}
.mini-cal-day {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  border-radius: 4px;
  cursor: pointer;
  color: var(--text-secondary);
  margin: auto;
}
.mini-cal-day:hover {
  background-color: var(--bg-hover);
  color: var(--text-primary);
}
.mini-cal-day.is-muted {
  color: var(--text-tertiary);
}
.mini-cal-day.is-today {
  background-color: var(--accent);
  color: var(--accent-on);
  font-weight: bold;
}
.mini-cal-day.is-selected {
  background-color: var(--accent-soft);
  color: var(--accent);
}

.dept-toggle-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.dept-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  cursor: pointer;
  color: var(--text-secondary);
}
.dept-toggle input[type="checkbox"] {
  accent-color: var(--accent);
  cursor: pointer;
}
.dept-toggle:hover {
  color: var(--text-primary);
}

.side-panel-profile {
  margin-top: auto;
  padding: 16px;
}

/* 6. Main content */
.main-content {
  flex: 1;
  overflow: auto;
  background-color: var(--bg-app);
  display: flex;
  flex-direction: column;
}

/* 7. Calendar area */
.calendar-area-inner {
  padding: 16px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* Month view */
.month-grid-wrap {
  display: flex;
  flex-direction: column;
  flex: 1;
}
.weekday-row {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  margin-bottom: 8px;
}
.weekday-label {
  text-align: center;
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
  text-transform: uppercase;
}
.month-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 1px;
  background-color: var(--border-subtle);
  flex: 1;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  overflow: hidden;
}
.day-cell {
  background-color: var(--bg-surface);
  min-height: 110px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  position: relative;
  transition: background-color 120ms ease-out;
}
.day-cell:hover {
  background-color: var(--bg-hover);
}
.day-cell.is-muted {
  background-color: var(--bg-app);
}
.day-cell.is-muted .day-number {
  color: var(--text-tertiary);
}
.day-cell.is-drag-over {
  outline: 2px dashed var(--accent);
  outline-offset: -2px;
}
.day-cell.is-today-cell {
  border-left: 3px solid var(--accent);
}
.day-number {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  border-radius: 50%;
  align-self: flex-end;
  color: var(--text-secondary);
}
.day-number.is-today {
  background-color: var(--accent);
  color: var(--accent-on);
  font-weight: bold;
}

.template-chip {
  display: flex;
  flex-direction: column;
  padding: 6px 8px;
  border-radius: 6px;
  width: 100%;
  font-size: 11px;
  cursor: pointer;
  transition: opacity 120ms ease-out;
  position: relative;
}
.template-chip:hover {
  opacity: 0.9;
}
.template-card-header {
  display: flex;
  align-items: center;
  gap: 6px;
}
.template-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.template-card-title {
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.template-card-line {
  margin-top: 4px;
  opacity: 0.8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.template-actions {
  position: absolute;
  top: 4px;
  right: 4px;
  display: none;
  gap: 4px;
}
.template-chip:hover .template-actions {
  display: flex;
}

.tpl-teal { background-color: var(--tpl-teal-bg); color: var(--tpl-teal-fg); }
.tpl-teal .template-dot { background-color: var(--tpl-teal-dot); }

.tpl-amber { background-color: var(--tpl-amber-bg); color: var(--tpl-amber-fg); }
.tpl-amber .template-dot { background-color: var(--tpl-amber-dot); }

.tpl-burgundy { background-color: var(--tpl-burgundy-bg); color: var(--tpl-burgundy-fg); }
.tpl-burgundy .template-dot { background-color: var(--tpl-burgundy-dot); }

.tpl-blue { background-color: var(--tpl-blue-bg); color: var(--tpl-blue-fg); }
.tpl-blue .template-dot { background-color: var(--tpl-blue-dot); }

.tpl-purple { background-color: var(--tpl-purple-bg); color: var(--tpl-purple-fg); }
.tpl-purple .template-dot { background-color: var(--tpl-purple-dot); }

.day-add-btn-subtle {
  display: none;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 16px;
  cursor: pointer;
  align-self: center;
  margin-top: auto;
}
.day-cell:hover .day-add-btn-subtle {
  display: block;
}
.day-add-btn-subtle:hover {
  color: var(--accent);
}

.month-week-num {
  position: absolute;
  top: 8px;
  left: 8px;
  font-size: 10px;
  color: var(--text-tertiary);
  width: 16px;
  height: 16px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--bg-surface-alt);
}

/* Year view */
.year-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  padding: 16px;
}
.mini-month {
  background-color: var(--bg-surface-alt);
  border-radius: 12px;
  padding: 14px;
}
.mini-month-header {
  text-align: center;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
}
.mini-month-title-btn {
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-weight: inherit;
  font-size: inherit;
  cursor: pointer;
}
.mini-month-title-btn:hover {
  color: var(--accent);
}
.mini-weekday-row {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  text-align: center;
  font-size: 10px;
  color: var(--text-tertiary);
  margin-bottom: 6px;
}
.mini-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
}
.mini-day {
  width: 24px;
  height: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  border-radius: 4px;
  margin: auto;
  color: var(--text-secondary);
  position: relative;
}
.mini-day.is-muted {
  color: var(--text-tertiary);
  opacity: 0.5;
}
.mini-day.is-today {
  background-color: var(--accent);
  color: var(--accent-on);
  font-weight: bold;
}
.mini-week-num {
  font-size: 8px;
  color: var(--text-tertiary);
  position: absolute;
  left: -12px;
}
.mini-day-bar {
  width: 12px;
  height: 2px;
  border-radius: 1px;
  margin-top: 2px;
}
.mini-day-bar.tpl-teal { background-color: var(--tpl-teal-dot); }
.mini-day-bar.tpl-amber { background-color: var(--tpl-amber-dot); }
.mini-day-bar.tpl-burgundy { background-color: var(--tpl-burgundy-dot); }
.mini-day-bar.tpl-blue { background-color: var(--tpl-blue-dot); }
.mini-day-bar.tpl-purple { background-color: var(--tpl-purple-dot); }

/* Roster/Week view */
.roster-wrap {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}
.roster-scroll {
  flex: 1;
  overflow: auto;
  border-radius: 8px;
  border: 1px solid var(--border-default);
  background-color: var(--bg-surface);
}
.roster-grid {
  display: grid;
  /* e.g., sticky names, 7 days, 1 total */
  grid-template-columns: 200px repeat(7, minmax(180px, 1fr)) 100px;
}

.roster-name-header {
  position: sticky;
  top: 0;
  left: 0;
  z-index: 10;
  background-color: var(--bg-surface-alt);
  font-size: 10px;
  text-transform: uppercase;
  color: var(--text-tertiary);
  padding: 12px;
  border-bottom: 1px solid var(--border-default);
  border-right: 1px solid var(--border-default);
}
.roster-day-info {
  position: sticky;
  top: 0;
  background-color: var(--bg-surface-alt);
  border-bottom: 1px solid var(--border-default);
  border-right: 1px solid var(--border-default);
  padding: 8px;
  text-align: center;
  z-index: 5;
}
.roster-day-info.is-today {
  background-color: var(--accent-soft);
}
.roster-day-date {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}
.roster-day-tplname {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 4px;
}
.roster-day-tplcomments {
  font-size: 10px;
  color: var(--text-tertiary);
  margin-top: 2px;
}
.roster-subcol-group {
  display: flex;
  font-size: 10px;
  color: var(--text-tertiary);
  text-transform: uppercase;
  border-top: 1px solid var(--border-subtle);
  margin-top: 8px;
  padding-top: 4px;
}
.roster-subcol-group > div {
  flex: 1;
  text-align: center;
}

.roster-name-cell {
  position: sticky;
  left: 0;
  background-color: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
  border-right: 1px solid var(--border-default);
  padding: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  z-index: 2;
}
.roster-grid > div:nth-child(even) .roster-name-cell {
  background-color: var(--bg-surface-alt);
}
.roster-id-cell {
  font-size: 13px;
  font-weight: 500;
}
.roster-remove-cell {
  color: var(--danger);
  cursor: pointer;
  display: none;
}
.roster-name-cell:hover .roster-remove-cell {
  display: block;
}

.roster-schedule-cell, .roster-shift-cell, .roster-hrs-cell {
  border-bottom: 1px solid var(--border-subtle);
  border-right: 1px solid var(--border-default);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px;
  font-size: 12px;
  position: relative;
}
.roster-grid > div:nth-child(even) .roster-schedule-cell,
.roster-grid > div:nth-child(even) .roster-shift-cell,
.roster-grid > div:nth-child(even) .roster-hrs-cell {
  background-color: rgba(255,255,255,0.02);
}

.roster-shift-badge {
  width: 26px;
  height: 26px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 11px;
}
.roster-shift-badge-empty {
  width: 26px;
  height: 26px;
  border-radius: 6px;
  border: 1px dashed var(--border-strong);
  display: none;
  cursor: pointer;
}
.roster-shift-cell:hover .roster-shift-badge-empty {
  display: block;
}

.roster-total-cell {
  position: sticky;
  right: 0;
  background-color: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  color: var(--accent);
  padding: 8px;
  z-index: 2;
}
.roster-total-header {
  position: sticky;
  top: 0;
  right: 0;
  background-color: var(--bg-surface-alt);
  border-bottom: 1px solid var(--border-default);
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  text-transform: uppercase;
  color: var(--text-tertiary);
  padding: 12px;
}

.roster-plus-btn, .roster-minus-btn {
  background: var(--bg-surface-alt);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  width: 24px;
  height: 24px;
  border-radius: 4px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.roster-plus-btn:hover, .roster-minus-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}
.roster-add-crew-cell {
  grid-column: 1 / -1;
  padding: 12px;
  text-align: center;
}

.roster-day-edit-btn, .roster-day-remove-btn, .roster-day-assign-btn {
  background: var(--bg-surface-alt);
  border: 1px solid var(--border-default);
  border-radius: 4px;
  color: var(--text-secondary);
  font-size: 11px;
  padding: 4px 8px;
  cursor: pointer;
  display: none;
  position: absolute;
  top: 4px;
  right: 4px;
}
.roster-schedule-cell:hover .roster-day-edit-btn,
.roster-schedule-cell:hover .roster-day-remove-btn,
.roster-schedule-cell:hover .roster-day-assign-btn {
  display: block;
}

.roster-empty-row {
  grid-column: 1 / -1;
  text-align: center;
  padding: 24px;
  color: var(--text-tertiary);
  font-size: 13px;
}

/* Day view (Gantt) */
.day-view-wrap {
  display: flex;
  flex-direction: column;
  flex: 1;
}
.day-view-toolbar {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 20px;
  padding: 16px;
  border-bottom: 1px solid var(--border-default);
  background-color: var(--bg-surface);
}
.day-view-header {
  font-size: 20px;
  font-weight: 600;
}
.day-view-tplinline {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary);
}
.day-view-timestep {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}

.day-view-gantt-wrap {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.day-view-gantt-scroll {
  flex: 1;
  overflow: auto;
}
.day-view-gantt-grid {
  display: grid;
  /* e.g., 200px for names, 24 cols for 24h */
  grid-template-columns: 200px repeat(24, minmax(40px, 1fr));
  position: relative;
}

.gantt-head-cell {
  position: sticky;
  top: 0;
  background-color: var(--bg-surface-alt);
  font-size: 10px;
  text-transform: uppercase;
  color: var(--text-tertiary);
  padding: 8px;
  border-bottom: 1px solid var(--border-default);
  z-index: 10;
  text-align: center;
}
.gantt-cell {
  border-top: 1px solid var(--border-subtle);
  border-right: 1px dashed var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  height: 48px;
}
.gantt-cell-left {
  justify-content: flex-start;
  padding-left: 12px;
}
.gantt-bar-cell {
  position: relative;
  grid-column: 2 / -1;
  border-top: 1px solid var(--border-subtle);
  height: 48px;
}
.gantt-ruler-cell {
  grid-column: 2 / -1;
  position: sticky;
  top: 0;
  height: 32px;
  background-color: var(--bg-surface-alt);
  border-bottom: 1px solid var(--border-default);
  z-index: 9;
}
.timeline-ruler {
  position: relative;
  width: 100%;
  height: 100%;
}
.timeline-ruler-mark {
  position: absolute;
  bottom: 0;
  width: 1px;
  height: 8px;
  background-color: var(--border-strong);
}
.timeline-ruler-label {
  position: absolute;
  bottom: 10px;
  font-size: 10px;
  color: var(--text-tertiary);
  transform: translateX(-50%);
}

.timeline-bar {
  position: absolute;
  top: 8px;
  height: 32px;
  border-radius: 6px;
  cursor: grab;
  display: flex;
  align-items: center;
  padding: 0 8px;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  z-index: 2;
}
.timeline-bar:active {
  cursor: grabbing;
}
.timeline-bar-ghost {
  position: absolute;
  top: 8px;
  height: 32px;
  border-radius: 6px;
  border: 1px dashed var(--border-strong);
  background: transparent;
  pointer-events: none;
  z-index: 1;
}
.timeline-handle {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 8px;
  cursor: ew-resize;
}
.timeline-handle.left { left: 0; }
.timeline-handle.right { right: 0; }

.gantt-name-cell {
  position: sticky;
  left: 0;
  background-color: var(--bg-surface);
  border-top: 1px solid var(--border-subtle);
  border-right: 1px solid var(--border-default);
  padding: 0 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  z-index: 5;
}
.gantt-name-text {
  font-size: 13px;
  font-weight: 500;
}
.gantt-name-remove {
  color: var(--danger);
  cursor: pointer;
  display: none;
}
.gantt-name-cell:hover .gantt-name-remove {
  display: block;
}
.gantt-name-add {
  grid-column: 1 / -1;
  padding: 12px;
  text-align: center;
  border-top: 1px solid var(--border-subtle);
}
.gantt-shift-cell {
  /* wrapper inside gantt-bar-cell */
}
.shift-edit-popover {
  position: absolute;
  background-color: var(--bg-surface-alt);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  box-shadow: var(--shadow-md);
  padding: 12px;
  z-index: 100;
}

/* Popovers & pickers */
.template-picker-popover {
  position: absolute;
  z-index: 100;
  background-color: var(--bg-surface-alt);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  box-shadow: var(--shadow-lg);
  padding: 8px;
  min-width: 200px;
}
.picker-popover-label {
  text-transform: uppercase;
  font-size: 10px;
  color: var(--text-tertiary);
  margin-bottom: 8px;
  padding: 0 8px;
}
.template-picker-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 220px;
  overflow-y: auto;
}
.template-picker-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 120ms ease-out;
}
.template-picker-option:hover {
  background-color: var(--bg-hover);
}
.template-picker-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.template-picker-name {
  font-size: 13px;
  flex: 1;
}
.template-picker-empty {
  font-size: 12px;
  color: var(--text-tertiary);
  padding: 8px;
  text-align: center;
}
.template-picker-create {
  color: var(--accent);
  border-top: 1px solid var(--border-subtle);
  margin-top: 4px;
  padding-top: 8px;
  font-size: 13px;
  text-align: center;
  cursor: pointer;
}
.template-picker-create:hover {
  background-color: var(--bg-hover);
}
.template-picker-edit-current {
  color: var(--accent);
  font-size: 12px;
  cursor: pointer;
}
.template-picker-remove-current {
  color: var(--danger);
  font-size: 12px;
  cursor: pointer;
}
.template-picker-divider {
  height: 1px;
  background-color: var(--border-subtle);
  margin: 4px 0;
}

.date-picker-popover {
  position: absolute;
  z-index: 100;
  background-color: var(--bg-surface-alt);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  box-shadow: var(--shadow-lg);
  padding: 16px;
  width: 264px;
  text-align: center;
}
.picker-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.picker-title {
  font-size: 14px;
  font-weight: 600;
}
.picker-nav-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
}
.picker-nav-btn:hover {
  color: var(--text-primary);
}
.picker-weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  font-size: 11px;
  color: var(--text-tertiary);
  margin-bottom: 8px;
}
.picker-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}
.picker-day {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  border-radius: 14px;
  cursor: pointer;
  margin: auto;
}
.picker-day:hover {
  background-color: var(--bg-hover);
}
.picker-day.is-today {
  color: var(--accent);
  font-weight: bold;
}
.picker-day.is-selected {
  background-color: var(--accent);
  color: var(--accent-on);
}
.picker-day.is-in-range {
  background-color: var(--accent-soft);
}
.picker-hint {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 12px;
}

/* Time components */
.time-scroller-popover {
  position: absolute;
  background-color: var(--bg-surface-alt);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  box-shadow: var(--shadow-md);
  padding: 8px;
  z-index: 100;
}
.time-scroller {
  display: flex;
  align-items: center;
  height: 150px;
}
.time-scroller-sep {
  font-size: 16px;
  font-weight: bold;
  margin: 0 8px;
}
.time-scroller-unit {
  /* wrapper */
}
.scroll-wheel-col {
  width: 40px;
  height: 100%;
  position: relative;
  overflow: hidden;
}
.scroll-wheel-highlight {
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 30px;
  transform: translateY(-50%);
  background-color: var(--accent-soft);
  border-radius: 4px;
  pointer-events: none;
}
.scroll-wheel-viewport {
  height: 100%;
  overflow-y: scroll;
  scroll-snap-type: y mandatory;
  scrollbar-width: none; /* Firefox */
}
.scroll-wheel-viewport::-webkit-scrollbar {
  display: none; /* Safari and Chrome */
}
.scroll-wheel-row {
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: var(--text-secondary);
  scroll-snap-align: center;
  cursor: pointer;
}
.scroll-wheel-row.is-selected {
  color: var(--text-primary);
  font-weight: bold;
}

.time-picker-field {
  display: flex;
  align-items: center;
  background-color: var(--bg-app);
  border: 1px solid var(--border-default);
  border-radius: 4px;
  padding: 4px 8px;
}
.time-picker-trigger {
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
}

/* Shift editor */
.shift-editor-row {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: relative;
}
.shift-editor-row-top {
  position: absolute;
  top: 8px;
  right: 8px;
}
.shift-field-label {
  text-transform: uppercase;
  font-size: 11px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}
.shift-id-field {
  width: 100%;
  background-color: var(--bg-app);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 13px;
}
.shift-color-dots {
  display: flex;
  gap: 8px;
}
.shift-ranges-block {
  background-color: var(--bg-surface-alt);
  border-radius: 6px;
  padding: 10px;
}
.shift-range-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.shift-range-row:last-child {
  margin-bottom: 0;
}
.shift-range-index {
  font-size: 12px;
  color: var(--text-tertiary);
  width: 20px;
}
.shift-time-sep {
  color: var(--text-secondary);
}
.shift-range-hrs {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-left: auto;
}
.shift-range-add {
  background: transparent;
  border: 1px dashed var(--border-strong);
  color: var(--text-secondary);
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
  cursor: pointer;
  display: block;
  width: 100%;
  margin-top: 8px;
}
.shift-range-add:hover {
  border-color: var(--accent);
  color: var(--accent);
}
.shift-editor-row-footer {
  display: flex;
  justify-content: flex-end;
}
.shift-save-btn {
  background-color: var(--accent);
  color: var(--accent-on);
  border: none;
  border-radius: 4px;
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
}
.shift-badge-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.shift-badge-icon {
  width: 36px;
  height: 36px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
}
.shift-badge-add {
  width: 36px;
  height: 36px;
  border-radius: 9px;
  border: 1px dashed var(--border-strong);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--text-secondary);
}
.shift-badge-add:hover {
  border-color: var(--accent);
  color: var(--accent);
}

/* Template full-view editor */
.template-full-view {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.template-full-topbar {
  height: 56px;
  display: flex;
  align-items: center;
  background-color: var(--bg-surface-alt);
  border-bottom: 1px solid var(--border-default);
  padding: 0 16px;
}
.template-full-back {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  margin-right: 16px;
}
.template-full-back:hover {
  color: var(--text-primary);
}
.template-full-topbar-title {
  font-size: 16px;
  font-weight: 600;
}
.template-full-topbar-actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
}
.template-full-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}
.template-editor-fieldset {
  border: none;
  padding: 0;
  margin: 0 0 24px 0;
}
.template-full-fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.template-full-row2 {
  grid-column: 1 / -1;
}
.color-swatch-row {
  display: flex;
  gap: 12px;
}
.color-swatch-lg {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid transparent;
}
.color-swatch-lg.is-selected {
  border-color: var(--text-primary);
}
.template-comments-textarea {
  width: 100%;
  background-color: var(--bg-app);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  border-radius: 4px;
  padding: 8px;
  min-height: 80px;
  font-family: inherit;
  font-size: 13px;
  resize: vertical;
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal-panel {
  background-color: var(--bg-surface-alt);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  box-shadow: var(--shadow-lg);
  max-width: 520px;
  width: 100%;
  display: flex;
  flex-direction: column;
}
.modal-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-default);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 16px;
  font-weight: 600;
}
.modal-body {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.modal-footer {
  padding: 14px 20px;
  border-top: 1px solid var(--border-default);
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.modal-close-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 16px;
  cursor: pointer;
}
.modal-close-btn:hover {
  color: var(--text-primary);
}
.modal-cancel-btn {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
}
.modal-cancel-btn:hover {
  background-color: var(--bg-hover);
}
.modal-save-btn {
  background-color: var(--accent);
  color: var(--accent-on);
  border: none;
  padding: 6px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
}
.modal-save-btn:hover {
  background-color: var(--accent-hover);
}
.confirm-dialog-panel {
  max-width: 420px;
}
.confirm-dialog-message {
  font-size: 14px;
  color: var(--text-secondary);
}
.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.form-row-full {
  grid-column: 1 / -1;
}

/* Tab pages */
.tab-page {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.tab-page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.tab-page-header h2 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}
.tab-filter-row {
  display: flex;
  gap: 12px;
  align-items: center;
}
.tab-search {
  background-color: var(--bg-surface-alt);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  display: flex;
  align-items: center;
  padding: 4px 8px;
  gap: 8px;
}
.tab-search input {
  background: transparent;
  border: none;
  color: var(--text-primary);
  outline: none;
  font-size: 13px;
}
.tab-filter-hint {
  font-size: 12px;
  color: var(--text-tertiary);
}
.tab-table {
  border: 1px solid var(--border-default);
  border-radius: 8px;
  overflow: hidden;
  background-color: var(--bg-surface);
}
.tab-table-row {
  display: grid;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-subtle);
  align-items: center;
}
.tab-table-row:last-child {
  border-bottom: none;
}
.tab-table-head {
  background-color: var(--bg-surface-alt);
  text-transform: uppercase;
  font-size: 11px;
  color: var(--text-tertiary);
  font-weight: 600;
}
.tab-sort-btn {
  background: transparent;
  border: none;
  color: inherit;
  font: inherit;
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  padding: 0;
}
.tab-sort-btn:hover {
  color: var(--accent);
}
.tab-table-name {
  font-size: 13px;
  font-weight: 500;
}
.tab-table-comments {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tab-table-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.tab-table-empty {
  padding: 24px;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 13px;
}
.template-table-row {
  grid-template-columns: 1.5fr 2.4fr 1fr .6fr .8fr;
}
.team-table-row {
  /* adjust based on content */
  grid-template-columns: repeat(10, 1fr);
}
.is-archived {
  opacity: 0.5;
}
.team-email {
  font-size: 12px;
  color: var(--text-secondary);
}
.team-text-action {
  background: transparent;
  border: none;
  color: var(--accent);
  font-size: 12px;
  cursor: pointer;
}
.team-text-action:hover {
  text-decoration: underline;
}

/* Settings */
.settings-page {
  max-width: 640px;
  margin: 0 auto;
  width: 100%;
}
.settings-section {
  background-color: var(--bg-surface-alt);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}
.settings-section h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13.5px;
  font-weight: 600;
  margin: 0 0 12px 0;
}
.settings-field {
  margin-bottom: 12px;
}
.settings-hint {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 4px;
}
.settings-role-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.settings-role-btn {
  background-color: var(--bg-app);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}
.settings-role-btn.is-selected {
  background-color: var(--accent-soft);
  border-color: var(--accent);
  color: var(--accent);
}
.settings-chip-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.settings-chip {
  background-color: var(--bg-active);
  padding: 4px 10px;
  border-radius: 14px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.settings-add-row {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
.settings-add-btn {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}
.settings-mode-row {
  display: flex;
  gap: 12px;
}
.settings-mode-btn {
  flex: 1;
  background-color: var(--bg-app);
  border: 1px solid var(--border-default);
  padding: 12px;
  border-radius: 6px;
  text-align: center;
  cursor: pointer;
  font-size: 13px;
}
.settings-mode-btn.is-selected {
  border-color: var(--accent);
  background-color: var(--accent-soft);
}
.settings-theme-row {
  display: flex;
  gap: 12px;
}
.settings-theme-swatch {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid transparent;
}
.settings-theme-swatch.is-selected {
  border-color: var(--text-primary);
}

/* Inputs */
.quick-edit-input {
  background-color: var(--bg-app);
  border: 1px solid var(--border-default);
  border-radius: 4px;
  padding: 7px 9px;
  font-size: 12px;
  color: var(--text-primary);
  outline: none;
  width: 100%;
}
.quick-edit-input:focus {
  border-color: var(--accent);
}

/* Buttons */
.tpl-icon-btn {
  width: 17px;
  height: 17px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
}
.tpl-icon-btn:hover {
  background-color: var(--bg-hover);
  color: var(--text-primary);
}
.tpl-icon-btn-danger:hover {
  background-color: var(--danger-soft);
  color: var(--danger);
}
.danger-btn {
  background-color: var(--danger);
  color: var(--danger-on);
  border: none;
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 13px;
  cursor: pointer;
}
.danger-btn-ghost {
  background: transparent;
  border: 1px solid var(--danger);
  color: var(--danger);
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 13px;
  cursor: pointer;
}
.danger-btn-ghost:hover {
  background-color: var(--danger-soft);
}

/* Custom view */
.custom-view {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}
.custom-view-card {
  text-align: center;
  max-width: 340px;
  color: var(--text-secondary);
}
.custom-view-card h3 {
  color: var(--text-primary);
  margin-bottom: 8px;
}

/* Profile menu */
.profile-menu-wrap {
  position: relative;
}
.profile-trigger {
  background: transparent;
  border: none;
  padding: 0;
  cursor: pointer;
}
.profile-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background-color: var(--accent-soft);
  color: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
}
.profile-popover {
  position: absolute;
  bottom: 40px; /* Assuming it's in the nav rail at the bottom */
  left: 40px;
  background-color: var(--bg-surface-alt);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  box-shadow: var(--shadow-lg);
  padding: 8px 0;
  min-width: 160px;
  z-index: 100;
}
.profile-popover-label {
  padding: 4px 12px;
  font-size: 10px;
  text-transform: uppercase;
  color: var(--text-tertiary);
}
.profile-ws-option {
  padding: 8px 12px;
  font-size: 13px;
  cursor: pointer;
  color: var(--text-secondary);
}
.profile-ws-option:hover {
  background-color: var(--bg-hover);
  color: var(--text-primary);
}
.profile-popover-divider {
  height: 1px;
  background-color: var(--border-subtle);
  margin: 4px 0;
}
.profile-login-btn {
  padding: 8px 12px;
  font-size: 13px;
  cursor: pointer;
  color: var(--accent);
  width: 100%;
  text-align: left;
  background: transparent;
  border: none;
}
.profile-login-btn:hover {
  background-color: var(--bg-hover);
}

/* Toast */
.toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  background-color: var(--bg-active);
  color: var(--text-primary);
  padding: 12px 24px;
  border-radius: 8px;
  box-shadow: var(--shadow-lg);
  font-size: 14px;
  z-index: 2000;
  animation: slide-up 200ms ease-out forwards;
}

@keyframes slide-up {
  from { opacity: 0; transform: translate(-50%, 20px); }
  to { opacity: 1; transform: translate(-50%, 0); }
}

/* Scrollbar */
::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background-color: var(--bg-active);
  border-radius: 5px;
  border: 2px solid transparent;
  background-clip: content-box;
}
::-webkit-scrollbar-thumb:hover {
  background-color: var(--text-tertiary);
}

/* Focus */
button:focus-visible, input:focus-visible, select:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
  border-radius: 4px;
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}

/* Quick-color-dot */
.quick-color-dot {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid transparent;
}
.quick-color-dot.tpl-teal { background-color: var(--tpl-teal-dot); }
.quick-color-dot.tpl-amber { background-color: var(--tpl-amber-dot); }
.quick-color-dot.tpl-burgundy { background-color: var(--tpl-burgundy-dot); }
.quick-color-dot.tpl-blue { background-color: var(--tpl-blue-dot); }
.quick-color-dot.tpl-purple { background-color: var(--tpl-purple-dot); }

.quick-color-dot.is-selected {
  border-color: var(--text-primary);
}

/* Shift badge icon variants */
.shift-badge-icon.tpl-teal { background-color: var(--tpl-teal-bg); color: var(--tpl-teal-fg); border: 1px solid var(--tpl-teal-dot); }
.shift-badge-icon.tpl-amber { background-color: var(--tpl-amber-bg); color: var(--tpl-amber-fg); border: 1px solid var(--tpl-amber-dot); }
.shift-badge-icon.tpl-burgundy { background-color: var(--tpl-burgundy-bg); color: var(--tpl-burgundy-fg); border: 1px solid var(--tpl-burgundy-dot); }
.shift-badge-icon.tpl-blue { background-color: var(--tpl-blue-bg); color: var(--tpl-blue-fg); border: 1px solid var(--tpl-blue-dot); }
.shift-badge-icon.tpl-purple { background-color: var(--tpl-purple-bg); color: var(--tpl-purple-fg); border: 1px solid var(--tpl-purple-dot); }

.roster-shift-badge.tpl-teal { background-color: var(--tpl-teal-bg); color: var(--tpl-teal-fg); border: 1px solid var(--tpl-teal-dot); }
.roster-shift-badge.tpl-amber { background-color: var(--tpl-amber-bg); color: var(--tpl-amber-fg); border: 1px solid var(--tpl-amber-dot); }
.roster-shift-badge.tpl-burgundy { background-color: var(--tpl-burgundy-bg); color: var(--tpl-burgundy-fg); border: 1px solid var(--tpl-burgundy-dot); }
.roster-shift-badge.tpl-blue { background-color: var(--tpl-blue-bg); color: var(--tpl-blue-fg); border: 1px solid var(--tpl-blue-dot); }
.roster-shift-badge.tpl-purple { background-color: var(--tpl-purple-bg); color: var(--tpl-purple-fg); border: 1px solid var(--tpl-purple-dot); }

.timeline-bar.tpl-teal { background-color: var(--tpl-teal-bg); color: var(--tpl-teal-fg); border: 1px solid var(--tpl-teal-dot); }
.timeline-bar.tpl-amber { background-color: var(--tpl-amber-bg); color: var(--tpl-amber-fg); border: 1px solid var(--tpl-amber-dot); }
.timeline-bar.tpl-burgundy { background-color: var(--tpl-burgundy-bg); color: var(--tpl-burgundy-fg); border: 1px solid var(--tpl-burgundy-dot); }
.timeline-bar.tpl-blue { background-color: var(--tpl-blue-bg); color: var(--tpl-blue-fg); border: 1px solid var(--tpl-blue-dot); }
.timeline-bar.tpl-purple { background-color: var(--tpl-purple-bg); color: var(--tpl-purple-fg); border: 1px solid var(--tpl-purple-dot); }
`;
