import React, { useState, useRef, useEffect, useMemo, useLayoutEffect } from 'react';
import {
  ChevronDown, ChevronLeft, ChevronRight, Plus, Pencil, Trash2, GripVertical,
  CalendarDays, LayoutTemplate, Users, Printer, LayoutDashboard, Bell, Info,
  Settings, Menu, Check, User, Filter, ArrowUpDown, Search,
  Building2, ShieldCheck, KeyRound, Briefcase, Mail, Clock,
  ClipboardList, FileBarChart, CalendarOff, UserCog, X, Sun, Moon, Palette,
} from 'lucide-react';

/* ------------------------------------------------------------------ */
/* Constants                                                            */
/* ------------------------------------------------------------------ */

const WEEKDAY_BASE = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const WEEKDAY_FULL_BASE = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const MONTH_LABELS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];
const SCALES = ['Year', 'Month', 'Week', 'Day', 'Custom'];
const TEMPLATE_COLORS = ['blue', 'green', 'amber', 'red', 'purple'];
const TODAY = new Date(2026, 7, 5); // Wed, Aug 5 2026 — fixed so the demo always reads correctly

const INITIAL_DEPARTMENTS = ['Dealers', 'Supervisors', 'Managers'];
const INITIAL_ROLES = ['Dealer 1', 'Dealer 2', 'Dealer 3', 'Dealer 4', 'Pit Supervisor', 'Senior Supervisor', 'Casino Manager', 'Assistant Casino Manager', 'Operations Manager', 'Floor Manager', 'Training Manager'];
const INITIAL_POSITIONS = ['B1', 'B2', 'B3', 'RW1', 'RW2', 'BJ1', 'BJ2', 'BJ3', 'CR1', 'PK1', 'BRK', 'FLOAT'];
const WORKSPACES = ['Sunrise Retail Group', 'Harbor Hospitality Co.', 'Blue Ridge Logistics'];
const USER_ROLES = ['License Keeper', 'Admin', 'Manager', 'Assistant Manager', 'Supervisor'];

const COLOR_THEMES = {
  blue: { name: 'Blue', dark: { accent: '#8ab4f8', hover: '#aecbfa', on: '#062e6f', soft: 'rgba(138,180,248,.16)', cta: '#4c8dff', ctaHover: '#699dff', ctaOn: '#ffffff' }, light: { accent: '#3b6fd6', hover: '#2955ad', on: '#ffffff', soft: 'rgba(59,111,214,.12)', cta: '#3b6fd6', ctaHover: '#2955ad', ctaOn: '#ffffff' } },
  green: { name: 'Green', dark: { accent: '#81c995', hover: '#a8dab5', on: '#0b3d1e', soft: 'rgba(129,201,149,.16)', cta: '#2fb350', ctaHover: '#4cc46b', ctaOn: '#ffffff' }, light: { accent: '#1e8e4a', hover: '#166937', on: '#ffffff', soft: 'rgba(30,142,74,.12)', cta: '#1e8e4a', ctaHover: '#166937', ctaOn: '#ffffff' } },
  purple: { name: 'Purple', dark: { accent: '#c58af9', hover: '#d7aefb', on: '#3a0d63', soft: 'rgba(197,138,249,.16)', cta: '#a142f4', ctaHover: '#b565f6', ctaOn: '#ffffff' }, light: { accent: '#8430ce', hover: '#6b23a8', on: '#ffffff', soft: 'rgba(132,48,206,.12)', cta: '#8430ce', ctaHover: '#6b23a8', ctaOn: '#ffffff' } },
  rose: { name: 'Rose', dark: { accent: '#f6a3ae', hover: '#f8bcc4', on: '#5c0a1c', soft: 'rgba(246,163,174,.18)', cta: '#e8496b', ctaHover: '#ee6a87', ctaOn: '#ffffff' }, light: { accent: '#d23a63', hover: '#ab2c4f', on: '#ffffff', soft: 'rgba(210,58,99,.12)', cta: '#d23a63', ctaHover: '#ab2c4f', ctaOn: '#ffffff' } },
  amber: { name: 'Amber', dark: { accent: '#fdd663', hover: '#fde293', on: '#4a3400', soft: 'rgba(253,214,99,.16)', cta: '#f2a600', ctaHover: '#f7bb33', ctaOn: '#1f1500' }, light: { accent: '#a6720a', hover: '#845a08', on: '#ffffff', soft: 'rgba(166,114,10,.12)', cta: '#c98a06', ctaHover: '#a6720a', ctaOn: '#ffffff' } },
};
const SURFACE_THEMES = {
  dark: { surface0: '#131314', surface1: '#1e1f20', surface2: '#28292a', surface3: '#303134', surface4: '#3c3d40', border: 'rgba(255,255,255,0.09)', borderStrong: 'rgba(255,255,255,0.16)', textPrimary: '#e8eaed', textSecondary: '#9aa0a6', textTertiary: '#5f6368', danger: '#f28b82', dangerOn: '#410002', dangerSoft: 'rgba(242,139,130,.15)', shadowA: '.3', shadowB: '.35', shadowC: '.45' },
  light: { surface0: '#eef0f2', surface1: '#ffffff', surface2: '#f6f7f8', surface3: '#eceef0', surface4: '#e1e3e6', border: 'rgba(0,0,0,0.09)', borderStrong: 'rgba(0,0,0,0.16)', textPrimary: '#1f1f1f', textSecondary: '#5f6368', textTertiary: '#80868b', danger: '#d93025', dangerOn: '#ffffff', dangerSoft: 'rgba(217,48,37,.08)', shadowA: '.10', shadowB: '.12', shadowC: '.16' },
};
function getThemeVars(mode, themeKey) {
  const s = SURFACE_THEMES[mode];
  const a = (COLOR_THEMES[themeKey] || COLOR_THEMES.blue)[mode];
  return {
    '--surface-0': s.surface0, '--surface-1': s.surface1, '--surface-2': s.surface2, '--surface-3': s.surface3, '--surface-4': s.surface4,
    '--border': s.border, '--border-strong': s.borderStrong,
    '--text-primary': s.textPrimary, '--text-secondary': s.textSecondary, '--text-tertiary': s.textTertiary,
    '--accent': a.accent, '--accent-hover': a.hover, '--accent-on': a.on, '--accent-soft-bg': a.soft,
    '--cta': a.cta, '--cta-hover': a.ctaHover, '--cta-on': a.ctaOn,
    '--danger': s.danger, '--danger-on': s.dangerOn, '--danger-soft-bg': s.dangerSoft,
    '--shadow-sm': `0 1px 2px rgba(0,0,0,${s.shadowA}), 0 1px 3px rgba(0,0,0,${s.shadowA})`,
    '--shadow-md': `0 4px 12px rgba(0,0,0,${s.shadowB}), 0 1px 3px rgba(0,0,0,${s.shadowA})`,
    '--shadow-lg': `0 12px 32px rgba(0,0,0,${s.shadowC}), 0 4px 10px rgba(0,0,0,${s.shadowB})`,
    '--dur-fast': '140ms',
    '--dur-med': '220ms',
    '--ease': 'cubic-bezier(0.2, 0, 0, 1)',
    colorScheme: mode,
  };
}

const NAV_ITEMS_MAIN = [
  { key: 'schedule', label: 'Schedule', icon: CalendarDays },
  { key: 'templates', label: 'Templates', icon: LayoutTemplate },
  { key: 'team', label: 'Team', icon: Users },
  { key: 'print', label: 'Print Center', icon: Printer },
  { key: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { key: 'reports', label: 'Report Center', icon: FileBarChart },
  { key: 'offtracker', label: 'Off Tracker', icon: CalendarOff },
  { key: 'notifications', label: 'Notifications', icon: Bell },
];
const NAV_ITEMS_BOTTOM = [
  { key: 'about', label: 'About', icon: Info },
  { key: 'help', label: 'Guide', icon: ClipboardList },
  { key: 'settings', label: 'Settings', icon: Settings },
];

/* ------------------------------------------------------------------ */
/* Sample data — staff, templates (own their shifts), assignments, roster */
/* ------------------------------------------------------------------ */

const STAFF = [
  { id: '20100', firstName: 'David', lastName: "Whitfield", department: 'Managers', position: 'Casino Manager', email: 'david.whitfield@rostastudio.app' },
  { id: '20101', firstName: 'Marcus', lastName: "Okonkwo", department: 'Managers', position: 'Assistant Casino Manager', email: 'marcus.okonkwo@rostastudio.app' },
  { id: '20102', firstName: 'Elena', lastName: "Petrova", department: 'Managers', position: 'Operations Manager', email: 'elena.petrova@rostastudio.app' },
  { id: '20103', firstName: 'Priya', lastName: "Raghavan", department: 'Managers', position: 'Floor Manager', email: 'priya.raghavan@rostastudio.app' },
  { id: '20104', firstName: 'Andre', lastName: "Delacroix", department: 'Managers', position: 'Training Manager', email: 'andre.delacroix@rostastudio.app' },
  { id: '20200', firstName: 'Ryan', lastName: "O'Connell", department: 'Supervisors', position: 'Pit Supervisor', email: 'ryan.oconnell@rostastudio.app' },
  { id: '20201', firstName: 'Fatima', lastName: "Al-Rashid", department: 'Supervisors', position: 'Pit Supervisor', email: 'fatima.al-rashid@rostastudio.app' },
  { id: '20202', firstName: 'Noah', lastName: "Bergstrom", department: 'Supervisors', position: 'Senior Supervisor', email: 'noah.bergstrom@rostastudio.app' },
  { id: '20203', firstName: 'Chloe', lastName: "Dubois", department: 'Supervisors', position: 'Pit Supervisor', email: 'chloe.dubois@rostastudio.app' },
  { id: '20204', firstName: 'Tariq', lastName: "Osei", department: 'Supervisors', position: 'Senior Supervisor', email: 'tariq.osei@rostastudio.app' },
  { id: '20205', firstName: 'Ingrid', lastName: "Larsen", department: 'Supervisors', position: 'Pit Supervisor', email: 'ingrid.larsen@rostastudio.app' },
  { id: '20206', firstName: 'Diego', lastName: "Fernandez", department: 'Supervisors', position: 'Pit Supervisor', email: 'diego.fernandez@rostastudio.app' },
  { id: '20207', firstName: 'Hannah', lastName: "Cole", department: 'Supervisors', position: 'Senior Supervisor', email: 'hannah.cole@rostastudio.app' },
  { id: '20208', firstName: 'Wei', lastName: "Zhang", department: 'Supervisors', position: 'Pit Supervisor', email: 'wei.zhang@rostastudio.app' },
  { id: '20209', firstName: 'Sofia', lastName: "Ricci", department: 'Supervisors', position: 'Pit Supervisor', email: 'sofia.ricci@rostastudio.app' },
  { id: '20210', firstName: 'Omar', lastName: "Haddad", department: 'Supervisors', position: 'Senior Supervisor', email: 'omar.haddad@rostastudio.app' },
  { id: '20211', firstName: 'Lucia', lastName: "Moreno", department: 'Supervisors', position: 'Pit Supervisor', email: 'lucia.moreno@rostastudio.app' },
  { id: '20300', firstName: 'Maria', lastName: "Santos", department: 'Dealers', position: 'Dealer 1', email: 'maria.santos@rostastudio.app' },
  { id: '20301', firstName: 'James', lastName: "Cooper", department: 'Dealers', position: 'Dealer 2', email: 'james.cooper@rostastudio.app' },
  { id: '20302', firstName: 'Aiko', lastName: "Tanaka", department: 'Dealers', position: 'Dealer 3', email: 'aiko.tanaka@rostastudio.app' },
  { id: '20303', firstName: 'Daniel', lastName: "Kim", department: 'Dealers', position: 'Dealer 4', email: 'daniel.kim@rostastudio.app' },
  { id: '20304', firstName: 'Nadia', lastName: "Hassan", department: 'Dealers', position: 'Dealer 1', email: 'nadia.hassan@rostastudio.app' },
  { id: '20305', firstName: 'Ethan', lastName: "Brooks", department: 'Dealers', position: 'Dealer 2', email: 'ethan.brooks@rostastudio.app' },
  { id: '20306', firstName: 'Lucas', lastName: "Silva", department: 'Dealers', position: 'Dealer 3', email: 'lucas.silva@rostastudio.app' },
  { id: '20307', firstName: 'Amara', lastName: "Nwosu", department: 'Dealers', position: 'Dealer 4', email: 'amara.nwosu@rostastudio.app' },
  { id: '20308', firstName: 'Kenji', lastName: "Watanabe", department: 'Dealers', position: 'Dealer 1', email: 'kenji.watanabe@rostastudio.app' },
  { id: '20309', firstName: 'Isabel', lastName: "Reyes", department: 'Dealers', position: 'Dealer 2', email: 'isabel.reyes@rostastudio.app' },
  { id: '20310', firstName: 'Tomas', lastName: "Novak", department: 'Dealers', position: 'Dealer 3', email: 'tomas.novak@rostastudio.app' },
  { id: '20311', firstName: 'Yara', lastName: "Haddad", department: 'Dealers', position: 'Dealer 4', email: 'yara.haddad@rostastudio.app' },
  { id: '20312', firstName: 'Viktor', lastName: "Petrov", department: 'Dealers', position: 'Dealer 1', email: 'viktor.petrov@rostastudio.app' },
  { id: '20313', firstName: 'Leila', lastName: "Karim", department: 'Dealers', position: 'Dealer 2', email: 'leila.karim@rostastudio.app' },
  { id: '20314', firstName: 'Marcus', lastName: "Webb", department: 'Dealers', position: 'Dealer 3', email: 'marcus.webb@rostastudio.app' },
  { id: '20315', firstName: 'Nina', lastName: "Andersen", department: 'Dealers', position: 'Dealer 4', email: 'nina.andersen@rostastudio.app' },
  { id: '20316', firstName: 'Pavel', lastName: "Volkov", department: 'Dealers', position: 'Dealer 1', email: 'pavel.volkov@rostastudio.app' },
  { id: '20317', firstName: 'Rosa', lastName: "Guerrero", department: 'Dealers', position: 'Dealer 2', email: 'rosa.guerrero@rostastudio.app' },
  { id: '20318', firstName: 'Samuel', lastName: "Adeyemi", department: 'Dealers', position: 'Dealer 3', email: 'samuel.adeyemi@rostastudio.app' },
  { id: '20319', firstName: 'Thandi', lastName: "Mbeki", department: 'Dealers', position: 'Dealer 4', email: 'thandi.mbeki@rostastudio.app' },
  { id: '20320', firstName: 'Ulises', lastName: "Ortega", department: 'Dealers', position: 'Dealer 1', email: 'ulises.ortega@rostastudio.app' },
  { id: '20321', firstName: 'Vera', lastName: "Lindqvist", department: 'Dealers', position: 'Dealer 2', email: 'vera.lindqvist@rostastudio.app' },
  { id: '20322', firstName: 'Wesley', lastName: "Chan", department: 'Dealers', position: 'Dealer 3', email: 'wesley.chan@rostastudio.app' },
  { id: '20323', firstName: 'Ximena', lastName: "Duarte", department: 'Dealers', position: 'Dealer 4', email: 'ximena.duarte@rostastudio.app' },
  { id: '20324', firstName: 'Yusuf', lastName: "Demir", department: 'Dealers', position: 'Dealer 1', email: 'yusuf.demir@rostastudio.app' },
  { id: '20325', firstName: 'Zara', lastName: "Malik", department: 'Dealers', position: 'Dealer 2', email: 'zara.malik@rostastudio.app' },
].map((s) => ({ ...s, name: `${s.firstName} ${s.lastName}`, archived: false }));

function mkShift(id, start, end, role, color, comments) {
  return { id, ranges: [{ start, end }], role, color, comments: comments || '' };
}

const TEMPLATES = [
  { id: 'tpl-sea-dealers', name: 'Sea Day', comments: ['No port call today', 'Casino Op 10:00 AM · CL 3:00 AM'], department: 'Dealers', color: 'green', shifts: [
    mkShift('1','08:00','16:00','Dealer','blue'), mkShift('2','10:00','18:00','Dealer','amber'), mkShift('3','12:00','20:00','Dealer','green'), mkShift('CL1','18:00','02:00','Dealer','purple','Closing'), mkShift('CL2','19:00','03:00','Dealer','red','Closing'),
  ] },
  { id: 'tpl-sea-supervisors', name: 'Sea Day', comments: ['No port call today', 'Casino Op 10:00 AM · CL 3:00 AM'], department: 'Supervisors', color: 'green', shifts: [
    mkShift('S1','08:00','16:00','Supervisor','blue'), mkShift('S2','11:00','19:00','Supervisor','green'), mkShift('SCL','16:00','00:00','Supervisor','purple','Closing'),
  ] },
  { id: 'tpl-sea-managers', name: 'Sea Day', comments: ['No port call today', 'Casino Op 10:00 AM · CL 3:00 AM'], department: 'Managers', color: 'green', shifts: [
    mkShift('M1','09:00','17:00','Manager','blue'), mkShift('MCL','17:00','01:00','Manager','purple','Closing'),
  ] },
  { id: 'tpl-cozumel-dealers', name: 'Cozumel', comments: ['ETA 8:00 AM · ETD 6:00 PM', 'Casino Op 6:30 PM · CL 3:00 AM'], department: 'Dealers', color: 'blue', shifts: [
    mkShift('1','08:00','16:00','Dealer','blue'), mkShift('2','11:00','19:00','Dealer','amber'), mkShift('CL1','18:30','03:00','Dealer','purple','Closing'), mkShift('CL2','19:00','03:30','Dealer','red','Closing'),
  ] },
  { id: 'tpl-cozumel-supervisors', name: 'Cozumel', comments: ['ETA 8:00 AM · ETD 6:00 PM', 'Casino Op 6:30 PM · CL 3:00 AM'], department: 'Supervisors', color: 'blue', shifts: [
    mkShift('S1','07:30','15:30','Supervisor','blue'), mkShift('SCL','18:00','02:00','Supervisor','purple','Closing'),
  ] },
  { id: 'tpl-cozumel-managers', name: 'Cozumel', comments: ['ETA 8:00 AM · ETD 6:00 PM', 'Casino Op 6:30 PM · CL 3:00 AM'], department: 'Managers', color: 'blue', shifts: [
    mkShift('M1','08:00','16:00','Manager','blue'), mkShift('MCL','18:00','02:00','Manager','purple','Closing'),
  ] },
  { id: 'tpl-nassau-dealers', name: 'Nassau', comments: ['ETA 7:00 AM · ETD 5:00 PM', 'Casino Op 5:30 PM · CL 2:00 AM'], department: 'Dealers', color: 'amber', shifts: [
    mkShift('1','07:30','15:30','Dealer','blue'), mkShift('2','10:30','18:30','Dealer','amber'), mkShift('CL1','18:00','02:00','Dealer','purple','Closing'),
  ] },
  { id: 'tpl-nassau-supervisors', name: 'Nassau', comments: ['ETA 7:00 AM · ETD 5:00 PM', 'Casino Op 5:30 PM · CL 2:00 AM'], department: 'Supervisors', color: 'amber', shifts: [
    mkShift('S1','07:00','15:00','Supervisor','blue'), mkShift('SCL','17:30','01:30','Supervisor','purple','Closing'),
  ] },
  { id: 'tpl-nassau-managers', name: 'Nassau', comments: ['ETA 7:00 AM · ETD 5:00 PM', 'Casino Op 5:30 PM · CL 2:00 AM'], department: 'Managers', color: 'amber', shifts: [
    mkShift('M1','08:00','16:00','Manager','blue'), mkShift('MCL','17:00','01:00','Manager','purple','Closing'),
  ] },
  { id: 'tpl-grandcayman-dealers', name: 'Grand Cayman', comments: ['ETA 7:30 AM · ETD 4:30 PM', 'Casino Op 5:00 PM · CL 2:30 AM'], department: 'Dealers', color: 'purple', shifts: [
    mkShift('1','08:00','16:00','Dealer','blue'), mkShift('2','10:00','18:00','Dealer','amber'), mkShift('CL1','17:30','01:30','Dealer','purple','Closing'),
  ] },
  { id: 'tpl-grandcayman-supervisors', name: 'Grand Cayman', comments: ['ETA 7:30 AM · ETD 4:30 PM', 'Casino Op 5:00 PM · CL 2:30 AM'], department: 'Supervisors', color: 'purple', shifts: [
    mkShift('S1','07:30','15:30','Supervisor','blue'), mkShift('SCL','17:00','01:00','Supervisor','purple','Closing'),
  ] },
  { id: 'tpl-grandcayman-managers', name: 'Grand Cayman', comments: ['ETA 7:30 AM · ETD 4:30 PM', 'Casino Op 5:00 PM · CL 2:30 AM'], department: 'Managers', color: 'purple', shifts: [
    mkShift('M1','08:00','16:00','Manager','blue'), mkShift('MCL','17:00','01:00','Manager','purple','Closing'),
  ] },
  { id: 'tpl-stthomas-dealers', name: 'St. Thomas', comments: ['ETA 8:00 AM · ETD 5:30 PM', 'Casino Op 6:00 PM · CL 2:30 AM'], department: 'Dealers', color: 'red', shifts: [
    mkShift('1','08:30','16:30','Dealer','blue'), mkShift('2','11:00','19:00','Dealer','amber'), mkShift('CL1','18:00','02:00','Dealer','purple','Closing'),
  ] },
  { id: 'tpl-stthomas-supervisors', name: 'St. Thomas', comments: ['ETA 8:00 AM · ETD 5:30 PM', 'Casino Op 6:00 PM · CL 2:30 AM'], department: 'Supervisors', color: 'red', shifts: [
    mkShift('S1','08:00','16:00','Supervisor','blue'), mkShift('SCL','17:30','01:30','Supervisor','purple','Closing'),
  ] },
  { id: 'tpl-stthomas-managers', name: 'St. Thomas', comments: ['ETA 8:00 AM · ETD 5:30 PM', 'Casino Op 6:00 PM · CL 2:30 AM'], department: 'Managers', color: 'red', shifts: [
    mkShift('M1','08:30','16:30','Manager','blue'), mkShift('MCL','17:30','01:30','Manager','purple','Closing'),
  ] },
];

const PORT_ROTATION = [
  ['2026-06-01', 'tpl-grandcayman'], ['2026-06-02', 'tpl-sea'], ['2026-06-03', 'tpl-sea'], ['2026-06-04', 'tpl-stthomas'],
  ['2026-06-05', 'tpl-sea'], ['2026-06-06', 'tpl-sea'], ['2026-06-07', 'tpl-nassau'], ['2026-06-08', 'tpl-sea'],
  ['2026-06-09', 'tpl-cozumel'], ['2026-06-10', 'tpl-sea'], ['2026-06-11', 'tpl-sea'], ['2026-06-12', 'tpl-nassau'],
  ['2026-06-13', 'tpl-sea'], ['2026-06-14', 'tpl-grandcayman'], ['2026-06-15', 'tpl-grandcayman'], ['2026-06-16', 'tpl-sea'],
  ['2026-06-17', 'tpl-sea'], ['2026-06-18', 'tpl-stthomas'], ['2026-06-19', 'tpl-sea'], ['2026-06-20', 'tpl-sea'],
  ['2026-06-21', 'tpl-nassau'], ['2026-06-22', 'tpl-sea'], ['2026-06-23', 'tpl-cozumel'], ['2026-06-24', 'tpl-sea'],
  ['2026-06-25', 'tpl-sea'], ['2026-06-26', 'tpl-nassau'], ['2026-06-27', 'tpl-sea'], ['2026-06-28', 'tpl-grandcayman'],
  ['2026-06-29', 'tpl-grandcayman'], ['2026-06-30', 'tpl-sea'], ['2026-07-01', 'tpl-sea'], ['2026-07-02', 'tpl-stthomas'],
  ['2026-07-03', 'tpl-sea'], ['2026-07-04', 'tpl-sea'], ['2026-07-05', 'tpl-nassau'], ['2026-07-06', 'tpl-sea'],
  ['2026-07-07', 'tpl-cozumel'], ['2026-07-08', 'tpl-sea'], ['2026-07-09', 'tpl-sea'], ['2026-07-10', 'tpl-nassau'],
  ['2026-07-11', 'tpl-sea'], ['2026-07-12', 'tpl-grandcayman'], ['2026-07-13', 'tpl-grandcayman'], ['2026-07-14', 'tpl-sea'],
  ['2026-07-15', 'tpl-sea'], ['2026-07-16', 'tpl-stthomas'], ['2026-07-17', 'tpl-sea'], ['2026-07-18', 'tpl-sea'],
  ['2026-07-19', 'tpl-nassau'], ['2026-07-20', 'tpl-sea'], ['2026-07-21', 'tpl-cozumel'], ['2026-07-22', 'tpl-sea'],
  ['2026-07-23', 'tpl-sea'], ['2026-07-24', 'tpl-nassau'], ['2026-07-25', 'tpl-sea'], ['2026-07-26', 'tpl-grandcayman'],
  ['2026-07-27', 'tpl-grandcayman'], ['2026-07-28', 'tpl-sea'], ['2026-07-29', 'tpl-sea'], ['2026-07-30', 'tpl-stthomas'],
  ['2026-07-31', 'tpl-sea'], ['2026-08-01', 'tpl-sea'], ['2026-08-02', 'tpl-nassau'], ['2026-08-03', 'tpl-sea'],
  ['2026-08-04', 'tpl-cozumel'], ['2026-08-05', 'tpl-sea'], ['2026-08-06', 'tpl-sea'], ['2026-08-07', 'tpl-nassau'],
  ['2026-08-08', 'tpl-sea'], ['2026-08-09', 'tpl-grandcayman'], ['2026-08-10', 'tpl-grandcayman'], ['2026-08-11', 'tpl-sea'],
  ['2026-08-12', 'tpl-sea'], ['2026-08-13', 'tpl-stthomas'], ['2026-08-14', 'tpl-sea'], ['2026-08-15', 'tpl-sea'],
  ['2026-08-16', 'tpl-nassau'], ['2026-08-17', 'tpl-sea'], ['2026-08-18', 'tpl-cozumel'], ['2026-08-19', 'tpl-sea'],
  ['2026-08-20', 'tpl-sea'], ['2026-08-21', 'tpl-nassau'], ['2026-08-22', 'tpl-sea'], ['2026-08-23', 'tpl-grandcayman'],
  ['2026-08-24', 'tpl-grandcayman'], ['2026-08-25', 'tpl-sea'], ['2026-08-26', 'tpl-sea'], ['2026-08-27', 'tpl-stthomas'],
  ['2026-08-28', 'tpl-sea'], ['2026-08-29', 'tpl-sea'], ['2026-08-30', 'tpl-nassau'], ['2026-08-31', 'tpl-sea'],
];
const INITIAL_ASSIGNMENTS = {};
PORT_ROTATION.forEach(([dateKey, base]) => {
  INITIAL_ASSIGNMENTS[`${dateKey}__Dealers`] = `${base}-dealers`;
  INITIAL_ASSIGNMENTS[`${dateKey}__Supervisors`] = `${base}-supervisors`;
  INITIAL_ASSIGNMENTS[`${dateKey}__Managers`] = `${base}-managers`;
});

function rk(name, dateKey) { return `${name}__${dateKey}`; }

/* Roster is generated from the rotation so every day in the demo period is
   realistically staffed: crew cycle through the shifts of whichever template
   their department has that day, with a recurring day off. */
const INITIAL_ROSTER = (() => {
  const out = {};
  const byDept = { Dealers: [], Supervisors: [], Managers: [] };
  STAFF.forEach((s) => { if (byDept[s.department]) byDept[s.department].push(s); });

  PORT_ROTATION.forEach(([dateKey, base], dayIdx) => {
    Object.keys(byDept).forEach((dept) => {
      const tpl = TEMPLATES.find((t) => t.id === `${base}-${dept.toLowerCase()}`);
      if (!tpl || tpl.shifts.length === 0) return;
      const crew = byDept[dept];

      /* Real rosters are never perfectly full. Every few days one shift is
         deliberately left open so coverage reporting, the dashboard gap list
         and notifications reflect a realistic operation rather than a
         permanently-green demo. */
      const leaveOpen = (dayIdx % 6 === 3) ? tpl.shifts[(dayIdx / 3) % tpl.shifts.length].id : null;

      crew.forEach((person, i) => {
        // Each person gets a rolling day off every 7th day, offset per person.
        if ((dayIdx + i) % 7 === 0) return;
        const shift = tpl.shifts[(i + dayIdx) % tpl.shifts.length];
        if (shift.id === leaveOpen) return;
        out[rk(person.name, dateKey)] = {
          shiftId: shift.id,
          ranges: shift.ranges.map((r) => ({ ...r })),
        };
      });
    });
  });
  return out;
})();


/* ------------------------------------------------------------------ */
/* Date / time utilities                                                */
/* ------------------------------------------------------------------ */

function toKey(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}
function isSameDay(a, b) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}
function addDays(date, n) { const d = new Date(date); d.setDate(d.getDate() + n); return d; }
function addMonths(date, n) { const d = new Date(date); d.setMonth(d.getMonth() + n); return d; }
function addYears(date, n) { const d = new Date(date); d.setFullYear(d.getFullYear() + n); return d; }
function startOfWeek(date, weekStartsOn) {
  const d = new Date(date);
  const day = d.getDay();
  const diff = (day - weekStartsOn + 7) % 7;
  d.setDate(d.getDate() - diff);
  return d;
}
function getMonthMatrix(year, month, weekStartsOn) {
  const firstOfMonth = new Date(year, month, 1);
  const start = startOfWeek(firstOfMonth, weekStartsOn);
  const weeks = [];
  let cur = new Date(start);
  for (let w = 0; w < 6; w++) {
    const week = [];
    for (let d = 0; d < 7; d++) {
      week.push({ date: new Date(cur), inMonth: cur.getMonth() === month });
      cur.setDate(cur.getDate() + 1);
    }
    weeks.push(week);
  }
  return weeks;
}
function getWeekdayLabels(weekStartsOn, full) {
  const base = full ? WEEKDAY_FULL_BASE : WEEKDAY_BASE;
  return [...base.slice(weekStartsOn), ...base.slice(0, weekStartsOn)];
}
function getWeekNumber(date) {
  const start = new Date(date.getFullYear(), 0, 1);
  const days = Math.floor((date - start) / 86400000);
  return Math.ceil((days + start.getDay() + 1) / 7);
}
function formatShortDate(date) {
  return `${MONTH_LABELS[date.getMonth()].slice(0, 3)} ${date.getDate()}, ${date.getFullYear()}`;
}
function formatTime12h(hhmm) {
  const [h, m] = hhmm.split(':').map(Number);
  const period = h >= 12 ? 'PM' : 'AM';
  let h12 = h % 12; if (h12 === 0) h12 = 12;
  return `${h12}:${String(m).padStart(2, '0')} ${period}`;
}
function computeHours(start, end) {
  const [sh, sm] = start.split(':').map(Number);
  const [eh, em] = end.split(':').map(Number);
  let sMin = sh * 60 + sm;
  let eMin = eh * 60 + em;
  if (eMin <= sMin) eMin += 24 * 60;
  return Math.round(((eMin - sMin) / 60) * 10) / 10;
}
function computeEntryHours(entry) {
  return Math.round(entry.ranges.reduce((sum, r) => sum + computeHours(r.start, r.end), 0) * 10) / 10;
}
/* Consistent numeric display: one decimal place so columns align optically
   (8 -> "8.0", 7.5 -> "7.5"). Used anywhere hours appear in a column. */
function fmtHrs(n) {
  return (Math.round(n * 10) / 10).toFixed(1);
}
function getPeriodLabel(scale, date, customRange) {
  switch (scale) {
    case 'Year': return `${date.getFullYear()}`;
    case 'Month': return `${MONTH_LABELS[date.getMonth()]} ${date.getFullYear()}`;
    case 'Week': {
      const start = startOfWeek(date, 0);
      const end = addDays(start, 6);
      const sameMonth = start.getMonth() === end.getMonth();
      const startLabel = `${MONTH_LABELS[start.getMonth()].slice(0, 3)} ${start.getDate()}`;
      const endLabel = sameMonth ? `${end.getDate()}` : `${MONTH_LABELS[end.getMonth()].slice(0, 3)} ${end.getDate()}`;
      return `${startLabel}–${endLabel}, ${end.getFullYear()}`;
    }
    case 'Day': return `${WEEKDAY_FULL_BASE[date.getDay()]}, ${MONTH_LABELS[date.getMonth()].slice(0, 3)} ${date.getDate()}, ${date.getFullYear()}`;
    case 'Custom':
      if (!customRange || !customRange.start || !customRange.end) return 'Select a range';
      return `${formatShortDate(customRange.start)} – ${formatShortDate(customRange.end)}`;
    default: return '';
  }
}
function stepDate(scale, date, dir) {
  switch (scale) {
    case 'Year': return addYears(date, dir);
    case 'Month': return addMonths(date, dir);
    case 'Week': return addDays(date, 7 * dir);
    case 'Day': return addDays(date, dir);
    default: return date;
  }
}
function stepCustomRange(range, dir) {
  if (!range || !range.start || !range.end) return range;
  const lenDays = Math.round((range.end - range.start) / 86400000) + 1;
  return { start: addDays(range.start, dir * lenDays), end: addDays(range.end, dir * lenDays) };
}

const TIMELINE_START_HOUR = 6; // timeline spans 6 AM to 6 AM next day
function minutesFromTimelineStart(hhmm) {
  const [h, m] = hhmm.split(':').map(Number);
  let rel = h * 60 + m - TIMELINE_START_HOUR * 60;
  if (rel < 0) rel += 24 * 60;
  return rel;
}
function timelineStartToTimeStr(rel) {
  let total = (TIMELINE_START_HOUR * 60 + rel) % (24 * 60);
  if (total < 0) total += 24 * 60;
  const h = Math.floor(total / 60);
  const m = total % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

/* ------------------------------------------------------------------ */
/* Small shared hooks                                                   */
/* ------------------------------------------------------------------ */

function useOutsideClose(onClose) {
  const ref = useRef(null);
  useEffect(() => {
    function handlePointer(e) { if (ref.current && !ref.current.contains(e.target)) onClose(); }
    function handleKey(e) { if (e.key === 'Escape') onClose(); }
    document.addEventListener('mousedown', handlePointer);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handlePointer);
      document.removeEventListener('keydown', handleKey);
    };
  }, [onClose]);
  return ref;
}

function useElementWidth(fallback) {
  const ref = useRef(null);
  const [width, setWidth] = useState(fallback);
  useLayoutEffect(() => {
    if (!ref.current) return;
    const el = ref.current;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) setWidth(entry.contentRect.width);
    });
    ro.observe(el);
    setWidth(el.getBoundingClientRect().width || fallback);
    return () => ro.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return [ref, width];
}

/* ------------------------------------------------------------------ */
/* Timeline drag-resize bar (used by Template editor & Day view)       */
/* ------------------------------------------------------------------ */

function ScrollWheelColumn({ values, value, onChange, format }) {
  const viewportRef = useRef(null);
  const dragRef = useRef(null);
  const ROW_H = 28;

  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    const idx = values.indexOf(value);
    if (idx >= 0 && Math.abs(el.scrollTop - idx * ROW_H) > 1) el.scrollTop = idx * ROW_H;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  function commitFromScrollTop(scrollTop) {
    const idx = Math.round(scrollTop / ROW_H);
    const clamped = Math.max(0, Math.min(values.length - 1, idx));
    const v = values[clamped];
    if (v !== value) onChange(v);
    return clamped;
  }

  function handleScroll(e) {
    if (dragRef.current) return;
    commitFromScrollTop(e.target.scrollTop);
  }

  function handlePointerDown(e) {
    const el = viewportRef.current;
    if (!el) return;
    el.setPointerCapture(e.pointerId);
    dragRef.current = { startY: e.clientY, startScrollTop: el.scrollTop };
  }
  function handlePointerMove(e) {
    const d = dragRef.current;
    const el = viewportRef.current;
    if (!d || !el) return;
    el.scrollTop = d.startScrollTop - (e.clientY - d.startY);
    commitFromScrollTop(el.scrollTop);
  }
  function handlePointerUp(e) {
    const el = viewportRef.current;
    if (!dragRef.current || !el) return;
    dragRef.current = null;
    const idx = commitFromScrollTop(el.scrollTop);
    el.scrollTo({ top: idx * ROW_H, behavior: 'smooth' });
    try { el.releasePointerCapture(e.pointerId); } catch (err) { /* noop */ }
  }

  return (
    <div className="scroll-wheel-col">
      <div className="scroll-wheel-highlight" style={{ height: ROW_H }} />
      <div
        className="scroll-wheel-viewport" ref={viewportRef}
        onScroll={handleScroll}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        style={{ height: ROW_H * 3, paddingTop: ROW_H, paddingBottom: ROW_H }}
      >
        {values.map((v) => (
          <div key={v} className={`scroll-wheel-row ${v === value ? 'is-selected' : ''}`} style={{ height: ROW_H }}>
            {format ? format(v) : String(v).padStart(2, '0')}
          </div>
        ))}
      </div>
    </div>
  );
}

const HOUR_VALUES = Array.from({ length: 24 }, (_, i) => i);
const MINUTE_VALUES = Array.from({ length: 60 }, (_, i) => i);

function TimeStepScroller({ totalMinutes, onChange }) {
  const hours = Math.floor(totalMinutes / 60);
  const mins = totalMinutes % 60;
  return (
    <div className="time-scroller">
      <ScrollWheelColumn values={HOUR_VALUES} value={hours} onChange={(h) => onChange(Math.max(1, h * 60 + mins))} />
      <span className="time-scroller-unit">h</span>
      <span className="time-scroller-sep">:</span>
      <ScrollWheelColumn values={MINUTE_VALUES} value={mins} onChange={(m) => onChange(Math.max(1, hours * 60 + m))} />
      <span className="time-scroller-unit">m</span>
    </div>
  );
}

function ClockTimeScroller({ value, onChange }) {
  const [h, m] = value.split(':').map(Number);
  return (
    <div className="time-scroller">
      <ScrollWheelColumn values={HOUR_VALUES} value={h} onChange={(nh) => onChange(`${String(nh).padStart(2, '0')}:${String(m).padStart(2, '0')}`)} />
      <span className="time-scroller-sep">:</span>
      <ScrollWheelColumn values={MINUTE_VALUES} value={m} onChange={(nm) => onChange(`${String(h).padStart(2, '0')}:${String(nm).padStart(2, '0')}`)} />
    </div>
  );
}

function TimePickerField({ value, onChange, title }) {
  const [open, setOpen] = useState(false);
  const ref = useOutsideClose(() => setOpen(false));
  return (
    <div className="time-picker-field" ref={ref}>
      <button type="button" className="time-picker-trigger" onClick={() => setOpen((o) => !o)} title={title || 'Set time'}>
        <Clock size={11} /> {formatTime12h(value)}
      </button>
      {open && (
        <div className="time-scroller-popover">
          <ClockTimeScroller value={value} onChange={onChange} />
        </div>
      )}
    </div>
  );
}

function TimelineBar({ start, end, color, label, onChange, onRemove, onClick, trackWidth, removable, snapMin }) {
  const dragRef = useRef(null);
  const snap = snapMin || 15;

  const startRel = minutesFromTimelineStart(start);
  let endRel = minutesFromTimelineStart(end);
  if (endRel <= startRel) endRel += 24 * 60;
  const pxPerMin = trackWidth / (24 * 60);
  const left = startRel * pxPerMin;
  const width = Math.max((endRel - startRel) * pxPerMin, 8);

  function beginDrag(e, mode) {
    e.stopPropagation();
    e.preventDefault();
    const originX = e.clientX;
    const origStart = startRel;
    const origEnd = endRel;
    let moved = false;
    dragRef.current = { mode, originX, origStart, origEnd };

    function onMove(ev) {
      const d = dragRef.current;
      if (!d) return;
      const deltaMinRaw = (ev.clientX - d.originX) / pxPerMin;
      if (Math.abs(ev.clientX - d.originX) > 3) moved = true;
      const deltaMin = Math.round(deltaMinRaw / snap) * snap;
      let newStart = d.origStart;
      let newEnd = d.origEnd;
      if (d.mode === 'move') { newStart = d.origStart + deltaMin; newEnd = d.origEnd + deltaMin; }
      else if (d.mode === 'start') { newStart = Math.min(d.origStart + deltaMin, d.origEnd - snap); }
      else if (d.mode === 'end') { newEnd = Math.max(d.origEnd + deltaMin, d.origStart + snap); }
      const normStart = ((newStart % (24 * 60)) + 24 * 60) % (24 * 60);
      const normEndRaw = newEnd - newStart + normStart;
      onChange(timelineStartToTimeStr(normStart), timelineStartToTimeStr(normEndRaw));
    }
    function onUp() {
      dragRef.current = null;
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      if (!moved && mode === 'move' && onClick) onClick();
    }
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  }

  return (
    <div className={`timeline-bar tpl-${color}`} style={{ left, width }} onPointerDown={(e) => beginDrag(e, 'move')} title={`${formatTime12h(start)} – ${formatTime12h(end)} · click to edit, drag to move`}>
      <span className="timeline-handle timeline-handle-start" onPointerDown={(e) => beginDrag(e, 'start')} title="Drag to change start time" />
      <span className="timeline-bar-label">{label || `${formatTime12h(start)}–${formatTime12h(end)}`}</span>
      {removable && (
        <button type="button" className="timeline-bar-remove" title="Remove this range" onClick={(e) => { e.stopPropagation(); onRemove(); }}>
          <X size={10} />
        </button>
      )}
      <span className="timeline-handle timeline-handle-end" onPointerDown={(e) => beginDrag(e, 'end')} title="Drag to change end time" />
    </div>
  );
}

function formatTimeAbbrev(hhmm) {
  const [h, m] = hhmm.split(':').map(Number);
  const period = h >= 12 ? 'p' : 'a';
  let h12 = h % 12; if (h12 === 0) h12 = 12;
  return `${h12}:${String(m).padStart(2, '0')}${period}`;
}
function TimelineRuler({ trackWidth }) {
  const pxPerMin = trackWidth / (24 * 60);
  const marks = Array.from({ length: 25 }, (_, i) => i * 60);
  return (
    <div className="timeline-ruler" style={{ width: trackWidth }}>
      {marks.map((rel) => (
        <div key={rel} className="timeline-ruler-mark" style={{ left: rel * pxPerMin }}>
          <span className="timeline-ruler-label">{formatTimeAbbrev(timelineStartToTimeStr(rel))}</span>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Shift editor row + Template editor modal                            */
/* ------------------------------------------------------------------ */

function ShiftEditorRow({ shift, onChange, onDelete, onClose }) {
  function updateRange(idx, start, end) {
    const ranges = shift.ranges.map((r, i) => (i === idx ? { start, end } : r));
    onChange({ ...shift, ranges });
  }
  function addRange() {
    const last = shift.ranges[shift.ranges.length - 1];
    const startRel = minutesFromTimelineStart(last.end);
    const newEnd = timelineStartToTimeStr(startRel + 120);
    onChange({ ...shift, ranges: [...shift.ranges, { start: last.end, end: newEnd }] });
  }
  function removeRange(idx) {
    if (shift.ranges.length <= 1) return;
    onChange({ ...shift, ranges: shift.ranges.filter((_, i) => i !== idx) });
  }

  return (
    <div className="shift-editor-row">
      <div className="shift-editor-row-top">
        <button type="button" className="tpl-icon-btn tpl-icon-btn-danger" title="Delete this shift" onClick={onDelete}><Trash2 size={13} /></button>
      </div>

      <label className="shift-field-label shift-id-field">Shift Id
        <input className="quick-edit-input" value={shift.id} onChange={(e) => onChange({ ...shift, id: e.target.value })} title="Shift ID" />
      </label>

      <div className="shift-ranges-block">
        {shift.ranges.map((r, idx) => (
          <div key={idx} className="shift-range-row">
            <span className="shift-range-index">{idx + 1}</span>
            <TimePickerField value={r.start} onChange={(v) => updateRange(idx, v, r.end)} title="Start time" />
            <span className="shift-time-sep">–</span>
            <TimePickerField value={r.end} onChange={(v) => updateRange(idx, r.start, v)} title="End time" />
            <span className="shift-range-hrs" title="Duration">{fmtHrs(computeHours(r.start, r.end))} hrs</span>
            {shift.ranges.length > 1 && (
              <button type="button" className="tpl-icon-btn" title="Remove this time range" onClick={() => removeRange(idx)}><X size={13} /></button>
            )}
          </div>
        ))}
        <button type="button" className="shift-range-add" onClick={addRange} title="Add another time range (for a split shift)"><Plus size={13} /> Add range</button>
      </div>

      <label className="shift-field-label">Role
        <input className="quick-edit-input" value={shift.role} onChange={(e) => onChange({ ...shift, role: e.target.value })} placeholder="Role" title="Role for this shift" />
      </label>

      <div className="shift-field-label">Color
        <div className="shift-color-dots">
          {TEMPLATE_COLORS.map((c) => (
            <button key={c} type="button" className={`quick-color-dot tpl-${c} ${c === shift.color ? 'is-selected' : ''}`} onClick={() => onChange({ ...shift, color: c })} title={`Color: ${c}`} aria-label={c}>
              {c === shift.color && <Check size={11} strokeWidth={3} />}
            </button>
          ))}
        </div>
      </div>

      <label className="shift-field-label">Comments
        <input className="quick-edit-input" value={shift.comments} onChange={(e) => onChange({ ...shift, comments: e.target.value })} placeholder="e.g. Closing" title="Shift comments" />
      </label>

      <div className="shift-editor-row-footer">
        <button type="button" className="cta-btn shift-save-btn" onClick={onClose} title="Save and close">
          <Check size={14} /> Save
        </button>
      </div>
    </div>
  );
}



function TemplateEditor({ initial, departments, onSave, onCancel, onDelete, canEdit }) {
  const [name, setName] = useState(initial ? initial.name : '');
  const [department, setDepartment] = useState(initial ? initial.department : (departments[0] || ''));
  const [color, setColor] = useState(initial ? initial.color : 'blue');
  const [comments, setComments] = useState(initial && initial.comments ? initial.comments.join('\n') : '');
  const [shifts, setShifts] = useState(initial ? initial.shifts : []);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [editingShiftIdx, setEditingShiftIdx] = useState(null);

  function updateShift(idx, next) { setShifts((prev) => prev.map((s, i) => (i === idx ? next : s))); }
  function removeShift(idx) { setShifts((prev) => prev.filter((_, i) => i !== idx)); setEditingShiftIdx(null); }
  function addShift() {
    const newIdx = shifts.length;
    setShifts((prev) => [...prev, mkShift(String(prev.length + 1), '08:00', '16:00', 'Dealer', 'blue')]);
    setEditingShiftIdx(newIdx);
  }

  function handleSave() {
    if (!name.trim()) return;
    onSave({
      id: initial ? initial.id : `tpl-${Date.now()}`,
      name: name.trim(), department, color,
      comments: comments.split('\n').map((l) => l.trim()).filter(Boolean),
      shifts,
    });
  }

  return (
    <div className="template-full-view">
      <div className="template-full-topbar">
        <button type="button" className="template-full-back" onClick={onCancel} title="Back, discard changes">
          <ChevronLeft size={18} /> Back
        </button>
        <div className="template-full-topbar-title">{initial ? `Edit template — ${initial.name}` : 'New template'}</div>
        <div className="template-full-topbar-actions">
          {initial && onDelete && canEdit && (
            <button type="button" className="danger-btn-ghost" onClick={() => setConfirmDelete(true)} title="Delete this template">
              <Trash2 size={14} /> Delete template
            </button>
          )}
          <button type="button" className="modal-cancel-btn" onClick={onCancel} title="Cancel">Cancel</button>
          {canEdit && <button type="button" className="cta-btn" onClick={handleSave} title="Save template">Save template</button>}
        </div>
      </div>

      <div className="template-full-body">
        <fieldset disabled={!canEdit} className="template-editor-fieldset">
          <div className="template-full-fields">
            <label>Template name<input className="quick-edit-input" value={name} onChange={(e) => setName(e.target.value)} title="Template name" /></label>
            <label>Department
              <select className="quick-edit-input" value={department} onChange={(e) => setDepartment(e.target.value)} title="Department this template belongs to">
                {departments.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </label>
          </div>
          <div className="template-full-row2">
            <label className="form-row-full">Comments (one per line, shown on the calendar card)
              <textarea className="quick-edit-input template-comments-textarea" value={comments} onChange={(e) => setComments(e.target.value)} title="Template comments" rows={2} />
            </label>
            <label>Color
              <div className="color-swatch-row">
                {TEMPLATE_COLORS.map((c) => (
                  <button key={c} type="button" className={`color-swatch-lg tpl-${c} ${c === color ? 'is-selected' : ''}`} onClick={() => setColor(c)} title={`Use ${c}`} aria-label={c}>
                    {c === color && <Check size={16} strokeWidth={3} />}
                  </button>
                ))}
              </div>
            </label>
          </div>

          <div className="shift-editor-section-full">
            <div className="shift-editor-section-head">
              <h4>Shifts <span className="shift-editor-hint">— belong to this template only</span></h4>
            </div>
            <div className="shift-badge-row">
              {shifts.length === 0 && <div className="template-picker-empty">No shifts yet.</div>}
              {shifts.map((s, idx) => (
                <button
                  key={idx} type="button"
                  className={`shift-badge-icon tpl-${s.color} ${editingShiftIdx === idx ? 'is-active' : ''}`}
                  onClick={() => setEditingShiftIdx(editingShiftIdx === idx ? null : idx)}
                  title={`Edit shift ${s.id}`}
                >
                  {s.id}
                </button>
              ))}
              {canEdit && (
                <button type="button" className="shift-badge-icon shift-badge-add" onClick={addShift} title="Add a new shift">
                  <Plus size={16} />
                </button>
              )}
            </div>
            {editingShiftIdx !== null && shifts[editingShiftIdx] && (
              <ShiftEditorRow
                shift={shifts[editingShiftIdx]}
                onChange={(next) => updateShift(editingShiftIdx, next)}
                onDelete={() => removeShift(editingShiftIdx)}
                onClose={() => setEditingShiftIdx(null)}
              />
            )}
          </div>
        </fieldset>
      </div>

      {confirmDelete && (
        <ConfirmDialog
          title="Delete this template?"
          message={`This removes "${name || 'this template'}" and all ${shifts.length} of its shifts. Any day it's assigned to will lose it.`}
          confirmLabel="Delete template"
          onConfirm={() => onDelete(initial.id)}
          onCancel={() => setConfirmDelete(false)}
        />
      )}
    </div>
  );
}

function TemplatePickerPopover({ department, templates, current, onPick, onEdit, onRemove, onCreateNew, onClose, title }) {
  const ref = useOutsideClose(onClose);
  const options = templates.filter((t) => t.department === department);
  return (
    <div className="template-picker-popover" ref={ref}>
      {current && onEdit && (
        <>
          <button type="button" className="template-picker-option template-picker-edit-current" onClick={onEdit} title={`Edit ${current.name}`}>
            <Pencil size={13} />
            <span className="template-picker-name">Edit "{current.name}"</span>
          </button>
          {onRemove && (
            <button type="button" className="template-picker-option template-picker-remove-current" onClick={onRemove} title="Remove template from this day">
              <Trash2 size={13} />
              <span className="template-picker-name">Remove from this day</span>
            </button>
          )}
          <div className="template-picker-divider" />
        </>
      )}
      <div className="picker-popover-label">{title || `Choose a template — ${department}`}</div>
      <div className="template-picker-list">
        {options.length === 0 && <div className="template-picker-empty">No templates yet for {department}</div>}
        {options.map((t) => (
          <button key={t.id} type="button" className="template-picker-option" onClick={() => onPick(t.id)} title={`Assign ${t.name}`}>
            <span className={`template-picker-dot tpl-${t.color}`} />
            <span className="template-picker-name">{t.name}</span>
          </button>
        ))}
      </div>
      {onCreateNew && (
        <button type="button" className="template-picker-create" onClick={onCreateNew} title="Create a new template">
          <Plus size={14} /> Create new template
        </button>
      )}
    </div>
  );
}

function ShiftAssignPicker({ template, currentShiftId, onPick, onEditShift, onRemoveAssignment, onCreateNew, onClose }) {
  const ref = useOutsideClose(onClose);
  const currentShift = currentShiftId && template ? template.shifts.find((s) => s.id === currentShiftId) : null;
  if (!template) {
    return (
      <div className="template-picker-popover" ref={ref}>
        <div className="template-picker-empty">No template assigned to this date yet.</div>
      </div>
    );
  }
  return (
    <div className="template-picker-popover" ref={ref}>
      {currentShift && (
        <>
          <button type="button" className="template-picker-option template-picker-edit-current" onClick={() => onEditShift(currentShift.id)} title={`Edit shift ${currentShift.id}`}>
            <Pencil size={13} />
            <span className="template-picker-name">Edit shift "{currentShift.id}"</span>
          </button>
          <button type="button" className="template-picker-option template-picker-remove-current" onClick={onRemoveAssignment} title="Remove from this shift">
            <Trash2 size={13} />
            <span className="template-picker-name">Remove from this shift</span>
          </button>
          <div className="template-picker-divider" />
        </>
      )}
      <div className="picker-popover-label">{currentShift ? 'Replace with' : 'Assign to shift'} — {template.name}</div>
      <div className="template-picker-list">
        {template.shifts.length === 0 && <div className="template-picker-empty">No shifts in this template yet.</div>}
        {template.shifts.map((s) => (
          <button key={s.id} type="button" className="template-picker-option" onClick={() => onPick(s)} title={`Assign shift ${s.id}`}>
            <span className={`template-picker-dot tpl-${s.color}`} />
            <span className="template-picker-name">{s.id} · {s.role} · {formatTime12h(s.ranges[0].start)}–{formatTime12h(s.ranges[0].end)}</span>
          </button>
        ))}
      </div>
      {onCreateNew && (
        <button type="button" className="template-picker-create" onClick={onCreateNew} title="Create a new shift">
          <Plus size={14} /> Create new shift
        </button>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Confirm dialog (used before any delete)                             */
/* ------------------------------------------------------------------ */

function ConfirmDialog({ title, message, confirmLabel, onConfirm, onCancel }) {
  return (
    <div className="modal-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) onCancel(); }}>
      <div className="modal-panel confirm-dialog-panel">
        <div className="modal-header">
          <h3>{title}</h3>
          <button type="button" className="modal-close-btn" onClick={onCancel} title="Close"><X size={18} /></button>
        </div>
        <div className="modal-body"><p className="confirm-dialog-message">{message}</p></div>
        <div className="modal-footer">
          <button type="button" className="modal-cancel-btn" onClick={onCancel} title="Cancel">Cancel</button>
          <button type="button" className="danger-btn" onClick={onConfirm} title={confirmLabel}><Trash2 size={14} /> {confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Top bar controls                                                     */
/* ------------------------------------------------------------------ */

function DepartmentDropdown({ value, onChange, options }) {
  const [open, setOpen] = useState(false);
  const ref = useOutsideClose(() => setOpen(false));
  return (
    <div className="dept-dropdown" ref={ref}>
      <button type="button" className="dept-trigger" onClick={() => setOpen((o) => !o)} aria-haspopup="listbox" aria-expanded={open} title="Choose department">
        <span className="dept-trigger-text">{value}</span>
        <ChevronDown size={16} className={`dept-chevron ${open ? 'is-open' : ''}`} />
      </button>
      {open && (
        <div className="dept-menu" role="listbox">
          {options.map((dept) => (
            <button key={dept} type="button" role="option" aria-selected={dept === value} className={`dept-option ${dept === value ? 'is-selected' : ''}`} onClick={() => { onChange(dept); setOpen(false); }} title={`Switch to ${dept}`}>
              <span>{dept}</span>
              {dept === value && <Check size={14} />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function WeekStartDropdown({ value, onChange }) {
  const [open, setOpen] = useState(false);
  const ref = useOutsideClose(() => setOpen(false));
  return (
    <div className="dept-dropdown" ref={ref}>
      <button type="button" className="week-start-trigger" onClick={() => setOpen((o) => !o)} title="Choose which day the week starts on">
        <span>Week starts {WEEKDAY_FULL_BASE[value]}</span>
        <ChevronDown size={14} className={`dept-chevron ${open ? 'is-open' : ''}`} />
      </button>
      {open && (
        <div className="dept-menu">
          {WEEKDAY_FULL_BASE.map((l, v) => (
            <button key={v} type="button" className={`dept-option ${value === v ? 'is-selected' : ''}`} onClick={() => { onChange(v); setOpen(false); }} title={`Start weeks on ${l}`}>
              <span>{l}</span>
              {value === v && <Check size={14} />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function ScaleSelector({ value, onChange }) {
  const activeIndex = SCALES.indexOf(value);
  const fillPct = (activeIndex / (SCALES.length - 1)) * 80;
  return (
    <div className="scale-selector">
      <div className="scale-track" />
      <div className="scale-track-fill" style={{ width: `${fillPct}%` }} />
      {SCALES.map((scale) => (
        <button key={scale} type="button" className={`scale-point-wrap ${scale === value ? 'is-active' : ''}`} onClick={() => onChange(scale)} aria-pressed={scale === value} title={`Switch to ${scale} view`}>
          <span className="scale-point" />
          <span className="scale-label">{scale}</span>
        </button>
      ))}
    </div>
  );
}

function PeriodNav({ scale, date, customRange, onStep }) {
  return (
    <div className="period-nav">
      <button type="button" className="nav-arrow-btn" onClick={() => onStep(-1)} title="Previous period"><ChevronLeft size={16} /></button>
      <span className="period-label">{getPeriodLabel(scale, date, customRange)}</span>
      <button type="button" className="nav-arrow-btn" onClick={() => onStep(1)} title="Next period"><ChevronRight size={16} /></button>
    </div>
  );
}

function DatePickerPopover({ anchorDate, weekStartsOn, onSelect, onClose }) {
  const [viewDate, setViewDate] = useState(new Date(anchorDate.getFullYear(), anchorDate.getMonth(), 1));
  const ref = useOutsideClose(onClose);
  const weeks = useMemo(() => getMonthMatrix(viewDate.getFullYear(), viewDate.getMonth(), weekStartsOn), [viewDate, weekStartsOn]);
  const wdLabels = getWeekdayLabels(weekStartsOn, false);
  return (
    <div className="date-picker-popover" ref={ref}>
      <div className="picker-header">
        <button type="button" className="picker-nav-btn" onClick={() => setViewDate((d) => addMonths(d, -1))} title="Previous month"><ChevronLeft size={16} /></button>
        <span className="picker-title">{MONTH_LABELS[viewDate.getMonth()]} {viewDate.getFullYear()}</span>
        <button type="button" className="picker-nav-btn" onClick={() => setViewDate((d) => addMonths(d, 1))} title="Next month"><ChevronRight size={16} /></button>
      </div>
      <div className="picker-weekdays">{wdLabels.map((w) => <span key={w}>{w[0]}</span>)}</div>
      <div className="picker-grid">
        {weeks.flat().map(({ date, inMonth }) => {
          const isToday = isSameDay(date, TODAY);
          const isSelected = isSameDay(date, anchorDate);
          return (
            <button key={date.toISOString()} type="button" className={`picker-day ${!inMonth ? 'is-muted' : ''} ${isToday ? 'is-today' : ''} ${isSelected ? 'is-selected' : ''}`} onClick={() => onSelect(date)} title={formatShortDate(date)}>
              {date.getDate()}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function RangePickerPopover({ range, weekStartsOn, onSelectRange, onClose }) {
  const initial = (range && range.start) || TODAY;
  const [viewDate, setViewDate] = useState(new Date(initial.getFullYear(), initial.getMonth(), 1));
  const [draftStart, setDraftStart] = useState((range && range.start) || null);
  const [draftEnd, setDraftEnd] = useState((range && range.end) || null);
  const [hoverDate, setHoverDate] = useState(null);
  const ref = useOutsideClose(onClose);
  const weeks = useMemo(() => getMonthMatrix(viewDate.getFullYear(), viewDate.getMonth(), weekStartsOn), [viewDate, weekStartsOn]);
  const wdLabels = getWeekdayLabels(weekStartsOn, false);

  function handleDayClick(date) {
    if (!draftStart || draftEnd) { setDraftStart(date); setDraftEnd(null); }
    else {
      const start = date < draftStart ? date : draftStart;
      const end = date < draftStart ? draftStart : date;
      setDraftStart(start); setDraftEnd(end);
      onSelectRange({ start, end });
    }
  }
  const previewEnd = draftEnd || hoverDate;
  const lo = draftStart && previewEnd ? (draftStart < previewEnd ? draftStart : previewEnd) : draftStart;
  const hi = draftStart && previewEnd ? (draftStart < previewEnd ? previewEnd : draftStart) : null;

  return (
    <div className="date-picker-popover range-picker-popover" ref={ref}>
      <div className="picker-header">
        <button type="button" className="picker-nav-btn" onClick={() => setViewDate((d) => addMonths(d, -1))} title="Previous month"><ChevronLeft size={16} /></button>
        <span className="picker-title">{MONTH_LABELS[viewDate.getMonth()]} {viewDate.getFullYear()}</span>
        <button type="button" className="picker-nav-btn" onClick={() => setViewDate((d) => addMonths(d, 1))} title="Next month"><ChevronRight size={16} /></button>
      </div>
      <div className="picker-weekdays">{wdLabels.map((w) => <span key={w}>{w[0]}</span>)}</div>
      <div className="picker-grid" onMouseLeave={() => setHoverDate(null)}>
        {weeks.flat().map(({ date, inMonth }) => {
          const isToday = isSameDay(date, TODAY);
          const isEdge = (lo && isSameDay(date, lo)) || (hi && isSameDay(date, hi));
          const isInRange = lo && hi && date > lo && date < hi;
          return (
            <button key={date.toISOString()} type="button" className={`picker-day ${!inMonth ? 'is-muted' : ''} ${isToday ? 'is-today' : ''} ${isEdge ? 'is-selected' : ''} ${isInRange ? 'is-in-range' : ''}`} onClick={() => handleDayClick(date)} onMouseEnter={() => setHoverDate(date)} title={formatShortDate(date)}>
              {date.getDate()}
            </button>
          );
        })}
      </div>
      <div className="picker-hint">{!draftStart ? 'Pick a start date' : !draftEnd ? 'Pick an end date' : `${formatShortDate(draftStart)} – ${formatShortDate(draftEnd)}`}</div>
    </div>
  );
}

function DateBox({ scale, anchorDate, weekStartsOn, onSelect, customRange, onSelectRange }) {
  const [open, setOpen] = useState(false);
  const isCustom = scale === 'Custom';
  const label = isCustom && customRange && customRange.start && customRange.end
    ? `${formatShortDate(customRange.start)} – ${formatShortDate(customRange.end)}`
    : formatShortDate(anchorDate);
  return (
    <div className="date-box-wrap">
      <button type="button" className="date-box" onClick={() => setOpen((o) => !o)} title={isCustom ? 'Pick a date range' : 'Pick a date'}>
        <CalendarDays size={15} />
        <span>{label}</span>
      </button>
      {open && (isCustom ? (
        <RangePickerPopover range={customRange} weekStartsOn={weekStartsOn} onSelectRange={(r) => { onSelectRange(r); setOpen(false); }} onClose={() => setOpen(false)} />
      ) : (
        <DatePickerPopover anchorDate={anchorDate} weekStartsOn={weekStartsOn} onSelect={(d) => { onSelect(d); setOpen(false); }} onClose={() => setOpen(false)} />
      ))}
    </div>
  );
}

function TopBar({ section, department, onDepartment, departments, scale, onScale, anchorDate, onStep, onDateSelect, customRange, onSelectRange, weekStartsOn, onWeekStartsOn, onPublish }) {
  if (section !== 'schedule') {
    const titleMap = { templates: 'Templates', team: 'Team', settings: 'Settings', print: 'Print Center', dashboard: 'Dashboard', reports: 'Report Center', offtracker: 'Off Tracker', notifications: 'Notifications', about: 'About', help: 'Guide' };
    return (
      <header className="top-bar top-bar-simple">
        <span className="top-bar-title">{titleMap[section] || 'Rosta Studio'}</span>
      </header>
    );
  }
  const showWeekStart = scale === 'Month' || scale === 'Week';
  return (
    <header className="top-bar">
      <div className="top-bar-left">
        <DepartmentDropdown value={department} onChange={onDepartment} options={departments} />
      </div>
      <div className="top-bar-center">
        <ScaleSelector value={scale} onChange={onScale} />
        <PeriodNav scale={scale} date={anchorDate} customRange={customRange} onStep={onStep} />
        <DateBox scale={scale} anchorDate={anchorDate} weekStartsOn={weekStartsOn} onSelect={onDateSelect} customRange={customRange} onSelectRange={onSelectRange} />
        {showWeekStart && <WeekStartDropdown value={weekStartsOn} onChange={onWeekStartsOn} />}
      </div>
      <div className="top-bar-right">
        <button type="button" className="publish-btn" onClick={onPublish} title="Publish the current schedule">Publish</button>
      </div>
    </header>
  );
}

/* ------------------------------------------------------------------ */
/* Sidebar + profile / workspace switcher                              */
/* ------------------------------------------------------------------ */

function ProfileMenu({ expanded, workspace, onWorkspace, role, onRole }) {
  const [open, setOpen] = useState(false);
  const ref = useOutsideClose(() => setOpen(false));
  return (
    <div className="profile-menu-wrap" ref={ref}>
      <button type="button" className="profile-trigger" onClick={() => setOpen((o) => !o)} title="Workspace and account">
        <span className="profile-avatar"><User size={16} /></span>
        <span className="profile-info">
          <span className="profile-workspace">{workspace}</span>
          <span className="profile-email">{role}</span>
        </span>
      </button>
      {open && (
        <div className="profile-popover">
          <div className="profile-popover-label">Workspaces</div>
          {WORKSPACES.map((ws) => (
            <button key={ws} type="button" className={`profile-ws-option ${ws === workspace ? 'is-selected' : ''}`} onClick={() => { onWorkspace(ws); setOpen(false); }} title={`Switch to ${ws}`}>
              <span>{ws}</span>
              {ws === workspace && <Check size={13} />}
            </button>
          ))}
          <div className="profile-popover-divider" />
          <div className="profile-popover-label">Viewing as</div>
          {USER_ROLES.map((r) => (
            <button key={r} type="button" className={`profile-ws-option ${r === role ? 'is-selected' : ''}`} onClick={() => { onRole(r); setOpen(false); }} title={`View as ${r}`}>
              <span>{r}</span>
              {r === role && <Check size={13} />}
            </button>
          ))}
          <div className="profile-popover-divider" />
          <button type="button" className="profile-login-btn" title="Log in with a different account">Log in / switch account</button>
        </div>
      )}
    </div>
  );
}

function Sidebar({ expanded, onToggle, activeItem, onSelectItem, workspace, onWorkspace, role, onRole }) {
  return (
    <aside className={`sidebar ${expanded ? 'is-expanded' : ''}`}>
      <div className="sidebar-top">
        <button type="button" className="sidebar-toggle" onClick={onToggle} title={expanded ? 'Collapse sidebar' : 'Expand sidebar'}>
          <Menu size={20} />
        </button>
      </div>
      <nav className="sidebar-nav" aria-label="Main navigation">
        {NAV_ITEMS_MAIN.map((item) => {
          const Icon = item.icon;
          const isActive = item.key === activeItem;
          return (
            <button key={item.key} type="button" className={`sidebar-item ${isActive ? 'is-active' : ''}`} onClick={() => onSelectItem(item.key)} title={item.label}>
              <span className="sidebar-item-icon"><Icon size={20} /></span>
              <span className="sidebar-item-label">{item.label}</span>
            </button>
          );
        })}
      </nav>
      <div className="sidebar-bottom-group">
        <nav className="sidebar-nav" aria-label="Secondary navigation">
          {NAV_ITEMS_BOTTOM.map((item) => {
            const Icon = item.icon;
            const isActive = item.key === activeItem;
            return (
              <button key={item.key} type="button" className={`sidebar-item ${isActive ? 'is-active' : ''}`} onClick={() => onSelectItem(item.key)} title={item.label}>
                <span className="sidebar-item-icon"><Icon size={20} /></span>
                <span className="sidebar-item-label">{item.label}</span>
              </button>
            );
          })}
        </nav>
        <div className="sidebar-profile-wrap">
          <ProfileMenu expanded={expanded} workspace={workspace} onWorkspace={onWorkspace} role={role} onRole={onRole} />
        </div>
      </div>
    </aside>
  );
}

/* ------------------------------------------------------------------ */
/* Month view — day cell with template assignment                     */
/* ------------------------------------------------------------------ */

function DayCell({ date, inMonth, isToday, dateKey, department, assignedTemplate, templates, cellHandlers, onDrillDown, canEdit }) {
  const { pickerKey, openPicker, closePicker, assignTemplate, unassignTemplate, openTemplateEditorForNew, openTemplateEditorForEdit, dropAssignment } = cellHandlers;
  const [isDragOver, setIsDragOver] = useState(false);
  const myPickerKey = `assign:${dateKey}:${department}`;
  const isPickerOpen = pickerKey === myPickerKey;

  return (
    <div
      className={`day-cell ${!inMonth ? 'is-muted' : ''} ${isDragOver ? 'is-drag-over' : ''} ${isPickerOpen ? 'is-editing' : ''}`}
      onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = e.ctrlKey ? 'copy' : 'move'; }}
      onDragEnter={(e) => { e.preventDefault(); setIsDragOver(true); }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={(e) => {
        e.preventDefault(); setIsDragOver(false);
        const fromKey = e.dataTransfer.getData('text/plain');
        if (fromKey) dropAssignment(fromKey, dateKey, department, e.ctrlKey);
      }}
    >
      <div className="day-cell-header">
        <button type="button" className={`day-number ${isToday ? 'is-today' : ''}`} onClick={() => onDrillDown('Day', date)} title={`Open ${formatShortDate(date)}`}>
          {date.getDate()}
        </button>
      </div>

      {assignedTemplate && !isPickerOpen && (
        <div
          className={`template-chip tpl-${assignedTemplate.color}`}
          draggable={canEdit}
          onDragStart={(e) => { e.dataTransfer.setData('text/plain', `${dateKey}__${department}`); e.dataTransfer.effectAllowed = 'copyMove'; }}
          title="Drag to move · hold Ctrl to copy"
        >
          <div className="template-card-header">
            <span className="template-dot" />
            <span className="template-card-title">{assignedTemplate.name}</span>
          </div>
          {assignedTemplate.comments && assignedTemplate.comments.length > 0 && (
            <div className="template-card-line" title={assignedTemplate.comments.join(' · ')}>{assignedTemplate.comments[0]}</div>
          )}
          {canEdit && (
            <span className="template-actions template-actions-bottom">
              <button type="button" className="tpl-icon-btn" title="Edit or change template" onClick={() => openPicker(myPickerKey)}><Pencil size={12} /></button>
              <button type="button" className="tpl-icon-btn tpl-icon-btn-danger" title="Remove from this day" onClick={() => unassignTemplate(dateKey, department)}><Trash2 size={12} /></button>
              <span className="tpl-icon-btn tpl-drag" aria-hidden="true" title="Drag to move, Ctrl+drag to copy"><GripVertical size={12} /></span>
            </span>
          )}
        </div>
      )}

      {!assignedTemplate && !isPickerOpen && canEdit && (
        <button type="button" className="day-add-btn-subtle" onClick={() => openPicker(myPickerKey)} title="Assign a template to this day">
          <span className="day-add-btn-subtle-inner"><Plus size={16} /></span>
        </button>
      )}

      {isPickerOpen && (
        <TemplatePickerPopover
          department={department}
          templates={templates}
          current={assignedTemplate}
          onEdit={assignedTemplate ? () => openTemplateEditorForEdit(assignedTemplate) : undefined}
          onPick={(tplId) => { assignTemplate(dateKey, department, tplId); closePicker(); }}
          onCreateNew={() => openTemplateEditorForNew(department, dateKey)}
          onClose={closePicker}
        />
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Month & Year views                                                   */
/* ------------------------------------------------------------------ */

function MonthGrid({ anchorDate, department, templates, assignments, weekStartsOn, cellHandlers, onDrillDown, canEdit }) {
  const weeks = useMemo(() => getMonthMatrix(anchorDate.getFullYear(), anchorDate.getMonth(), weekStartsOn), [anchorDate, weekStartsOn]);
  const wdLabels = getWeekdayLabels(weekStartsOn, false);
  return (
    <div className="month-grid-wrap">
      <div className="weekday-row"><span className="weekday-label-spacer" />{wdLabels.map((w) => <div key={w} className="weekday-label">{w}</div>)}</div>
      <div className="month-grid">
        {weeks.map((week, wIndex) => (
          <React.Fragment key={wIndex}>
            <button type="button" className="month-week-num" onClick={() => onDrillDown('Week', week[0].date)} title={`Open week ${getWeekNumber(week[0].date)}`}>
              {getWeekNumber(week[0].date)}
            </button>
            {week.map(({ date, inMonth }) => {
              const dateKey = toKey(date);
              const tplId = assignments[`${dateKey}__${department}`];
              const assignedTemplate = tplId ? templates.find((t) => t.id === tplId) : null;
              return (
                <DayCell
                  key={dateKey} date={date} inMonth={inMonth} isToday={isSameDay(date, TODAY)}
                  dateKey={dateKey} department={department} assignedTemplate={assignedTemplate} templates={templates}
                  cellHandlers={cellHandlers} onDrillDown={onDrillDown} canEdit={canEdit}
                />
              );
            })}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

function MiniMonth({ year, month, department, assignments, templates, weekStartsOn, onDrillDown }) {
  const weeks = useMemo(() => getMonthMatrix(year, month, weekStartsOn), [year, month, weekStartsOn]);
  const wdLabels = getWeekdayLabels(weekStartsOn, false);
  return (
    <div className="mini-month">
      <div className="mini-month-header">
        <button type="button" className="mini-month-title-btn" onClick={() => onDrillDown('Month', new Date(year, month, 1))} title={`Open ${MONTH_LABELS[month]} ${year}`}>
          {MONTH_LABELS[month]}
        </button>
      </div>
      <div className="mini-weekday-row"><span />{wdLabels.map((w) => <span key={w}>{w[0]}</span>)}</div>
      <div className="mini-grid">
        {weeks.map((week, wIndex) => (
          <React.Fragment key={wIndex}>
            <button type="button" className="mini-week-num" onClick={() => onDrillDown('Week', week[0].date)} title={`Open week ${getWeekNumber(week[0].date)}`}>
              {getWeekNumber(week[0].date)}
            </button>
            {week.map(({ date, inMonth }) => {
              const dateKey = toKey(date);
              const tplId = assignments[`${dateKey}__${department}`];
              const tpl = inMonth && tplId ? templates.find((t) => t.id === tplId) : null;
              const isToday = isSameDay(date, TODAY);
              return (
                <button key={date.toISOString()} type="button" className={`mini-day ${!inMonth ? 'is-muted' : ''} ${isToday ? 'is-today' : ''}`} onClick={() => onDrillDown('Day', date)} disabled={!inMonth} title={formatShortDate(date)}>
                  <span className="mini-day-num">{date.getDate()}</span>
                  {tpl && <span className="mini-day-bar" style={{ background: `var(--tpl-${tpl.color}-dot)` }} />}
                </button>
              );
            })}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

function YearGrid({ anchorDate, department, assignments, templates, weekStartsOn, onDrillDown }) {
  const year = anchorDate.getFullYear();
  return (
    <div className="year-grid">
      {MONTH_LABELS.map((_, i) => (
        <MiniMonth key={i} year={year} month={i} department={department} assignments={assignments} templates={templates} weekStartsOn={weekStartsOn} onDrillDown={onDrillDown} />
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Roster grid — Week & Custom (matches the reference: template header  */
/* per day, shift code + working hours + Hrs per person, Total Hrs)     */
/* ------------------------------------------------------------------ */

function RosterGrid({ days, department, departments, staff, templates, assignments, roster, hiddenStaffIds, extraStaffIds, handlers, canEdit }) {
  const hiddenSet = (hiddenStaffIds && hiddenStaffIds[department]) || new Set();
  const extraSet = (extraStaffIds && extraStaffIds[department]) || new Set();
  const deptStaff = staff.filter((s) => !s.archived && ((s.department === department && !hiddenSet.has(s.id)) || extraSet.has(s.id)));
  const visibleIds = new Set(deptStaff.map((s) => s.id));
  const NAME_COL = 106;
  const ID_COL = 64;
  const REMOVE_COL = 26;
  const SCHED_COL = 132;
  const SHIFT_COL = 52;
  const HRS_COL = 46;
  const addCrewKey = `addcrew:${department}`;

  function totalHrsFor(name) {
    let total = 0;
    days.forEach((d) => {
      const entry = roster[rk(name, toKey(d))];
      if (entry) total += computeEntryHours(entry);
    });
    return Math.round(total * 10) / 10;
  }

  return (
    <div className="roster-wrap">
      <div className="roster-scroll">
        <div
          className="roster-grid"
          style={{
            gridTemplateColumns: `${NAME_COL}px ${NAME_COL}px ${ID_COL}px ${REMOVE_COL}px repeat(${days.length}, ${SCHED_COL}px ${SHIFT_COL}px ${HRS_COL}px) 72px`,
            gridTemplateRows: `70px 30px repeat(${deptStaff.length}, 46px) 38px`,
          }}
        >
          <div className="roster-name-header" style={{ gridRow: '1 / 3', left: 0, width: NAME_COL }}>Last Name</div>
          <div className="roster-name-header" style={{ gridRow: '1 / 3', left: NAME_COL, width: NAME_COL }}>First Name</div>
          <div className="roster-name-header roster-id-header" style={{ gridRow: '1 / 3', left: NAME_COL * 2, width: ID_COL }}>id#</div>
          <div className="roster-name-header" style={{ gridRow: '1 / 3', left: NAME_COL * 2 + ID_COL, width: REMOVE_COL }} />

          {days.map((d) => {
            const dateKey = toKey(d);
            const tplId = assignments[`${dateKey}__${department}`];
            const tpl = tplId ? templates.find((t) => t.id === tplId) : null;
            const dayPickerKey = `assign:${dateKey}:${department}`;
            return (
              <div key={`${dateKey}-info`} className={`roster-day-info ${isSameDay(d, TODAY) ? 'is-today' : ''}`} style={{ gridColumn: 'span 3' }}>
                <div className="roster-day-date">{WEEKDAY_BASE[d.getDay()]}, {MONTH_LABELS[d.getMonth()].slice(0, 3)} {d.getDate()}</div>
                {tpl ? (
                  <>
                    <div className="roster-day-tplname">
                      <span className="template-dot" style={{ background: `var(--tpl-${tpl.color}-dot)` }} />
                      {tpl.name}
                      {canEdit && (
                        <span className="roster-day-tpl-actions">
                          <button type="button" className="roster-day-edit-btn" onClick={() => handlers.openPicker(dayPickerKey)} title="Edit or change this template"><Pencil size={10} /></button>
                          <button type="button" className="roster-day-edit-btn roster-day-remove-btn" onClick={() => handlers.unassignTemplate(dateKey, department)} title="Remove template from this day"><Trash2 size={10} /></button>
                        </span>
                      )}
                    </div>
                    {tpl.comments && tpl.comments.length > 0 && <div className="roster-day-tplcomments" title={tpl.comments.join(' · ')}>{tpl.comments.join(' · ')}</div>}
                  </>
                ) : canEdit ? (
                  <button type="button" className="roster-day-assign-btn" onClick={() => handlers.openPicker(dayPickerKey)} title="Assign a template to this day"><Plus size={12} /> Assign template</button>
                ) : (
                  <div className="roster-day-tplname is-empty">No template</div>
                )}
                {handlers.pickerKey === dayPickerKey && (
                  <TemplatePickerPopover
                    department={department} templates={templates} current={tpl}
                    onEdit={tpl ? () => handlers.openTemplateEditorForEdit(tpl) : undefined}
                    onRemove={tpl ? () => { handlers.unassignTemplate(dateKey, department); handlers.closePicker(); } : undefined}
                    onPick={(id) => { handlers.assignTemplate(dateKey, department, id); handlers.closePicker(); }}
                    onCreateNew={() => handlers.openTemplateEditorForNew(department, dateKey)}
                    onClose={handlers.closePicker}
                  />
                )}
              </div>
            );
          })}
          <div className="roster-total-header" style={{ gridRow: '1 / 3' }} title="Total hours across this period">Total<br />Hrs</div>

          {days.map((d) => (
            <div key={`${toKey(d)}-sub`} className="roster-subcol-group" style={{ gridColumn: 'span 3', gridTemplateColumns: `${SCHED_COL}px ${SHIFT_COL}px ${HRS_COL}px` }}>
              <span title="Working hours">Schedule</span>
              <span title="Shift code">Shift</span>
              <span title="Hours worked">Hrs</span>
            </div>
          ))}

          {deptStaff.length === 0 && (
            <div className="roster-empty-row" style={{ gridColumn: `1 / -1` }}>No {department} staff shown — use + below to add crew.</div>
          )}
          {deptStaff.map((person) => (
            <React.Fragment key={person.id}>
              <div className="roster-name-cell" style={{ left: 0, width: NAME_COL }} title={person.lastName}>{person.lastName}</div>
              <div className="roster-name-cell" style={{ left: NAME_COL, width: NAME_COL }} title={person.firstName}>{person.firstName}</div>
              <div className="roster-name-cell roster-id-cell" style={{ left: NAME_COL * 2, width: ID_COL }} title={person.id}>{person.id}</div>
              <div className="roster-name-cell roster-remove-cell" style={{ left: NAME_COL * 2 + ID_COL, width: REMOVE_COL }}>
                {canEdit && (
                  <button type="button" className="roster-minus-btn" onClick={() => handlers.hideStaffFromView(department, person.id)} title={`Remove ${person.name} from this view`}>−</button>
                )}
              </div>
              {days.map((d) => {
                const dateKey = toKey(d);
                const entry = roster[rk(person.name, dateKey)];
                const tplId = assignments[`${dateKey}__${department}`];
                const tpl = tplId ? templates.find((t) => t.id === tplId) : null;
                const shiftDef = entry && tpl ? tpl.shifts.find((s) => s.id === entry.shiftId) : null;
                const cellKey = `roster:${person.name}:${dateKey}`;
                const isPickerOpen = handlers.pickerKey === cellKey;
                return (
                  <React.Fragment key={dateKey}>
                    <div className="roster-schedule-cell">
                      {entry && entry.ranges.map((r, i) => (
                        <span key={i} title="Working hours">{formatTime12h(r.start)} – {formatTime12h(r.end)}</span>
                      ))}
                    </div>
                    <div className={`roster-shift-cell ${isPickerOpen ? 'is-editing' : ''}`}>
                      {entry ? (
                        canEdit ? (
                          <button type="button" className={`roster-shift-badge tpl-${shiftDef ? shiftDef.color : 'blue'}`} onClick={() => handlers.openPicker(cellKey)} title={`Shift ${entry.shiftId} — click to edit, replace, or remove`}>{entry.shiftId}</button>
                        ) : (
                          <span className={`roster-shift-badge tpl-${shiftDef ? shiftDef.color : 'blue'}`} title={`Shift ${entry.shiftId}`}>{entry.shiftId}</span>
                        )
                      ) : tpl && canEdit ? (
                        <button type="button" className="roster-shift-badge roster-shift-badge-empty" onClick={() => handlers.openPicker(cellKey)} title={`Assign ${person.firstName} a shift`}><Plus size={14} /></button>
                      ) : null}
                      {isPickerOpen && (
                        <ShiftAssignPicker
                          template={tpl} currentShiftId={entry ? entry.shiftId : null}
                          onPick={(shift) => { handlers.assignShift(person.name, dateKey, shift); handlers.closePicker(); }}
                          onEditShift={(shiftId) => handlers.openPicker(`dayshift:${tpl.id}:${shiftId}`)}
                          onRemoveAssignment={() => handlers.unassignShift(person.name, dateKey)}
                          onCreateNew={tpl ? () => handlers.createShiftAndAssign(tpl.id, person.name, dateKey) : undefined}
                          onClose={handlers.closePicker}
                        />
                      )}
                      {handlers.pickerKey === `dayshift:${tpl ? tpl.id : ''}:${entry ? entry.shiftId : ''}` && tpl && entry && (
                        <div className="shift-edit-popover">
                          <ShiftEditorRow
                            shift={tpl.shifts.find((s) => s.id === entry.shiftId)}
                            onChange={(next) => handlers.updateTemplateShift(tpl.id, entry.shiftId, next)}
                            onDelete={() => handlers.removeTemplateShift(tpl.id, entry.shiftId)}
                            onClose={handlers.closePicker}
                          />
                        </div>
                      )}
                    </div>
                    <div className="roster-hrs-cell">{entry && fmtHrs(computeEntryHours(entry))}</div>
                  </React.Fragment>
                );
              })}
              <div className="roster-total-cell">{fmtHrs(totalHrsFor(person.name))}</div>
            </React.Fragment>
          ))}

          <div className="roster-name-cell roster-add-crew-cell" style={{ left: 0, width: NAME_COL * 2 + ID_COL + REMOVE_COL, gridColumn: 'span 4' }}>
            {canEdit && (
              <button type="button" className="roster-plus-btn" onClick={() => handlers.openPicker(addCrewKey)} title="Add crew to this view"><Plus size={13} /> Add crew</button>
            )}
            {handlers.pickerKey === addCrewKey && (
              <AddCrewPicker departments={departments} defaultDepartment={department} allStaff={staff} visibleIds={visibleIds} onPick={(s) => handlers.addStaffToView(department, s.id)} onClose={handlers.closePicker} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}


function WeekView({ anchorDate, weekStartsOn, department, departments, staff, templates, assignments, roster, hiddenStaffIds, extraStaffIds, handlers, canEdit }) {
  const start = startOfWeek(anchorDate, weekStartsOn);
  const days = Array.from({ length: 7 }, (_, i) => addDays(start, i));
  return <RosterGrid days={days} department={department} departments={departments} staff={staff} templates={templates} assignments={assignments} roster={roster} hiddenStaffIds={hiddenStaffIds} extraStaffIds={extraStaffIds} handlers={handlers} canEdit={canEdit} />;
}

function CustomRosterView({ customRange, department, departments, staff, templates, assignments, roster, hiddenStaffIds, extraStaffIds, handlers, canEdit }) {
  if (!customRange || !customRange.start || !customRange.end) {
    return (
      <div className="custom-view">
        <div className="custom-view-card">
          <CalendarDays size={28} />
          <h3>Pick a custom range</h3>
          <p>Use the date box above to choose a start and end date.</p>
        </div>
      </div>
    );
  }
  const MAX_DAYS = 62;
  const days = [];
  let cur = new Date(customRange.start);
  while (cur <= customRange.end && days.length < MAX_DAYS) { days.push(new Date(cur)); cur = addDays(cur, 1); }
  const truncated = cur <= customRange.end;
  return (
    <>
      {truncated && (
        <div className="range-truncated-notice" role="status">
          <Info size={13} />
          Showing the first {MAX_DAYS} days of your range. Narrow the dates to see the rest.
        </div>
      )}
      <RosterGrid days={days} department={department} departments={departments} staff={staff} templates={templates} assignments={assignments} roster={roster} hiddenStaffIds={hiddenStaffIds} extraStaffIds={extraStaffIds} handlers={handlers} canEdit={canEdit} />
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Day view — shifts as timeline rows, who is assigned, drag to adjust  */
/* ------------------------------------------------------------------ */

function barGeometry(start, end, trackWidth) {
  const startRel = minutesFromTimelineStart(start);
  let endRel = minutesFromTimelineStart(end);
  if (endRel <= startRel) endRel += 24 * 60;
  const pxPerMin = trackWidth / (24 * 60);
  return { left: startRel * pxPerMin, width: Math.max((endRel - startRel) * pxPerMin, 8) };
}

function StaffPickerPopover({ staff, onPick, onClose }) {
  const ref = useOutsideClose(onClose);
  return (
    <div className="template-picker-popover" ref={ref}>
      <div className="picker-popover-label">Assign a person</div>
      <div className="template-picker-list">
        {staff.length === 0 && <div className="template-picker-empty">No staff in this department yet.</div>}
        {staff.map((p) => (
          <button key={p.id} type="button" className="template-picker-option" onClick={() => onPick(p)} title={`Assign ${p.name}`}>
            <span className="template-picker-name">{p.name} · {p.position}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function AddCrewPicker({ departments, defaultDepartment, allStaff, visibleIds, onPick, onClose }) {
  const [dept, setDept] = useState(defaultDepartment);
  const ref = useOutsideClose(onClose);
  const options = allStaff.filter((s) => s.department === dept && !s.archived && !visibleIds.has(s.id));
  return (
    <div className="template-picker-popover" ref={ref}>
      <label className="add-crew-dept-field">Department
        <select className="quick-edit-input" value={dept} onChange={(e) => setDept(e.target.value)} title="Pick a department to add crew from">
          {departments.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
      </label>
      <div className="picker-popover-label">Add to this view</div>
      <div className="template-picker-list">
        {options.length === 0 && <div className="template-picker-empty">Everyone from {dept} is already shown.</div>}
        {options.map((s) => (
          <button key={s.id} type="button" className="template-picker-option" onClick={() => onPick(s)} title={`Add ${s.name}`}>
            <span className="template-picker-name">{s.name} · {s.position}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function ShiftBrowsePicker({ shifts, currentShiftId, onEdit, onDelete, onCreateNew, onClose }) {
  const ref = useOutsideClose(onClose);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const current = shifts.find((s) => s.id === currentShiftId);
  const others = shifts.filter((s) => s.id !== currentShiftId);
  return (
    <div className="template-picker-popover" ref={ref}>
      {current && (
        <>
          <button type="button" className="template-picker-option template-picker-edit-current" onClick={() => onEdit(current.id)} title={`Edit shift ${current.id}`}>
            <Pencil size={13} />
            <span className="template-picker-name">Edit "{current.id}"</span>
          </button>
          {confirmingDelete ? (
            <div className="picker-confirm">
              <p className="picker-confirm-text">Delete shift "{current.id}" from this template? It will be removed from every day using it.</p>
              <div className="picker-confirm-actions">
                <button type="button" className="picker-confirm-cancel" onClick={() => setConfirmingDelete(false)}>Cancel</button>
                <button type="button" className="picker-confirm-delete" onClick={() => onDelete(current.id)}>Delete shift</button>
              </div>
            </div>
          ) : (
            <button type="button" className="template-picker-option template-picker-remove-current" onClick={() => setConfirmingDelete(true)} title="Delete this shift">
              <Trash2 size={13} />
              <span className="template-picker-name">Delete this shift</span>
            </button>
          )}
          <div className="template-picker-divider" />
        </>
      )}
      <div className="picker-popover-label">Other shifts in this template</div>
      <div className="template-picker-list">
        {others.length === 0 && <div className="template-picker-empty">No other shifts yet.</div>}
        {others.map((s) => (
          <button key={s.id} type="button" className="template-picker-option" onClick={() => onEdit(s.id)} title={`Edit shift ${s.id}`}>
            <span className={`template-picker-dot tpl-${s.color}`} />
            <span className="template-picker-name">{s.id} · {s.role}</span>
          </button>
        ))}
      </div>
      <button type="button" className="template-picker-create" onClick={onCreateNew} title="Create a new shift">
        <Plus size={14} /> Create new shift
      </button>
    </div>
  );
}

function DayViewHeader({ anchorDate }) {
  return (
    <div className="day-view-header">
      <span className={`day-number large ${isSameDay(anchorDate, TODAY) ? 'is-today' : ''}`}>{anchorDate.getDate()}</span>
      <div>
        <div className="day-view-weekday">{WEEKDAY_FULL_BASE[anchorDate.getDay()]}</div>
        <div className="day-view-month">{MONTH_LABELS[anchorDate.getMonth()]} {anchorDate.getFullYear()}</div>
      </div>
    </div>
  );
}

/* Grid mode for Day view — an Excel-like sheet where each cell is one
   position/time slot. Supervisors can type a position code directly or pick
   one from the predefined list configured in Settings. */
function DayGridView({ tpl, rows, dateKey, handlers, canEdit }) {
  const SLOT_MIN = 60;
  const window0 = useMemo(() => {
    let min = Infinity, max = -Infinity;
    tpl.shifts.forEach((s) => s.ranges.forEach((r) => {
      const a = minutesFromTimelineStart(r.start);
      let b = minutesFromTimelineStart(r.end);
      if (b <= a) b += 24 * 60;
      if (a < min) min = a;
      if (b > max) max = b;
    }));
    return min === Infinity ? { min: 0, max: 24 * 60 } : { min, max };
  }, [tpl]);

  const slots = [];
  for (let t = Math.floor(window0.min / SLOT_MIN) * SLOT_MIN; t < window0.max; t += SLOT_MIN) slots.push(t);

  function isWorking(row, slotStart) {
    const ranges = row.entry ? row.entry.ranges : row.shift.ranges;
    return ranges.some((r) => {
      const a = minutesFromTimelineStart(r.start);
      let b = minutesFromTimelineStart(r.end);
      if (b <= a) b += 24 * 60;
      return slotStart >= a && slotStart < b;
    });
  }

  return (
    <div className="day-view-gantt-wrap">
      <div className="day-view-gantt-scroll">
        <table className="day-grid-table">
          <thead>
            <tr>
              <th className="day-grid-sticky day-grid-th-shift">Shift</th>
              <th className="day-grid-sticky day-grid-th-name">Employee</th>
              {slots.map((t) => (
                <th key={t} className="day-grid-slot-head">{formatTimeAbbrev(timelineStartToTimeStr(t % (24 * 60)))}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr><td colSpan={slots.length + 2} className="day-grid-empty">This template has no shifts yet.</td></tr>
            )}
            {rows.map((row, idx) => (
              <tr key={idx}>
                <td className="day-grid-sticky day-grid-td-shift">
                  <span className={`roster-shift-badge tpl-${row.shift.color}`} title={`Shift ${row.shift.id} · ${row.shift.role}`}>{row.shift.id}</span>
                </td>
                <td className="day-grid-sticky day-grid-td-name">
                  {row.person ? row.person.name : <span className="gantt-unassigned">Unassigned</span>}
                </td>
                {slots.map((t) => {
                  const working = isWorking(row, t);
                  const cellKey = `${dateKey}:${row.shift.id}:${row.person ? row.person.id : 'none'}:${t}`;
                  const value = handlers.positionCells[cellKey] || '';
                  return (
                    <td key={t} className={`day-grid-cell ${working ? 'is-working' : ''}`}>
                      {working && canEdit && (
                        <input
                          className="day-grid-input" list="rosta-position-list" value={value}
                          placeholder="—"
                          onChange={(e) => handlers.setPositionCell(cellKey, e.target.value)}
                          title="Type a position code or pick one from the list"
                        />
                      )}
                      {working && !canEdit && <span className="day-grid-readonly">{value || '—'}</span>}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
        <datalist id="rosta-position-list">
          {handlers.positions.map((p) => <option key={p} value={p} />)}
        </datalist>
      </div>
    </div>
  );
}

function DayView({ anchorDate, department, staff, templates, assignments, roster, handlers, canEdit }) {
  const dateKey = toKey(anchorDate);
  const tplId = assignments[`${dateKey}__${department}`];
  const tpl = tplId ? templates.find((t) => t.id === tplId) : null;
  const dayPickerKey = `assign:${dateKey}:${department}`;
  const deptStaff = staff.filter((s) => s.department === department && !s.archived);
  const [timeStep, setTimeStep] = useState(15);
  const [timeStepOpen, setTimeStepOpen] = useState(false);
  const timeStepRef = useOutsideClose(() => setTimeStepOpen(false));
  const [dragOverShiftId, setDragOverShiftId] = useState(null);
  const [viewMode, setViewMode] = useState('gantt');
  const [gridRef, gridWidth] = useElementWidth(820);
  const FIXED_COLS_WIDTH = 44 + 44 + 106 + 100 + 62;
  const ganttWidth = Math.max(gridWidth - FIXED_COLS_WIDTH, 240);

  /* Overall operating window for the day — used to lightly shade the active
     shift range so supervisors can see at a glance when the day starts/ends. */
  const workWindow = useMemo(() => {
    if (!tpl || tpl.shifts.length === 0) return null;
    let min = Infinity, max = -Infinity;
    tpl.shifts.forEach((s) => s.ranges.forEach((r) => {
      const a = minutesFromTimelineStart(r.start);
      let b = minutesFromTimelineStart(r.end);
      if (b <= a) b += 24 * 60;
      if (a < min) min = a;
      if (b > max) max = b;
    }));
    if (min === Infinity) return null;
    return { min, max };
  }, [tpl]);

  function assigneesFor(shiftId) {
    return deptStaff
      .map((p) => ({ person: p, entry: roster[rk(p.name, dateKey)] }))
      .filter((x) => x.entry && x.entry.shiftId === shiftId);
  }

  const rows = [];
  if (tpl) {
    tpl.shifts.forEach((shift) => {
      const assignees = assigneesFor(shift.id);
      if (assignees.length === 0) rows.push({ shift, person: null, entry: null });
      else assignees.forEach(({ person, entry }) => rows.push({ shift, person, entry }));
    });
  }
  const rowCount = Math.max(rows.length, 1) + (tpl && canEdit ? 1 : 0);

  return (
    <div className="day-view-wrap">
      <div className="day-view-toolbar">
        <DayViewHeader anchorDate={anchorDate} />
        {tpl && (
          <div className="day-view-tplinline">
            <span className="template-dot" style={{ background: `var(--tpl-${tpl.color}-dot)` }} />
            <span className="day-view-tplbar-name">{tpl.name}</span>
            {tpl.comments && tpl.comments.length > 0 && <span className="day-view-tplbar-comments">{tpl.comments.join(' · ')}</span>}
            {canEdit && (
              <span className="day-view-tplbar-actions">
                <button type="button" className="roster-day-edit-btn" onClick={() => handlers.openTemplateEditorForEdit(tpl)} title="Edit this template"><Pencil size={13} /></button>
                <button type="button" className="roster-day-edit-btn roster-day-remove-btn" onClick={() => handlers.unassignTemplate(dateKey, department)} title="Remove template from this day"><Trash2 size={13} /></button>
                <button type="button" className="roster-day-edit-btn" onClick={() => handlers.openPicker(dayPickerKey)} title="Replace with a different template"><ChevronDown size={13} /></button>
              </span>
            )}
            {handlers.pickerKey === dayPickerKey && (
              <TemplatePickerPopover
                department={department} templates={templates} current={tpl}
                onEdit={() => handlers.openTemplateEditorForEdit(tpl)}
                onRemove={() => { handlers.unassignTemplate(dateKey, department); handlers.closePicker(); }}
                onPick={(id) => { handlers.assignTemplate(dateKey, department, id); handlers.closePicker(); }}
                onCreateNew={() => handlers.openTemplateEditorForNew(department, dateKey)}
                onClose={handlers.closePicker}
              />
            )}
          </div>
        )}
        {tpl && (
          <div className="day-view-mode-toggle" role="group" aria-label="Day view display mode">
            <button type="button" className={viewMode === 'gantt' ? 'is-selected' : ''} onClick={() => setViewMode('gantt')} title="Timeline (Gantt) view">
              <ArrowUpDown size={12} style={{ transform: 'rotate(90deg)' }} /> Gantt
            </button>
            <button type="button" className={viewMode === 'grid' ? 'is-selected' : ''} onClick={() => setViewMode('grid')} title="Grid view — one cell per time slot">
              <LayoutDashboard size={12} /> Grid
            </button>
          </div>
        )}
        {tpl && viewMode === 'gantt' && (
          <div className="day-view-timestep" ref={timeStepRef}>
            <span className="day-view-timestep-label">Time step</span>
            <button type="button" className="day-view-timestep-trigger" onClick={() => setTimeStepOpen((o) => !o)} title="Set the drag-snap increment">
              {Math.floor(timeStep / 60)}h {timeStep % 60}m
            </button>
            {timeStepOpen && (
              <div className="time-scroller-popover">
                <TimeStepScroller totalMinutes={timeStep} onChange={setTimeStep} />
              </div>
            )}
          </div>
        )}
      </div>

      {!tpl ? (
        <div className="day-view-body">
          {canEdit ? (
            <button type="button" className="day-view-empty" onClick={() => handlers.openPicker(dayPickerKey)} title="Assign a template to this day">
              <Plus size={16} /><span>Assign a template for {department}</span>
            </button>
          ) : <div className="day-view-empty-static">No template assigned for {department}.</div>}
          {handlers.pickerKey === dayPickerKey && (
            <TemplatePickerPopover department={department} templates={templates} onPick={(id) => { handlers.assignTemplate(dateKey, department, id); handlers.closePicker(); }} onCreateNew={() => handlers.openTemplateEditorForNew(department, dateKey)} onClose={handlers.closePicker} />
          )}
        </div>
      ) : viewMode === 'grid' ? (
        <DayGridView
          tpl={tpl} rows={rows} dateKey={dateKey}
          handlers={handlers} canEdit={canEdit}
        />
      ) : (
        <div className="day-view-gantt-wrap">
          <div className="day-view-gantt-scroll">
            <div
              className="day-view-gantt-grid" ref={gridRef}
              style={{ gridTemplateColumns: `44px 44px 106px 100px 62px 1fr`, gridTemplateRows: `32px repeat(${rowCount}, 42px)` }}
            >
              <div className="gantt-head-cell" title="Shift code — drag to reorder, click to edit">Shift</div>
              <div className="gantt-head-cell" title="Hours">Hrs</div>
              <div className="gantt-head-cell gantt-head-left">Last Name</div>
              <div className="gantt-head-cell gantt-head-left">First Name</div>
              <div className="gantt-head-cell" title="Employee id">id#</div>
              <div className="gantt-ruler-cell">{ganttWidth > 40 && <TimelineRuler trackWidth={ganttWidth} />}</div>

              {rows.length === 0 && <div className="roster-empty-row" style={{ gridColumn: '1 / -1' }}>This template has no shifts yet — use the + below.</div>}
              {rows.map((row, idx) => {
                const cellKey = row.person ? `dayrow:${row.person.name}:${dateKey}` : `dayadd:${dateKey}:${row.shift.id}:${idx}`;
                const shiftBrowseKey = `dayshiftbrowse:${tpl.id}:${row.shift.id}`;
                const shiftEditKey = `dayshift:${tpl.id}:${row.shift.id}`;
                const isPickerOpen = handlers.pickerKey === cellKey;
                const isShiftBrowseOpen = handlers.pickerKey === shiftBrowseKey;
                const isShiftEditOpen = handlers.pickerKey === shiftEditKey;
                return (
                  <React.Fragment key={idx}>
                    <div className={`gantt-cell gantt-shift-cell ${dragOverShiftId === row.shift.id ? 'is-drag-over' : ''}`}>
                      <button
                        type="button"
                        className={`roster-shift-badge tpl-${row.shift.color} ${isShiftBrowseOpen || isShiftEditOpen ? 'is-active' : ''}`}
                        title={`Shift ${row.shift.id} · ${row.shift.role} — click to edit, replace, or remove; drag to reorder`}
                        draggable={canEdit}
                        onClick={() => handlers.openPicker(isShiftBrowseOpen ? null : shiftBrowseKey)}
                        onDragStart={(e) => { e.dataTransfer.setData('text/plain', row.shift.id); e.dataTransfer.effectAllowed = 'move'; }}
                        onDragOver={(e) => { if (canEdit) { e.preventDefault(); setDragOverShiftId(row.shift.id); } }}
                        onDragLeave={() => setDragOverShiftId(null)}
                        onDrop={(e) => {
                          e.preventDefault();
                          setDragOverShiftId(null);
                          const draggedId = e.dataTransfer.getData('text/plain');
                          if (draggedId && draggedId !== row.shift.id) handlers.reorderTemplateShift(tpl.id, draggedId, row.shift.id);
                        }}
                      >
                        {row.shift.id}
                      </button>
                      {isShiftBrowseOpen && (
                        <ShiftBrowsePicker
                          shifts={tpl.shifts} currentShiftId={row.shift.id}
                          onEdit={(shiftId) => handlers.openPicker(`dayshift:${tpl.id}:${shiftId}`)}
                          onDelete={(shiftId) => handlers.removeTemplateShift(tpl.id, shiftId)}
                          onCreateNew={() => handlers.addTemplateShift(tpl.id)}
                          onClose={handlers.closePicker}
                        />
                      )}
                      {isShiftEditOpen && (
                        <div className="shift-edit-popover">
                          <ShiftEditorRow
                            shift={row.shift}
                            onChange={(next) => handlers.updateTemplateShift(tpl.id, row.shift.id, next)}
                            onDelete={() => handlers.removeTemplateShift(tpl.id, row.shift.id)}
                            onClose={handlers.closePicker}
                          />
                        </div>
                      )}
                    </div>
                    <div className="gantt-cell">{row.entry ? fmtHrs(computeEntryHours(row.entry)) : ''}</div>
                    <div className="gantt-cell gantt-cell-left gantt-name-cell">
                      {row.person ? (
                        <>
                          <span className="gantt-name-text">{row.person.lastName}</span>
                          {canEdit && (
                            <button type="button" className="gantt-name-remove" onClick={() => handlers.unassignShift(row.person.name, dateKey)} title="Remove from this shift"><X size={11} /></button>
                          )}
                        </>
                      ) : canEdit ? (
                        <button type="button" className="gantt-name-add" onClick={() => handlers.openPicker(cellKey)} title={`Assign someone to shift ${row.shift.id}`}>
                          <Plus size={13} /> Unassigned
                        </button>
                      ) : (
                        <span className="gantt-unassigned">Unassigned</span>
                      )}
                      {isPickerOpen && !row.entry && (
                        <StaffPickerPopover staff={deptStaff} onPick={(person) => { handlers.assignShift(person.name, dateKey, row.shift); handlers.closePicker(); }} onClose={handlers.closePicker} />
                      )}
                    </div>
                    <div className="gantt-cell gantt-cell-left">{row.person ? row.person.firstName : ''}</div>
                    <div className="gantt-cell">{row.person ? row.person.id : ''}</div>
                    <div className={`gantt-bar-cell ${isPickerOpen ? 'is-editing' : ''}`}>
                      {workWindow && (() => {
                        const pxPerMin = ganttWidth / (24 * 60);
                        return <div className="gantt-work-window" style={{ left: workWindow.min * pxPerMin, width: (workWindow.max - workWindow.min) * pxPerMin }} title="Operating window for this day" />;
                      })()}
                      {row.entry && row.entry.ranges.map((r, rangeIdx) => (
                        canEdit ? (
                          <TimelineBar key={rangeIdx} start={r.start} end={r.end} color={row.shift.color} trackWidth={ganttWidth} snapMin={timeStep} label={row.person.firstName}
                            onChange={(s, e) => handlers.updateRosterRangeTime(row.person.name, dateKey, rangeIdx, s, e)}
                            onClick={() => handlers.openPicker(isShiftBrowseOpen ? null : shiftBrowseKey)} />
                        ) : (() => {
                          const g = barGeometry(r.start, r.end, ganttWidth);
                          return <div key={rangeIdx} className={`timeline-bar tpl-${row.shift.color}`} style={{ left: g.left, width: g.width }}><span className="timeline-bar-label">{row.person.firstName}</span></div>;
                        })()
                      ))}
                      {!row.entry && row.shift.ranges.map((r, i) => {
                        const g = barGeometry(r.start, r.end, ganttWidth);
                        return <div key={i} className="timeline-bar-ghost" style={{ left: g.left, width: g.width }} title="Unassigned — this only highlights the shift duration" />;
                      })}
                    </div>
                  </React.Fragment>
                );
              })}

              {canEdit && (
                <>
                  <div className="gantt-cell gantt-shift-cell">
                    <button type="button" className="roster-shift-badge shift-badge-add" onClick={() => handlers.addTemplateShift(tpl.id)} title="Add a new shift to this template"><Plus size={14} /></button>
                  </div>
                  <div className="gantt-cell" />
                  <div className="gantt-cell gantt-cell-left" />
                  <div className="gantt-cell gantt-cell-left" />
                  <div className="gantt-cell" />
                  <div className="gantt-bar-cell" />
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


function CalendarArea({ scale, anchorDate, department, departments, staff, templates, assignments, roster, customRange, weekStartsOn, hiddenStaffIds, extraStaffIds, handlers, onDrillDown, canEdit }) {
  switch (scale) {
    case 'Year':
      return <YearGrid anchorDate={anchorDate} department={department} assignments={assignments} templates={templates} weekStartsOn={weekStartsOn} onDrillDown={onDrillDown} />;
    case 'Week':
      return <WeekView anchorDate={anchorDate} weekStartsOn={weekStartsOn} department={department} departments={departments} staff={staff} templates={templates} assignments={assignments} roster={roster} hiddenStaffIds={hiddenStaffIds} extraStaffIds={extraStaffIds} handlers={handlers} canEdit={canEdit} />;
    case 'Day':
      return <DayView anchorDate={anchorDate} department={department} staff={staff} templates={templates} assignments={assignments} roster={roster} handlers={handlers} canEdit={canEdit} />;
    case 'Custom':
      return <CustomRosterView customRange={customRange} department={department} departments={departments} staff={staff} templates={templates} assignments={assignments} roster={roster} hiddenStaffIds={hiddenStaffIds} extraStaffIds={extraStaffIds} handlers={handlers} canEdit={canEdit} />;
    case 'Month':
    default:
      return <MonthGrid anchorDate={anchorDate} department={department} templates={templates} assignments={assignments} weekStartsOn={weekStartsOn} cellHandlers={handlers} onDrillDown={onDrillDown} canEdit={canEdit} />;
  }
}

/* ------------------------------------------------------------------ */
/* Template Tab                                                         */
/* ------------------------------------------------------------------ */

function TemplateTab({ templates, onOpenNew, onOpenEdit, onDeleteTemplate, canEdit }) {
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState('name');
  const [sortDir, setSortDir] = useState('asc');
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);

  const filtered = templates
    .filter((t) => {
      const q = search.trim().toLowerCase();
      if (!q) return true;
      return t.name.toLowerCase().includes(q) || t.department.toLowerCase().includes(q) || (t.comments || []).join(' ').toLowerCase().includes(q);
    })
    .sort((a, b) => {
      const av = (a[sortKey] || '').toString().toLowerCase();
      const bv = (b[sortKey] || '').toString().toLowerCase();
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sortDir === 'asc' ? cmp : -cmp;
    });

  function toggleSort(key) {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else { setSortKey(key); setSortDir('asc'); }
  }

  const deleteTarget = confirmDeleteId ? templates.find((t) => t.id === confirmDeleteId) : null;

  return (
    <div className="tab-page">
      <div className="tab-page-header">
        <h2>Templates</h2>
        {canEdit && (
          <button type="button" className="cta-btn" onClick={onOpenNew} title="Add a new template">
            <Plus size={14} /> Add Template
          </button>
        )}
      </div>
      <div className="tab-filter-row">
        <div className="tab-search"><Search size={14} /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Filter templates…" title="Filter by name, department, or comments" /></div>
        <span className="tab-filter-hint" title="Click a column header to sort"><Filter size={13} /> Click a header to sort</span>
      </div>
      <div className="tab-table">
        <div className="tab-table-row tab-table-head template-table-row">
          <button type="button" className="tab-sort-btn" onClick={() => toggleSort('name')} title="Sort by name">Name <ArrowUpDown size={11} /></button>
          <span>Comments</span>
          <button type="button" className="tab-sort-btn" onClick={() => toggleSort('department')} title="Sort by department">Department <ArrowUpDown size={11} /></button>
          <span>Shifts</span>
          {canEdit && <span className="tab-actions-head">Actions</span>}
        </div>
        {filtered.length === 0 && <div className="tab-table-empty">No templates match your filter.</div>}
        {filtered.map((t) => (
          <div key={t.id} className="tab-table-row template-table-row">
            <span className="tab-table-name"><span className="template-dot" style={{ background: `var(--tpl-${t.color}-dot)` }} />{t.name}</span>
            <span className="tab-table-comments" title={(t.comments || []).join(' · ')}>{(t.comments || []).join(' · ') || '—'}</span>
            <span>{t.department}</span>
            <span>{t.shifts.length}</span>
            {canEdit && (
              <span className="tab-table-actions">
                <button type="button" className="tpl-icon-btn" title="Edit template" onClick={() => onOpenEdit(t)}><Pencil size={14} /></button>
                <button type="button" className="tpl-icon-btn tpl-icon-btn-danger" title="Delete template" onClick={() => setConfirmDeleteId(t.id)}><Trash2 size={14} /></button>
              </span>
            )}
          </div>
        ))}
      </div>
      {deleteTarget && (
        <ConfirmDialog
          title="Delete this template?"
          message={`This removes "${deleteTarget.name}" and all ${deleteTarget.shifts.length} of its shifts. Any day it's assigned to will lose it.`}
          confirmLabel="Delete template"
          onConfirm={() => { onDeleteTemplate(deleteTarget.id); setConfirmDeleteId(null); }}
          onCancel={() => setConfirmDeleteId(null)}
        />
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Team Tab                                                              */
/* ------------------------------------------------------------------ */

function StaffEditor({ initial, departments, roles, onSave, onCancel }) {
  const [firstName, setFirstName] = useState(initial ? initial.firstName : '');
  const [lastName, setLastName] = useState(initial ? initial.lastName : '');
  const [id, setId] = useState(initial ? initial.id : '');
  const [department, setDepartment] = useState(initial ? initial.department : (departments[0] || ''));
  const [position, setPosition] = useState(initial ? initial.position : (roles[0] || ''));
  const [email, setEmail] = useState(initial ? initial.email : '');

  function handleSave() {
    if (!firstName.trim() || !lastName.trim() || !id.trim()) return;
    onSave({
      id: id.trim(), firstName: firstName.trim(), lastName: lastName.trim(),
      name: `${firstName.trim()} ${lastName.trim()}`,
      department, position, email: email.trim(), archived: initial ? initial.archived : false,
    });
  }

  return (
    <div className="modal-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) onCancel(); }}>
      <div className="modal-panel">
        <div className="modal-header">
          <h3>{initial ? 'Edit employee' : 'Add employee'}</h3>
          <button type="button" className="modal-close-btn" onClick={onCancel} title="Close"><X size={18} /></button>
        </div>
        <div className="modal-body">
          <div className="form-row">
            <label>First name<input className="quick-edit-input" value={firstName} onChange={(e) => setFirstName(e.target.value)} title="First name" /></label>
            <label>Last name<input className="quick-edit-input" value={lastName} onChange={(e) => setLastName(e.target.value)} title="Last name" /></label>
          </div>
          <div className="form-row">
            <label>id#<input className="quick-edit-input" value={id} onChange={(e) => setId(e.target.value)} title="Employee id" disabled={!!initial} /></label>
            <label>Email<input className="quick-edit-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} title="Email address" /></label>
          </div>
          <div className="form-row">
            <label>Department
              <select className="quick-edit-input" value={department} onChange={(e) => setDepartment(e.target.value)} title="Department">
                {departments.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </label>
            <label>Position
              <select className="quick-edit-input" value={position} onChange={(e) => setPosition(e.target.value)} title="Position">
                {roles.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </label>
          </div>
        </div>
        <div className="modal-footer">
          <button type="button" className="modal-cancel-btn" onClick={onCancel}>Cancel</button>
          <button type="button" className="quick-edit-save modal-save-btn" onClick={handleSave} title="Save employee">Save employee</button>
        </div>
      </div>
    </div>
  );
}

function TeamTab({ staff, departments, roles, onSaveStaff, onArchiveStaff, onDeleteStaff, canEdit }) {
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState('lastName');
  const [sortDir, setSortDir] = useState('asc');
  const [editing, setEditing] = useState(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);

  const filtered = staff
    .filter((s) => {
      const q = search.trim().toLowerCase();
      if (!q) return true;
      return s.name.toLowerCase().includes(q) || s.department.toLowerCase().includes(q) || s.position.toLowerCase().includes(q) || s.id.includes(q);
    })
    .sort((a, b) => {
      const av = (a[sortKey] || '').toString().toLowerCase();
      const bv = (b[sortKey] || '').toString().toLowerCase();
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sortDir === 'asc' ? cmp : -cmp;
    });

  function toggleSort(key) {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else { setSortKey(key); setSortDir('asc'); }
  }

  const deleteTarget = confirmDeleteId ? staff.find((s) => s.id === confirmDeleteId) : null;

  return (
    <div className="tab-page">
      <div className="tab-page-header">
        <h2>Team</h2>
        {canEdit && <button type="button" className="cta-btn" onClick={() => setEditing({ isNew: true })} title="Add a new employee"><Plus size={14} /> Add Employee</button>}
      </div>
      <div className="tab-filter-row">
        <div className="tab-search"><Search size={14} /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Filter team…" title="Filter by name, department, position, or id" /></div>
        <span className="tab-filter-hint" title="Click a column header to sort"><Filter size={13} /> Click a header to sort</span>
      </div>
      <div className="tab-table team-table">
        <div className="tab-table-row tab-table-head team-table-row">
          <button type="button" className="tab-sort-btn" onClick={() => toggleSort('lastName')} title="Sort by last name">Last Name <ArrowUpDown size={11} /></button>
          <button type="button" className="tab-sort-btn" onClick={() => toggleSort('firstName')} title="Sort by first name">First Name <ArrowUpDown size={11} /></button>
          <button type="button" className="tab-sort-btn" onClick={() => toggleSort('id')} title="Sort by id">id# <ArrowUpDown size={11} /></button>
          <button type="button" className="tab-sort-btn" onClick={() => toggleSort('department')} title="Sort by department">Department <ArrowUpDown size={11} /></button>
          <button type="button" className="tab-sort-btn" onClick={() => toggleSort('position')} title="Sort by position">Position <ArrowUpDown size={11} /></button>
          <span>Email</span>
          {canEdit && (<><span>Edit</span><span>Password</span><span>Archive</span><span>Delete</span></>)}
        </div>
        {filtered.length === 0 && <div className="tab-table-empty">No team members match your filter.</div>}
        {filtered.map((s) => (
          <div key={s.id} className={`tab-table-row team-table-row ${s.archived ? 'is-archived' : ''}`}>
            <span>{s.lastName}</span>
            <span>{s.firstName}</span>
            <span>{s.id}</span>
            <span>{s.department}</span>
            <span>{s.position}</span>
            <span className="team-email" title={s.email}><Mail size={12} />{s.email}</span>
            {canEdit && (
              <>
                <button type="button" className="tpl-icon-btn" title="Edit employee" onClick={() => setEditing({ id: s.id })}><Pencil size={14} /></button>
                <button type="button" className="team-text-action" title="Send a password reset email">Reset</button>
                <button type="button" className="team-text-action" title={s.archived ? 'Restore this employee' : 'Archive this employee'} onClick={() => onArchiveStaff(s.id)}>{s.archived ? 'Restore' : 'Archive'}</button>
                <button type="button" className="tpl-icon-btn tpl-icon-btn-danger" title="Delete employee" onClick={() => setConfirmDeleteId(s.id)}><Trash2 size={14} /></button>
              </>
            )}
          </div>
        ))}
      </div>
      {editing && (
        <StaffEditor
          initial={editing.isNew ? null : staff.find((s) => s.id === editing.id)}
          departments={departments} roles={roles}
          onSave={(saved) => { onSaveStaff(saved, !!editing.isNew); setEditing(null); }}
          onCancel={() => setEditing(null)}
        />
      )}
      {deleteTarget && (
        <ConfirmDialog
          title="Delete this employee?"
          message={`This permanently removes ${deleteTarget.name} from the team. Any shifts already assigned to them will remain on the schedule but show no employee.`}
          confirmLabel="Delete employee"
          onConfirm={() => { onDeleteStaff(deleteTarget.id); setConfirmDeleteId(null); }}
          onCancel={() => setConfirmDeleteId(null)}
        />
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Settings Tab                                                         */
/* ------------------------------------------------------------------ */

/* Reorderable chip list — drag any chip to change its order. Used for
   departments, roles, and position codes in Settings. */
function DraggableChipList({ items, onRemove, onReorder, canEdit, labelFor }) {
  const [dragItem, setDragItem] = useState(null);
  const [overItem, setOverItem] = useState(null);
  return (
    <div className="settings-chip-list">
      {items.length === 0 && <span className="settings-chip-empty">Nothing added yet.</span>}
      {items.map((it) => (
        <span
          key={it}
          className={`settings-chip ${canEdit ? 'is-draggable' : ''} ${overItem === it && dragItem !== it ? 'is-drag-over' : ''} ${dragItem === it ? 'is-dragging' : ''}`}
          draggable={canEdit}
          onDragStart={(e) => { setDragItem(it); e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/plain', it); }}
          onDragEnd={() => { setDragItem(null); setOverItem(null); }}
          onDragOver={(e) => { if (canEdit) { e.preventDefault(); setOverItem(it); } }}
          onDragLeave={() => setOverItem((cur) => (cur === it ? null : cur))}
          onDrop={(e) => {
            e.preventDefault();
            const from = e.dataTransfer.getData('text/plain');
            if (from && from !== it) onReorder(from, it);
            setDragItem(null); setOverItem(null);
          }}
          title={canEdit ? `${labelFor || 'Item'}: ${it} — drag to reorder` : it}
        >
          {canEdit && <GripVertical size={11} className="settings-chip-grip" />}
          {it}
          {canEdit && <button type="button" onClick={() => onRemove(it)} title={`Remove ${it}`}><X size={11} /></button>}
        </span>
      ))}
    </div>
  );
}

function SettingsTab({ workspace, onWorkspace, role, onRole, departments, onAddDepartment, onRemoveDepartment, onReorderDepartment, roles, onAddRole, onRemoveRole, onReorderRole, positions, onAddPosition, onRemovePosition, onReorderPosition, themeMode, onThemeMode, colorTheme, onColorTheme, canEdit }) {
  const [newDept, setNewDept] = useState('');
  const [newRole, setNewRole] = useState('');
  const [newPosition, setNewPosition] = useState('');

  return (
    <div className="tab-page settings-page">
      <div className="tab-page-header"><h2>Settings</h2></div>

      <div className="settings-section">
        <h3><Palette size={16} /> Appearance</h3>
        <div className="settings-mode-row">
          <button type="button" className={`settings-mode-btn ${themeMode === 'dark' ? 'is-selected' : ''}`} onClick={() => onThemeMode('dark')} title="Dark mode">
            <Moon size={14} /> Dark
          </button>
          <button type="button" className={`settings-mode-btn ${themeMode === 'light' ? 'is-selected' : ''}`} onClick={() => onThemeMode('light')} title="Light mode">
            <Sun size={14} /> Light
          </button>
        </div>
        <div className="settings-theme-row">
          {Object.entries(COLOR_THEMES).map(([key, t]) => (
            <button key={key} type="button" className={`settings-theme-swatch ${colorTheme === key ? 'is-selected' : ''}`} onClick={() => onColorTheme(key)} title={`${t.name} theme`} style={{ background: t[themeMode].cta }}>
              {colorTheme === key && <Check size={14} strokeWidth={3} color={t[themeMode].ctaOn} />}
            </button>
          ))}
        </div>
      </div>

      <div className="settings-section">
        <h3><Building2 size={16} /> Workspace</h3>
        <label className="settings-field">Workspace name
          <input className="quick-edit-input" value={workspace} onChange={(e) => onWorkspace(e.target.value)} title="Workspace name" disabled={!canEdit} />
        </label>
      </div>

      <div className="settings-section">
        <h3><ShieldCheck size={16} /> Viewing as</h3>
        <p className="settings-hint">License Keeper and Admin can do everything — license issuing is License-Keeper-only. Managers and Assistant Managers build and edit the schedule. Supervisors can view everything and fill the rotation grid, but can't edit templates or settings.</p>
        <div className="settings-role-list">
          {USER_ROLES.map((r) => (
            <button key={r} type="button" className={`settings-role-btn ${r === role ? 'is-selected' : ''}`} onClick={() => onRole(r)} title={`View as ${r}`}>
              {r === 'License Keeper' && <KeyRound size={14} />}
              {r === 'Admin' && <UserCog size={14} />}
              {(r === 'Manager' || r === 'Assistant Manager') && <Briefcase size={14} />}
              {r === 'Supervisor' && <ClipboardList size={14} />}
              {r}
            </button>
          ))}
        </div>
      </div>

      <div className="settings-section">
        <h3><Building2 size={16} /> Departments</h3>
        <p className="settings-hint">Drag to reorder. Templates and shifts are scoped to a department.</p>
        <DraggableChipList items={departments} onRemove={onRemoveDepartment} onReorder={onReorderDepartment} canEdit={canEdit} labelFor="Department" />
        {canEdit && (
          <div className="settings-add-row">
            <input className="quick-edit-input" value={newDept} onChange={(e) => setNewDept(e.target.value)} placeholder="New department" title="New department name" />
            <button type="button" className="tpl-icon-btn settings-add-btn" onClick={() => { if (newDept.trim()) { onAddDepartment(newDept.trim()); setNewDept(''); } }} title="Add department"><Plus size={14} /></button>
          </div>
        )}
      </div>

      <div className="settings-section">
        <h3><Briefcase size={16} /> Roles / positions</h3>
        <p className="settings-hint">Job titles assigned to employees in the Team tab. Drag to reorder.</p>
        <DraggableChipList items={roles} onRemove={onRemoveRole} onReorder={onReorderRole} canEdit={canEdit} labelFor="Role" />
        {canEdit && (
          <div className="settings-add-row">
            <input className="quick-edit-input" value={newRole} onChange={(e) => setNewRole(e.target.value)} placeholder="New role / position" title="New role or position name" />
            <button type="button" className="tpl-icon-btn settings-add-btn" onClick={() => { if (newRole.trim()) { onAddRole(newRole.trim()); setNewRole(''); } }} title="Add role"><Plus size={14} /></button>
          </div>
        )}
      </div>

      <div className="settings-section">
        <h3><LayoutTemplate size={16} /> Position codes</h3>
        <p className="settings-hint">Short codes (B1, RW2, BRK…) offered in Day view's grid mode. Drag to reorder.</p>
        <DraggableChipList items={positions} onRemove={onRemovePosition} onReorder={onReorderPosition} canEdit={canEdit} labelFor="Position code" />
        {canEdit && (
          <div className="settings-add-row">
            <input className="quick-edit-input" value={newPosition} onChange={(e) => setNewPosition(e.target.value)} placeholder="New position code" title="New position code" />
            <button type="button" className="tpl-icon-btn settings-add-btn" onClick={() => { if (newPosition.trim()) { onAddPosition(newPosition.trim()); setNewPosition(''); } }} title="Add position code"><Plus size={14} /></button>
          </div>
        )}
      </div>
    </div>
  );
}

function DashboardTab({ department, staff, templates, assignments, roster }) {
  const days = useMemo(() => Array.from({ length: 7 }, (_, i) => addDays(TODAY, i)), []);
  const deptStaff = staff.filter((s) => s.department === department && !s.archived);

  const { neededSlots, filledSlots, gaps, daysUncovered, upcoming } = useMemo(() => {
    let needed = 0, filled = 0;
    const gapList = [];
    const uncoveredList = [];
    const upcomingList = [];
    days.forEach((d) => {
      const dateKey = toKey(d);
      const tplId = assignments[`${dateKey}__${department}`];
      const tpl = tplId ? templates.find((t) => t.id === tplId) : null;
      upcomingList.push({ date: d, tpl });
      if (!tpl) { uncoveredList.push(d); return; }
      tpl.shifts.forEach((shift) => {
        needed++;
        const isFilled = deptStaff.some((p) => {
          const entry = roster[rk(p.name, dateKey)];
          return entry && entry.shiftId === shift.id;
        });
        if (isFilled) filled++;
        else gapList.push({ date: d, shift, tpl });
      });
    });
    return { neededSlots: needed, filledSlots: filled, gaps: gapList, daysUncovered: uncoveredList, upcoming: upcomingList };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [days, department, templates, assignments, roster, staff]);

  const fillRate = neededSlots > 0 ? Math.round((filledSlots / neededSlots) * 100) : 100;

  const utilization = useMemo(() => deptStaff.map((p) => {
    let hours = 0;
    days.forEach((d) => {
      const entry = roster[rk(p.name, toKey(d))];
      if (entry) hours += computeEntryHours(entry);
    });
    return { person: p, hours: Math.round(hours * 10) / 10 };
  }).sort((a, b) => b.hours - a.hours),
  // eslint-disable-next-line react-hooks/exhaustive-deps
  [deptStaff, days, roster]);

  return (
    <div className="tab-page dashboard-page">
      <div className="tab-page-header"><h2>Dashboard</h2><span className="dash-subtitle">{department} · next 7 days from today</span></div>

      <div className="dash-stats-row">
        <div className="dash-stat-card is-primary">
          <div className="dash-stat-top">
            <span className="dash-stat-label">Shift fill rate</span>
            <span className={`dash-stat-chip ${fillRate < 80 ? 'is-warn' : 'is-good'}`}>{fillRate >= 95 ? 'On track' : fillRate >= 80 ? 'Watch' : 'At risk'}</span>
          </div>
          <span className="dash-stat-value">{fillRate}<span className="dash-stat-unit">%</span></span>
          <div className="dash-meter"><div className={`dash-meter-fill ${fillRate < 80 ? 'is-warn' : 'is-good'}`} style={{ width: `${fillRate}%` }} /></div>
          <span className="dash-stat-sub">{filledSlots} of {neededSlots} shifts covered</span>
        </div>
        <div className="dash-stat-card">
          <div className="dash-stat-top"><span className="dash-stat-label">Unfilled shifts</span><span className="dash-stat-icon"><Bell size={14} /></span></div>
          <span className={`dash-stat-value ${gaps.length > 0 ? 'is-warn' : 'is-good'}`}>{gaps.length}</span>
          <span className="dash-stat-sub">{gaps.length === 0 ? 'Nothing outstanding' : 'Needs assignment'}</span>
        </div>
        <div className="dash-stat-card">
          <div className="dash-stat-top"><span className="dash-stat-label">Days with no template</span><span className="dash-stat-icon"><CalendarOff size={14} /></span></div>
          <span className={`dash-stat-value ${daysUncovered.length > 0 ? 'is-warn' : 'is-good'}`}>{daysUncovered.length}</span>
          <span className="dash-stat-sub">of next {days.length} days</span>
        </div>
        <div className="dash-stat-card">
          <div className="dash-stat-top"><span className="dash-stat-label">Active crew</span><span className="dash-stat-icon"><Users size={14} /></span></div>
          <span className="dash-stat-value">{deptStaff.length}</span>
          <span className="dash-stat-sub">{department}</span>
        </div>
      </div>

      <div className="dash-grid-2col">
        <div className="dash-panel">
          <h3>Upcoming — next 7 days</h3>
          <div className="dash-upcoming-list">
            {upcoming.map(({ date, tpl }) => (
              <div key={toKey(date)} className={`dash-upcoming-row ${isSameDay(date, TODAY) ? 'is-today' : ''}`}>
                <span className="dash-upcoming-date">{WEEKDAY_BASE[date.getDay()]}, {MONTH_LABELS[date.getMonth()].slice(0, 3)} {date.getDate()}</span>
                {tpl ? (
                  <span className="dash-upcoming-tpl"><span className="template-dot" style={{ background: `var(--tpl-${tpl.color}-dot)` }} />{tpl.name}</span>
                ) : (
                  <span className="dash-upcoming-empty">No template assigned</span>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="dash-panel">
          <h3>Staffing gaps</h3>
          {gaps.length === 0 ? (
            <div className="dash-empty-good"><Check size={15} /> Every shift in the next 7 days is covered.</div>
          ) : (
            <div className="dash-gaps-list">
              {gaps.slice(0, 8).map((g, i) => (
                <div key={i} className="dash-gap-row">
                  <span className={`roster-shift-badge tpl-${g.shift.color}`}>{g.shift.id}</span>
                  <span className="dash-gap-info">{g.tpl.name} · {WEEKDAY_BASE[g.date.getDay()]} {MONTH_LABELS[g.date.getMonth()].slice(0, 3)} {g.date.getDate()}</span>
                </div>
              ))}
              {gaps.length > 8 && <div className="dash-gap-more">+{gaps.length - 8} more</div>}
            </div>
          )}
        </div>
      </div>

      <div className="dash-panel dash-panel-wide">
        <h3>Team utilization — next 7 days</h3>
        <div className="dash-util-list">
          {utilization.length === 0 && <div className="template-picker-empty">No staff in {department}.</div>}
          {utilization.map(({ person, hours }) => (
            <div key={person.id} className="dash-util-row">
              <span className="dash-util-name">{person.name}</span>
              <div className="dash-util-bar-track"><div className="dash-util-bar-fill" style={{ width: `${Math.min((hours / 56) * 100, 100)}%` }} /></div>
              <span className="dash-util-hours">{fmtHrs(hours)} hrs</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function PrintCenterTab({ department, departments, staff, templates, assignments, roster, workspace }) {
  const [rangeStart, setRangeStart] = useState(TODAY);
  const [rangeDays, setRangeDays] = useState(7);
  const [printDept, setPrintDept] = useState(department);
  const [format, setFormat] = useState('grid');
  const [staffFilter, setStaffFilter] = useState('all');

  const days = Array.from({ length: rangeDays }, (_, i) => addDays(rangeStart, i));
  const deptStaffAll = staff.filter((s) => s.department === printDept && !s.archived);
  const deptStaff = deptStaffAll.filter((s) => staffFilter === 'all' || s.id === staffFilter);

  return (
    <div className="tab-page print-center-page">
      <div className="tab-page-header no-print">
        <h2>Print Center</h2>
        <button type="button" className="cta-btn" onClick={() => window.print()} title="Print this schedule"><Printer size={14} /> Print</button>
      </div>

      <div className="print-config-row no-print">
        <label className="print-config-field">Department
          <select className="quick-edit-input" value={printDept} onChange={(e) => { setPrintDept(e.target.value); setStaffFilter('all'); }}>
            {departments.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </label>
        <label className="print-config-field">Employee
          <select className="quick-edit-input" value={staffFilter} onChange={(e) => setStaffFilter(e.target.value)}>
            <option value="all">All employees</option>
            {deptStaffAll.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </label>
        <label className="print-config-field">Start date
          <input
            type="date" className="quick-edit-input" value={toKey(rangeStart)}
            onChange={(e) => { const [y, m, d] = e.target.value.split('-').map(Number); if (y && m && d) setRangeStart(new Date(y, m - 1, d)); }}
          />
        </label>
        <label className="print-config-field">Range
          <select className="quick-edit-input" value={rangeDays} onChange={(e) => setRangeDays(Number(e.target.value))}>
            <option value={7}>7 days</option>
            <option value={14}>14 days</option>
            <option value={30}>30 days</option>
          </select>
        </label>
        <label className="print-config-field">Format
          <div className="print-format-toggle">
            <button type="button" className={format === 'grid' ? 'is-selected' : ''} onClick={() => setFormat('grid')}>Grid</button>
            <button type="button" className={format === 'list' ? 'is-selected' : ''} onClick={() => setFormat('list')}>List</button>
          </div>
        </label>
      </div>

      <div className="print-preview-wrap">
        <div className="print-preview-output">
          <div className="print-header">
            <div className="print-masthead">
              <div>
                <div className="print-eyebrow">{workspace}</div>
                <h1>{printDept} Schedule</h1>
                <p className="print-daterange">
                  {WEEKDAY_FULL_BASE[days[0].getDay()]}, {MONTH_LABELS[days[0].getMonth()]} {days[0].getDate()} — {WEEKDAY_FULL_BASE[days[days.length - 1].getDay()]}, {MONTH_LABELS[days[days.length - 1].getMonth()]} {days[days.length - 1].getDate()}, {days[days.length - 1].getFullYear()}
                </p>
              </div>
              <div className="print-meta">
                <div><span>Employees</span><strong>{deptStaff.length}</strong></div>
                <div><span>Days</span><strong>{days.length}</strong></div>
                <div><span>Generated</span><strong>{MONTH_LABELS[TODAY.getMonth()].slice(0, 3)} {TODAY.getDate()}, {TODAY.getFullYear()}</strong></div>
              </div>
            </div>
          </div>

          {deptStaff.length === 0 ? (
            <div className="print-empty">No employees to show for this selection.</div>
          ) : format === 'grid' ? (
            <table className="print-grid-table">
              <thead>
                <tr>
                  <th>Employee</th>
                  {days.map((d) => <th key={toKey(d)}>{WEEKDAY_BASE[d.getDay()]}<br />{MONTH_LABELS[d.getMonth()].slice(0, 3)} {d.getDate()}</th>)}
                </tr>
              </thead>
              <tbody>
                {deptStaff.map((p) => (
                  <tr key={p.id}>
                    <td className="print-name-cell">{p.name}</td>
                    {days.map((d) => {
                      const entry = roster[rk(p.name, toKey(d))];
                      return (
                        <td key={toKey(d)}>
                          {entry ? entry.ranges.map((r, i) => <div key={i}>{formatTime12h(r.start)}–{formatTime12h(r.end)}</div>) : <span className="print-off">—</span>}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="print-list-view">
              {days.map((d) => {
                const dateKey = toKey(d);
                const tplId = assignments[`${dateKey}__${printDept}`];
                const tpl = tplId ? templates.find((t) => t.id === tplId) : null;
                const dayEntries = deptStaff
                  .map((p) => ({ p, entry: roster[rk(p.name, dateKey)] }))
                  .filter((x) => x.entry);
                return (
                  <div key={dateKey} className="print-list-day">
                    <h3>{WEEKDAY_FULL_BASE[d.getDay()]}, {MONTH_LABELS[d.getMonth()]} {d.getDate()} — {tpl ? tpl.name : 'No template'}</h3>
                    {dayEntries.length === 0 ? <p className="print-off">No assignments.</p> : (
                      <ul>
                        {dayEntries.map(({ p, entry }) => (
                          <li key={p.id}>{p.name} — Shift {entry.shiftId}: {entry.ranges.map((r) => `${formatTime12h(r.start)}–${formatTime12h(r.end)}`).join(', ')}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          <div className="print-footer">
            <span>{workspace} · {printDept} · Generated {MONTH_LABELS[TODAY.getMonth()]} {TODAY.getDate()}, {TODAY.getFullYear()}</span>
            <span className="print-footer-sign">Approved by _______________________</span>
          </div>
        </div>
      </div>
    </div>
  );
}

const GUIDE_CONTENT = {
  admin: {
    label: 'Admin', icon: KeyRound,
    steps: [
      { title: 'Set up your workspace', body: 'In Settings, name your workspace and choose an appearance — dark or light mode, plus an accent color theme.' },
      { title: 'Define departments', body: 'Add every department your business schedules separately (e.g. Dealers, Supervisors, Cage, Slots). Templates and shifts are scoped to a department.' },
      { title: 'Define roles and positions', body: 'Add the job titles your team uses so they are ready to assign from the Team tab.' },
      { title: 'Preview other roles', body: 'Use the role switcher at the bottom of the sidebar to see exactly what Managers and Supervisors can access.' },
    ],
  },
  manager: {
    label: 'Manager', icon: Briefcase,
    steps: [
      { title: 'Build a template', body: 'Open Templates and create one per recurring scenario. Add shifts inside it — each has its own id, time range(s), role, and color.' },
      { title: 'Assign templates to the calendar', body: 'On Month, Week, Custom, or Day view, click an empty day and pick a template, or create a new one on the spot.' },
      { title: 'Fill the roster', body: 'On Week or Custom view, click a shift cell to assign a crew member. Drag a shift badge up or down to reorder it within a template.' },
      { title: 'Keep the team current', body: 'Add, edit, or archive crew members in the Team tab as your roster changes.' },
      { title: 'Watch the Dashboard', body: 'Check fill rate and staffing gaps before the week starts, so nothing is left unfilled at the last minute.' },
    ],
  },
  supervisor: {
    label: 'Supervisor', icon: ClipboardList,
    steps: [
      { title: 'Find your day', body: 'Use the Year to Week to Day drill-down, or jump straight to Day view, to see exactly who is working and when.' },
      { title: 'Fill an open slot', body: 'On Week, Custom, or Day view, click an empty shift slot to assign someone from the crew list.' },
      { title: 'Adjust on the fly', body: 'Drag either edge of a Gantt bar in Day view to change a start or end time — it saves the moment you let go.' },
      { title: 'Edit or remove a shift', body: 'Click any shift badge to edit its details, replace it with another shift, or remove the assignment entirely.' },
    ],
  },
};

function GuideTab() {
  const [active, setActive] = useState('manager');
  const section = GUIDE_CONTENT[active];
  return (
    <div className="tab-page guide-page">
      <div className="tab-page-header"><h2>Guide</h2></div>
      <div className="guide-role-tabs">
        {Object.entries(GUIDE_CONTENT).map(([key, s]) => {
          const RoleIcon = s.icon;
          return (
            <button key={key} type="button" className={`guide-role-tab ${active === key ? 'is-active' : ''}`} onClick={() => setActive(key)}>
              <RoleIcon size={15} /> {s.label}
            </button>
          );
        })}
      </div>
      <div className="guide-steps">
        {section.steps.map((step, i) => (
          <div key={i} className="guide-step">
            <span className="guide-step-num">{i + 1}</span>
            <div>
              <div className="guide-step-title">{step.title}</div>
              <div className="guide-step-body">{step.body}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function AboutTab() {
  return (
    <div className="tab-page about-page">
      <div className="tab-page-header"><h2>About</h2></div>
      <div className="about-card">
        <div className="about-logo"><CalendarDays size={26} /></div>
        <h3>Rosta Studio</h3>
        <p className="about-version">Version 1.0 — internal preview</p>
        <p>A customizable roster and scheduling tool built for teams that run on shifting, recurring patterns — cruise casinos, restaurants, retail, and beyond. Templates and shifts are reusable, department-aware, and editable from every view that shows them.</p>
      </div>
    </div>
  );
}

const REPORT_TYPES = [
  { key: 'coverage', label: 'Shift coverage', desc: 'Which shifts were filled or left open, day by day.' },
  { key: 'hours', label: 'Employee hours', desc: 'Total scheduled hours per employee across the range.' },
  { key: 'position', label: 'Staffing by position', desc: 'Headcount and hours grouped by job position.' },
  { key: 'utilization', label: 'Team utilization', desc: 'Days worked, days off, and average shift length.' },
];

function ReportCenterTab({ department, departments, staff, templates, assignments, roster }) {
  const [reportType, setReportType] = useState('coverage');
  const [reportDept, setReportDept] = useState(department);
  const [rangeStart, setRangeStart] = useState(TODAY);
  const [rangeDays, setRangeDays] = useState(14);

  const days = useMemo(() => Array.from({ length: rangeDays }, (_, i) => addDays(rangeStart, i)), [rangeStart, rangeDays]);
  const deptStaff = useMemo(() => staff.filter((s) => s.department === reportDept && !s.archived), [staff, reportDept]);

  const report = useMemo(() => {
    if (reportType === 'coverage') {
      const rowsOut = days.map((d) => {
        const dateKey = toKey(d);
        const tplId = assignments[`${dateKey}__${reportDept}`];
        const tpl = tplId ? templates.find((t) => t.id === tplId) : null;
        if (!tpl) return { date: d, tplName: '—', total: 0, filled: 0 };
        let filled = 0;
        tpl.shifts.forEach((sh) => {
          if (deptStaff.some((p) => { const e = roster[rk(p.name, dateKey)]; return e && e.shiftId === sh.id; })) filled++;
        });
        return { date: d, tplName: tpl.name, total: tpl.shifts.length, filled };
      });
      return {
        headers: ['Date', 'Template', 'Shifts', 'Filled', 'Coverage'],
        rows: rowsOut.map((r) => [
          `${WEEKDAY_BASE[r.date.getDay()]} ${MONTH_LABELS[r.date.getMonth()].slice(0, 3)} ${r.date.getDate()}`,
          r.tplName, String(r.total), String(r.filled),
          r.total > 0 ? `${Math.round((r.filled / r.total) * 100)}%` : '—',
        ]),
      };
    }
    if (reportType === 'hours') {
      return {
        headers: ['Employee', 'id#', 'Position', 'Days worked', 'Total hrs'],
        rows: deptStaff.map((p) => {
          let hrs = 0, worked = 0;
          days.forEach((d) => { const e = roster[rk(p.name, toKey(d))]; if (e) { hrs += computeEntryHours(e); worked++; } });
          return [p.name, p.id, p.position, String(worked), fmtHrs(hrs)];
        }),
      };
    }
    if (reportType === 'position') {
      const byPos = {};
      deptStaff.forEach((p) => {
        if (!byPos[p.position]) byPos[p.position] = { count: 0, hrs: 0 };
        byPos[p.position].count++;
        days.forEach((d) => { const e = roster[rk(p.name, toKey(d))]; if (e) byPos[p.position].hrs += computeEntryHours(e); });
      });
      return {
        headers: ['Position', 'Headcount', 'Total hrs', 'Avg hrs / person'],
        rows: Object.entries(byPos).map(([pos, v]) => [
          pos, String(v.count), fmtHrs(v.hrs), fmtHrs(v.hrs / v.count),
        ]),
      };
    }
    return {
      headers: ['Employee', 'Days worked', 'Days off', 'Total hrs', 'Avg shift'],
      rows: deptStaff.map((p) => {
        let hrs = 0, worked = 0;
        days.forEach((d) => { const e = roster[rk(p.name, toKey(d))]; if (e) { hrs += computeEntryHours(e); worked++; } });
        return [p.name, String(worked), String(days.length - worked), fmtHrs(hrs),
          worked > 0 ? fmtHrs(hrs / worked) : fmtHrs(0)];
      }),
    };
  }, [reportType, days, deptStaff, roster, assignments, templates, reportDept]);

  function exportCsv() {
    const esc = (v) => `"${String(v).replace(/"/g, '""')}"`;
    const csv = [report.headers.map(esc).join(','), ...report.rows.map((r) => r.map(esc).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `rosta-${reportType}-${toKey(rangeStart)}.csv`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  const active = REPORT_TYPES.find((r) => r.key === reportType);

  return (
    <div className="tab-page">
      <div className="tab-page-header">
        <h2>Report Center</h2>
        <button type="button" className="cta-btn" onClick={exportCsv} title="Download this report as CSV"><FileBarChart size={14} /> Export CSV</button>
      </div>

      <div className="report-type-row">
        {REPORT_TYPES.map((r) => (
          <button key={r.key} type="button" className={`report-type-card ${reportType === r.key ? 'is-active' : ''}`} onClick={() => setReportType(r.key)}>
            <span className="report-type-label">{r.label}</span>
            <span className="report-type-desc">{r.desc}</span>
          </button>
        ))}
      </div>

      <div className="print-config-row">
        <label className="print-config-field">Department
          <select className="quick-edit-input" value={reportDept} onChange={(e) => setReportDept(e.target.value)}>
            {departments.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </label>
        <label className="print-config-field">Start date
          <input type="date" className="quick-edit-input" value={toKey(rangeStart)}
            onChange={(e) => { const [y, m, d] = e.target.value.split('-').map(Number); if (y && m && d) setRangeStart(new Date(y, m - 1, d)); }} />
        </label>
        <label className="print-config-field">Range
          <select className="quick-edit-input" value={rangeDays} onChange={(e) => setRangeDays(Number(e.target.value))}>
            <option value={7}>7 days</option><option value={14}>14 days</option><option value={30}>30 days</option>
          </select>
        </label>
      </div>

      <div className="report-output">
        <h3 className="report-output-title">{active.label} — {reportDept}</h3>
        <div className="report-table-wrap">
          <table className="report-table">
            <thead><tr>{report.headers.map((h) => <th key={h}>{h}</th>)}</tr></thead>
            <tbody>
              {report.rows.length === 0 && <tr><td colSpan={report.headers.length} className="report-empty">No data for this selection.</td></tr>}
              {report.rows.map((r, i) => (
                <tr key={i}>{r.map((c, j) => <td key={j} className={j > 0 && /^[\d.]+%?$/.test(c) ? 'is-num' : ''}>{c}</td>)}</tr>
              ))}
            </tbody>
            {report.rows.length > 0 && (
              <tfoot>
                <tr>
                  {report.headers.map((h, j) => {
                    if (j === 0) return <td key={j}>{report.rows.length} rows</td>;
                    const nums = report.rows.map((r) => parseFloat(r[j])).filter((n) => !isNaN(n));
                    const isPct = report.rows.some((r) => String(r[j]).endsWith('%'));
                    if (nums.length !== report.rows.length) return <td key={j} />;
                    if (isPct) return <td key={j} className="is-num">{Math.round(nums.reduce((a, b) => a + b, 0) / nums.length)}%</td>;
                    return <td key={j} className="is-num">{fmtHrs(nums.reduce((a, b) => a + b, 0))}</td>;
                  })}
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>
    </div>
  );
}

function OffTrackerTab({ department, departments, staff, roster }) {
  const [offDept, setOffDept] = useState(department);
  const [rangeStart, setRangeStart] = useState(TODAY);
  const [rangeDays, setRangeDays] = useState(14);
  const days = useMemo(() => Array.from({ length: rangeDays }, (_, i) => addDays(rangeStart, i)), [rangeStart, rangeDays]);
  const deptStaff = staff.filter((s) => s.department === offDept && !s.archived);

  return (
    <div className="tab-page">
      <div className="tab-page-header"><h2>Off Tracker</h2><span className="dash-subtitle">Days without a scheduled shift</span></div>
      <div className="print-config-row">
        <label className="print-config-field">Department
          <select className="quick-edit-input" value={offDept} onChange={(e) => setOffDept(e.target.value)}>
            {departments.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </label>
        <label className="print-config-field">Start date
          <input type="date" className="quick-edit-input" value={toKey(rangeStart)}
            onChange={(e) => { const [y, m, d] = e.target.value.split('-').map(Number); if (y && m && d) setRangeStart(new Date(y, m - 1, d)); }} />
        </label>
        <label className="print-config-field">Range
          <select className="quick-edit-input" value={rangeDays} onChange={(e) => setRangeDays(Number(e.target.value))}>
            <option value={7}>7 days</option><option value={14}>14 days</option><option value={30}>30 days</option>
          </select>
        </label>
      </div>
      <div className="report-output">
        <div className="report-table-wrap">
          <table className="report-table off-tracker-table">
            <thead>
              <tr>
                <th className="off-name-col">Employee</th>
                {days.map((d) => <th key={toKey(d)} className="off-day-col">{WEEKDAY_BASE[d.getDay()][0]}<br />{d.getDate()}</th>)}
                <th>Off</th>
              </tr>
            </thead>
            <tbody>
              {deptStaff.length === 0 && <tr><td colSpan={days.length + 2} className="report-empty">No staff in {offDept}.</td></tr>}
              {deptStaff.map((p) => {
                let offCount = 0;
                const cells = days.map((d) => {
                  const on = !!roster[rk(p.name, toKey(d))];
                  if (!on) offCount++;
                  return { key: toKey(d), on };
                });
                return (
                  <tr key={p.id}>
                    <td className="off-name-col">{p.name}</td>
                    {cells.map((c) => (
                      <td key={c.key} className="off-day-col">
                        <span className={`off-dot ${c.on ? 'is-on' : 'is-off'}`} title={c.on ? 'Scheduled' : 'Off'} />
                      </td>
                    ))}
                    <td className="off-count">{offCount}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function NotificationsTab({ department, staff, templates, assignments, roster }) {
  const days = useMemo(() => Array.from({ length: 14 }, (_, i) => addDays(TODAY, i)), []);
  const deptStaff = staff.filter((s) => s.department === department && !s.archived);

  const alerts = useMemo(() => {
    const out = [];
    days.forEach((d) => {
      const dateKey = toKey(d);
      const label = `${WEEKDAY_BASE[d.getDay()]} ${MONTH_LABELS[d.getMonth()].slice(0, 3)} ${d.getDate()}`;
      const tplId = assignments[`${dateKey}__${department}`];
      const tpl = tplId ? templates.find((t) => t.id === tplId) : null;
      if (!tpl) { out.push({ level: 'warn', title: 'No template assigned', detail: `${label} has no ${department} template.` }); return; }
      const open = tpl.shifts.filter((sh) => !deptStaff.some((p) => { const e = roster[rk(p.name, dateKey)]; return e && e.shiftId === sh.id; }));
      if (open.length > 0) out.push({ level: 'warn', title: `${open.length} unfilled shift${open.length > 1 ? 's' : ''}`, detail: `${label} · ${tpl.name} — ${open.map((s) => s.id).join(', ')}` });
    });
    deptStaff.forEach((p) => {
      let hrs = 0;
      days.slice(0, 7).forEach((d) => { const e = roster[rk(p.name, toKey(d))]; if (e) hrs += computeEntryHours(e); });
      if (hrs > 60) out.push({ level: 'info', title: 'High scheduled hours', detail: `${p.name} is scheduled ${Math.round(hrs)} hrs over the next 7 days.` });
    });
    return out;
  }, [days, department, templates, assignments, roster, deptStaff]);

  return (
    <div className="tab-page">
      <div className="tab-page-header"><h2>Notifications</h2><span className="dash-subtitle">{department} · next 14 days</span></div>
      {alerts.length === 0 ? (
        <div className="dash-panel"><div className="dash-empty-good"><Check size={15} /> Nothing needs attention right now.</div></div>
      ) : (
        <div className="notif-list">
          {alerts.map((a, i) => (
            <div key={i} className={`notif-row is-${a.level}`}>
              <span className="notif-icon">{a.level === 'warn' ? <Bell size={14} /> : <Info size={14} />}</span>
              <div>
                <div className="notif-title">{a.title}</div>
                <div className="notif-detail">{a.detail}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Styles                                                               */
/* ------------------------------------------------------------------ */

const STYLES = `
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;600;700&display=swap');

.rosta-app, .rosta-app * { box-sizing: border-box; }

.rosta-app {
  --surface-0:#131314; --surface-1:#1e1f20; --surface-2:#28292a; --surface-3:#303134; --surface-4:#3c3d40;
  --border: rgba(255,255,255,0.09); --border-strong: rgba(255,255,255,0.16);
  --text-primary:#e8eaed; --text-secondary:#9aa0a6; --text-tertiary:#5f6368;
  --accent:#8ab4f8; --accent-hover:#aecbfa; --accent-on:#062e6f; --accent-soft-bg: rgba(138,180,248,0.16);
  --danger:#f28b82; --success:#81c995; --warning:#fdd663;
  --shadow-sm: 0 1px 2px rgba(0,0,0,.3), 0 1px 3px rgba(0,0,0,.25);
  --shadow-md: 0 4px 8px rgba(0,0,0,.35), 0 1px 3px rgba(0,0,0,.3);
  --shadow-lg: 0 8px 24px rgba(0,0,0,.45), 0 2px 6px rgba(0,0,0,.3);
  --tpl-blue-bg: rgba(138,180,248,.18); --tpl-blue-fg:#aecbfa; --tpl-blue-dot:#8ab4f8;
  --tpl-green-bg: rgba(129,201,149,.18); --tpl-green-fg:#a8dab5; --tpl-green-dot:#81c995;
  --tpl-amber-bg: rgba(253,214,99,.18); --tpl-amber-fg:#fde293; --tpl-amber-dot:#fdd663;
  --tpl-red-bg: rgba(242,139,130,.18); --tpl-red-fg:#f6aca5; --tpl-red-dot:#f28b82;
  --tpl-purple-bg: rgba(197,138,249,.18); --tpl-purple-fg:#d7aefb; --tpl-purple-dot:#c58af9;

  color-scheme: dark;
  height: 100vh; display: flex; flex-direction: column;
  background: var(--surface-0); color: var(--text-primary);
  font-family: 'Inter', 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
  font-size: 14px; overflow: hidden;
  -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}
/* Tabular figures everywhere numbers must line up in columns */
.roster-hrs-cell, .roster-total-cell, .roster-schedule-cell, .roster-id-cell,
.gantt-cell, .dash-stat-value, .dash-util-hours, .off-count, .day-number,
.timeline-ruler-label, .report-table td.is-num, .print-grid-table td,
.roster-shift-badge, .scroll-wheel-row, .day-grid-slot-head {
  font-variant-numeric: tabular-nums; font-feature-settings: 'tnum' 1;
}
.rosta-app button { font-family: inherit; cursor: pointer; background: none; border: none; color: inherit; }
.rosta-app button:disabled { cursor: not-allowed; opacity: .55; }
.rosta-app input, .rosta-app select, .rosta-app textarea { font-family: inherit; }
.rosta-app fieldset { border: none; padding: 0; margin: 0; }

.rosta-app *::-webkit-scrollbar { width: 10px; height: 10px; }
.rosta-app *::-webkit-scrollbar-track { background: transparent; }
.rosta-app *::-webkit-scrollbar-thumb { background: var(--surface-4); border-radius: 8px; border: 2px solid transparent; background-clip: content-box; }
.rosta-app button:focus-visible, .rosta-app input:focus-visible, .rosta-app select:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 4px; }
@media (prefers-reduced-motion: reduce) { .rosta-app * { transition-duration: 0.01ms !important; animation-duration: 0.01ms !important; } }

/* ---------- Top bar ---------- */
.top-bar { display: flex; align-items: center; gap: 24px; height: 56px; flex-shrink: 0; padding: 0 16px; background: var(--surface-2); border-bottom: 1px solid var(--border); }
.top-bar-simple { justify-content: flex-start; }
.top-bar-title { font-size: 16px; font-weight: 600; }
.top-bar-left, .top-bar-right { display: flex; align-items: center; }
.top-bar-center { display: flex; align-items: center; gap: 14px; }
.top-bar-right { margin-left: auto; }

.dept-dropdown { position: relative; }
.dept-trigger { display: flex; align-items: center; gap: 8px; justify-content: space-between; background: var(--surface-3); border: 1px solid var(--border); padding: 8px 12px; border-radius: 8px; min-width: 150px; font-size: 13px; font-weight: 500; color: var(--text-primary); transition: background var(--dur-fast) var(--ease), border-color var(--dur-fast) var(--ease); }
.dept-trigger:hover { background: var(--surface-4); border-color: var(--border-strong); }
.dept-trigger-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dept-chevron { color: var(--text-secondary); transition: transform var(--dur-fast) var(--ease); flex-shrink: 0; }
.dept-chevron.is-open { transform: rotate(180deg); }
.dept-menu { position: absolute; top: calc(100% + 6px); left: 0; min-width: 190px; z-index: 100; background: var(--surface-3); border: 1px solid var(--border-strong); border-radius: 12px; box-shadow: var(--shadow-lg); padding: 6px; display: flex; flex-direction: column; gap: 2px; max-height: 260px; overflow-y: auto; }
.dept-option { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 8px 10px; border-radius: 8px; font-size: 13px; text-align: left; color: var(--text-primary); }
.dept-option:hover { background: var(--surface-4); }
.dept-option.is-selected { color: var(--accent); }
.week-start-trigger { display: flex; align-items: center; gap: 6px; background: var(--surface-3); border: 1px solid var(--border); padding: 7px 10px; border-radius: 8px; font-size: 12px; font-weight: 500; color: var(--text-secondary); }
.week-start-trigger:hover { background: var(--surface-4); }

.scale-selector { position: relative; display: grid; grid-template-columns: repeat(5, 1fr); width: 240px; padding-top: 2px; }
.scale-track { position: absolute; top: 9px; left: 10%; right: 10%; height: 2px; background: var(--border-strong); border-radius: 4px; }
.scale-track-fill { position: absolute; top: 9px; left: 10%; height: 2px; background: var(--accent); border-radius: 4px; transition: width var(--dur-med) var(--ease); }
.scale-point-wrap { position: relative; z-index: 1; display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 0; }
.scale-point { width: 8px; height: 8px; border-radius: 50%; background: var(--text-tertiary); box-shadow: 0 0 0 4px var(--surface-2); transition: all var(--dur-med) var(--ease); }
.scale-point-wrap.is-active .scale-point { width: 12px; height: 12px; background: var(--accent); box-shadow: 0 0 0 4px var(--surface-2), 0 0 0 6px var(--accent-soft-bg); }
.scale-label { font-size: 10px; font-weight: 500; letter-spacing: .02em; white-space: nowrap; color: var(--text-tertiary); transition: color var(--dur-med) var(--ease); }
.scale-point-wrap.is-active .scale-label { color: var(--accent); }

.period-nav { display: flex; align-items: center; gap: 2px; }
.nav-arrow-btn { width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; border-radius: 50%; color: var(--text-secondary); transition: background var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease); }
.nav-arrow-btn:hover:not(:disabled) { background: var(--surface-3); color: var(--text-primary); }
.period-label { font-size: 13px; font-weight: 500; min-width: 140px; text-align: center; white-space: nowrap; }

.date-box-wrap { position: relative; }
.date-box { display: flex; align-items: center; gap: 7px; background: var(--surface-3); border: 1px solid var(--border); padding: 7px 12px; border-radius: 8px; font-size: 13px; font-weight: 500; color: var(--text-primary); }
.date-box:hover { background: var(--surface-4); border-color: var(--border-strong); }
.date-picker-popover { position: absolute; top: calc(100% + 6px); left: 50%; transform: translateX(-50%); width: 264px; z-index: 100; background: var(--surface-3); border: 1px solid var(--border-strong); border-radius: 12px; box-shadow: var(--shadow-lg); padding: 12px; }
.picker-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.picker-title { font-size: 13px; font-weight: 600; }
.picker-nav-btn { width: 26px; height: 26px; display: flex; align-items: center; justify-content: center; border-radius: 50%; color: var(--text-secondary); }
.picker-nav-btn:hover { background: var(--surface-4); color: var(--text-primary); }
.picker-weekdays { display: grid; grid-template-columns: repeat(7, 1fr); margin-bottom: 4px; }
.picker-weekdays span { text-align: center; font-size: 10px; color: var(--text-tertiary); font-weight: 600; }
.picker-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }
.picker-day { aspect-ratio: 1; display: flex; align-items: center; justify-content: center; border-radius: 50%; font-size: 12px; color: var(--text-primary); }
.picker-day:hover { background: var(--surface-4); }
.picker-day.is-muted { color: var(--text-tertiary); }
.picker-day.is-today { color: var(--accent); font-weight: 700; }
.picker-day.is-selected { background: var(--accent); color: var(--accent-on); font-weight: 700; }
.picker-day.is-in-range { background: var(--accent-soft-bg); border-radius: 0; }
.picker-hint { margin-top: 8px; font-size: 11px; color: var(--text-secondary); text-align: center; }

.publish-btn, .cta-btn { display: flex; align-items: center; gap: 6px; background: var(--cta); color: var(--cta-on); padding: 8px 20px; border-radius: 999px; font-size: 13px; font-weight: 600; box-shadow: var(--shadow-sm); }
.publish-btn:hover, .cta-btn:hover { background: var(--cta-hover); box-shadow: var(--shadow-md); }
.publish-btn:active, .cta-btn:active { transform: scale(.97); }

/* ---------- App body / sidebar ---------- */
.app-body { flex: 1; display: flex; min-height: 0; }
.sidebar { width: 64px; flex-shrink: 0; background: var(--surface-1); border-right: 1px solid var(--border); display: flex; flex-direction: column; transition: width var(--dur-med) var(--ease); overflow: hidden; }
.sidebar.is-expanded { width: 226px; }
.sidebar-top { display: flex; padding: 12px; }
.sidebar-toggle { width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; border-radius: 50%; color: var(--text-secondary); flex-shrink: 0; }
.sidebar-toggle:hover { background: var(--surface-3); color: var(--text-primary); }
.sidebar-nav { display: flex; flex-direction: column; gap: 2px; padding: 4px 12px; overflow-y: auto; }
.sidebar-item { display: flex; align-items: center; gap: 16px; height: 42px; padding: 0 10px; border-radius: 999px; font-size: 13px; font-weight: 500; white-space: nowrap; color: var(--text-secondary); flex-shrink: 0; }
.sidebar-item:hover { background: var(--surface-3); color: var(--text-primary); }
.sidebar-item.is-active { background: var(--accent-soft-bg); color: var(--accent); }
.sidebar-item-icon { display: flex; align-items: center; justify-content: center; flex-shrink: 0; width: 20px; }
.sidebar-item-label { opacity: 0; max-width: 0; overflow: hidden; transition: opacity var(--dur-fast) var(--ease), max-width var(--dur-med) var(--ease); }
.sidebar.is-expanded .sidebar-item-label { opacity: 1; max-width: 160px; }
.sidebar-bottom-group { margin-top: auto; display: flex; flex-direction: column; border-top: 1px solid var(--border); padding-top: 4px; flex-shrink: 0; }
.sidebar-profile-wrap { padding: 8px 12px 12px; }
.profile-menu-wrap { position: relative; }
.profile-trigger { display: flex; align-items: center; gap: 10px; width: 100%; padding: 6px; border-radius: 999px; }
.profile-trigger:hover { background: var(--surface-3); }
.profile-avatar { width: 30px; height: 30px; border-radius: 50%; background: var(--accent-soft-bg); color: var(--accent); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.profile-info { display: flex; flex-direction: column; align-items: flex-start; min-width: 0; opacity: 0; max-width: 0; overflow: hidden; transition: opacity var(--dur-fast) var(--ease), max-width var(--dur-med) var(--ease); }
.sidebar.is-expanded .profile-info { opacity: 1; max-width: 160px; }
.profile-workspace { font-size: 12px; font-weight: 600; color: var(--text-primary); white-space: nowrap; }
.profile-email { font-size: 11px; color: var(--text-tertiary); white-space: nowrap; }
.profile-popover { position: absolute; bottom: calc(100% + 6px); left: 0; width: 230px; z-index: 100; background: var(--surface-3); border: 1px solid var(--border-strong); border-radius: 12px; box-shadow: var(--shadow-lg); padding: 8px; max-height: 70vh; overflow-y: auto; }
.profile-popover-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; color: var(--text-tertiary); padding: 6px 8px 4px; }
.profile-ws-option { display: flex; align-items: center; justify-content: space-between; width: 100%; padding: 8px; border-radius: 8px; font-size: 13px; color: var(--text-primary); }
.profile-ws-option:hover { background: var(--surface-4); }
.profile-ws-option.is-selected { color: var(--accent); }
.profile-popover-divider { height: 1px; background: var(--border); margin: 6px 2px; }
.profile-login-btn { width: 100%; text-align: left; padding: 8px; border-radius: 8px; font-size: 13px; color: var(--text-secondary); }
.profile-login-btn:hover { background: var(--surface-4); color: var(--text-primary); }

/* ---------- Calendar area ---------- */
.calendar-area { flex: 1; min-width: 0; overflow: auto; background: var(--surface-1); display: flex; flex-direction: column; }
.calendar-area-inner { flex: 1; display: flex; flex-direction: column; padding: 16px; min-height: 0; }
.month-grid-wrap { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.weekday-row { display: grid; grid-template-columns: 24px repeat(7, 1fr); flex-shrink: 0; padding-bottom: 8px; }
.weekday-label { text-align: center; font-size: 11px; font-weight: 600; letter-spacing: .03em; color: var(--text-secondary); text-transform: uppercase; padding-bottom: 6px; }
.weekday-label-spacer { display: block; }
.month-grid { flex: 1; min-height: 0; display: grid; grid-template-columns: 24px repeat(7, 1fr); grid-template-rows: repeat(6, 1fr); gap: 1px; background: var(--border); }
.month-grid > .day-cell:nth-child(2) { border-top-left-radius: 10px; }
.month-grid > .day-cell:nth-child(8) { border-top-right-radius: 10px; }
.month-grid > .day-cell:nth-child(42) { border-bottom-left-radius: 10px; }
.month-grid > .day-cell:nth-child(48) { border-bottom-right-radius: 10px; }
.month-week-num { width: 16px; height: 16px; border-radius: 50%; background: var(--text-tertiary); color: var(--surface-1); font-size: 10px; font-weight: 700; display: flex; align-items: center; justify-content: center; justify-self: center; transition: all var(--dur-fast) var(--ease); }
.month-week-num:hover { background: var(--accent); color: var(--accent-on); transform: scale(1.15); }
.day-cell { position: relative; background: var(--surface-1); padding: 6px; display: flex; flex-direction: column; gap: 4px; min-width: 0; min-height: 0; transition: background var(--dur-fast) var(--ease); }
.day-cell:hover { background: var(--surface-2); }
.day-cell.is-muted { color: var(--text-tertiary); }
.day-cell.is-muted .day-number { color: var(--text-tertiary); }
.day-cell.is-drag-over { background: var(--accent-soft-bg); outline: 1.5px dashed var(--accent); outline-offset: -2px; }
.day-cell.is-editing { z-index: 50; }
.day-cell-header { display: flex; align-items: center; justify-content: space-between; flex-shrink: 0; }
.day-number { width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 500; border-radius: 50%; color: var(--text-secondary); }
.day-number:hover { background: var(--surface-3); color: var(--text-primary); }
.day-number.is-today { background: var(--accent); color: var(--accent-on); font-weight: 700; }
.day-number.is-today:hover { background: var(--accent-hover); }
.day-number.large { width: 52px; height: 52px; font-size: 24px; flex-shrink: 0; }
.day-add-btn-subtle { flex: 1; display: flex; align-items: center; justify-content: center; }
.day-add-btn-subtle-inner { width: 26px; height: 26px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: var(--text-tertiary); opacity: 0; transition: opacity var(--dur-fast) var(--ease), background var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease), transform var(--dur-fast) var(--ease); }
.day-cell:hover .day-add-btn-subtle-inner { opacity: 1; }
.day-add-btn-subtle:hover .day-add-btn-subtle-inner { background: var(--accent-soft-bg); color: var(--accent); transform: scale(1.1); }

.template-chip { position: relative; display: flex; flex-direction: column; gap: 2px; padding: 6px 7px; border-radius: 8px; font-size: 11px; cursor: grab; flex: 1; min-height: 0; overflow: hidden; }
.template-chip:active { cursor: grabbing; }
.template-card-header { display: flex; align-items: center; gap: 5px; }
.template-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.template-card-title { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 600; font-size: 12px; }
.template-actions { display: flex; align-items: center; gap: 9px; opacity: 0; transition: opacity var(--dur-fast) var(--ease); flex-shrink: 0; }
.template-chip:hover .template-actions, .template-chip:focus-within .template-actions { opacity: 1; }
.template-actions-bottom { margin-top: auto; padding-top: 4px; justify-content: flex-end; }
.tpl-icon-btn { width: 17px; height: 17px; display: flex; align-items: center; justify-content: center; border-radius: 4px; opacity: .85; }
.tpl-icon-btn:hover { background: rgba(255,255,255,0.14); opacity: 1; }
.tpl-icon-btn-danger:hover { background: var(--danger-soft-bg); color: var(--danger); }
.tpl-drag { cursor: grab; opacity: .6; }
.template-card-line { font-size: 10px; line-height: 1.4; opacity: .82; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding-left: 11px; }
.tpl-blue { background: var(--tpl-blue-bg); color: var(--tpl-blue-fg); }
.tpl-blue .template-dot { background: var(--tpl-blue-dot); }
.tpl-green { background: var(--tpl-green-bg); color: var(--tpl-green-fg); }
.tpl-green .template-dot { background: var(--tpl-green-dot); }
.tpl-amber { background: var(--tpl-amber-bg); color: var(--tpl-amber-fg); }
.tpl-amber .template-dot { background: var(--tpl-amber-dot); }
.tpl-red { background: var(--tpl-red-bg); color: var(--tpl-red-fg); }
.tpl-red .template-dot { background: var(--tpl-red-dot); }
.tpl-purple { background: var(--tpl-purple-bg); color: var(--tpl-purple-fg); }
.tpl-purple .template-dot { background: var(--tpl-purple-dot); }
.template-chip.large { padding: 12px 14px; gap: 5px; border-radius: 12px; }
.template-chip.large .template-card-title { font-size: 14px; }
.template-chip.large .template-card-line { font-size: 12px; padding-left: 14px; }

/* Popovers shared by template / shift pickers */
.template-picker-popover { position: absolute; top: 30px; left: 0; width: 240px; z-index: 100; background: var(--surface-3); border: 1px solid var(--border-strong); border-radius: 12px; box-shadow: var(--shadow-lg); padding: 8px; }
.picker-popover-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; color: var(--text-tertiary); padding: 4px 6px 6px; }
.template-picker-list { display: flex; flex-direction: column; gap: 2px; max-height: 220px; overflow-y: auto; }
.template-picker-option { display: flex; align-items: center; gap: 8px; padding: 8px; border-radius: 8px; font-size: 13px; color: var(--text-primary); text-align: left; }
.template-picker-option:hover { background: var(--surface-4); }
.template-picker-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.template-picker-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.template-picker-empty { padding: 10px 6px; font-size: 12px; color: var(--text-tertiary); }
.template-picker-create { display: flex; align-items: center; gap: 6px; width: 100%; margin-top: 6px; padding: 8px; border-radius: 8px; border-top: 1px solid var(--border); font-size: 13px; font-weight: 600; color: var(--accent); }
.template-picker-create:hover { background: var(--accent-soft-bg); }

/* Quick edit popover (used for shift color etc.) */
.quick-edit-input { background: var(--surface-1); border: 1px solid var(--border); border-radius: 8px; padding: 7px 9px; font-size: 12px; color: var(--text-primary); width: 100%; }
.quick-edit-input:focus { border-color: var(--accent); outline: none; }
.quick-edit-input:disabled { opacity: .6; }
.quick-color-dot { width: 18px; height: 18px; border-radius: 50%; border: 2px solid transparent; flex-shrink: 0; }
.quick-color-dot.tpl-blue { background: var(--tpl-blue-dot); }
.quick-color-dot.tpl-green { background: var(--tpl-green-dot); }
.quick-color-dot.tpl-amber { background: var(--tpl-amber-dot); }
.quick-color-dot.tpl-red { background: var(--tpl-red-dot); }
.quick-color-dot.tpl-purple { background: var(--tpl-purple-dot); }
.quick-color-dot.is-selected { border-color: var(--text-primary); color: rgba(0,0,0,.75); }
.quick-edit-save { background: var(--cta); color: var(--cta-on); padding: 6px 14px; border-radius: 16px; font-size: 12px; font-weight: 600; margin-left: auto; }
.quick-edit-save:hover { background: var(--cta-hover); }

/* Modal (Template editor / Staff editor) */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.55); display: flex; align-items: center; justify-content: center; z-index: 300; padding: 24px; }
.modal-panel { background: var(--surface-2); border: 1px solid var(--border-strong); border-radius: 16px; box-shadow: var(--shadow-lg); width: 100%; max-width: 520px; max-height: 88vh; display: flex; flex-direction: column; overflow: hidden; }
.template-editor-panel { max-width: 680px; }
.modal-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid var(--border); flex-shrink: 0; }
.modal-header h3 { font-size: 16px; font-weight: 600; }
.modal-close-btn { width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; border-radius: 50%; color: var(--text-secondary); }
.modal-close-btn:hover { background: var(--surface-3); color: var(--text-primary); }
.modal-body { padding: 16px 20px; overflow-y: auto; flex: 1; display: flex; flex-direction: column; gap: 14px; }
.modal-footer { display: flex; align-items: center; justify-content: flex-end; gap: 10px; padding: 14px 20px; border-top: 1px solid var(--border); flex-shrink: 0; }
.modal-cancel-btn { padding: 8px 16px; border-radius: 16px; font-size: 13px; font-weight: 600; color: var(--text-secondary); }
.modal-cancel-btn:hover { background: var(--surface-3); color: var(--text-primary); }
.modal-save-btn { margin-left: 0 !important; }
.template-editor-fieldset { display: flex; flex-direction: column; gap: 14px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.form-row label, .form-row-full { display: flex; flex-direction: column; gap: 5px; font-size: 12px; font-weight: 600; color: var(--text-secondary); }
.form-row-full { width: 100%; }
.template-comments-textarea { resize: vertical; font-family: inherit; }

/* Shift editor (inside Template editor) */
.shift-editor-section { border-top: 1px solid var(--border); padding-top: 12px; }
.shift-editor-section-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.shift-editor-section-head h4 { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.shift-editor-hint { font-size: 11px; font-weight: 400; color: var(--text-tertiary); }
.shift-badge-row { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.shift-badge-icon { width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; color: rgba(0,0,0,.75); border: 2px solid transparent; }
.shift-badge-icon:hover { transform: translateY(-1px); }
.shift-badge-icon.is-active { border-color: var(--text-primary); }
.shift-badge-add { background: var(--surface-3); border: 1.5px dashed var(--border-strong); color: var(--text-secondary); filter: none; }
.shift-badge-add:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-soft-bg); }
.shift-editor-row { position: relative; margin-top: 14px; background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 14px; display: flex; flex-direction: column; gap: 12px; }
.shift-editor-row-top { position: absolute; top: 10px; right: 10px; display: flex; align-items: center; gap: 10px; }
.shift-field-label { display: flex; flex-direction: column; gap: 5px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .02em; color: var(--text-secondary); }
.shift-id-field { max-width: 140px; }
.shift-color-dots { display: flex; gap: 6px; }
.shift-ranges-block { display: flex; flex-direction: column; gap: 8px; padding: 10px; background: var(--surface-2); border-radius: 8px; }
.shift-range-row { display: flex; align-items: center; gap: 8px; }
.shift-range-index { width: 18px; height: 18px; border-radius: 50%; background: var(--surface-4); display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; color: var(--text-secondary); flex-shrink: 0; }
.time-picker-field { position: relative; }
.time-picker-trigger { display: flex; align-items: center; gap: 5px; background: var(--surface-3); border: 1px solid var(--border); border-radius: 8px; padding: 6px 9px; font-size: 12px; font-weight: 600; color: var(--text-primary); }
.time-picker-trigger:hover { background: var(--surface-4); }
.shift-time-sep { color: var(--text-tertiary); }
.shift-range-add { align-self: flex-start; display: flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 600; color: var(--accent); padding: 4px 8px; border-radius: 8px; }
.shift-range-add:hover { background: var(--accent-soft-bg); }
.shift-editor-row-footer { display: flex; justify-content: flex-end; padding-top: 4px; border-top: 1px solid var(--border); }
.shift-save-btn { padding: 7px 18px !important; }

/* Timeline (shared: Day view) */
.timeline-ruler { position: relative; height: 18px; margin-bottom: 4px; border-bottom: 1px solid var(--border); }
.timeline-ruler-mark { position: absolute; top: 0; bottom: 0; display: flex; align-items: flex-start; border-left: 1px solid var(--border); padding-left: 3px; }
.timeline-ruler-label { font-size: 10px; color: var(--text-tertiary); white-space: nowrap; }
.timeline-track { position: relative; height: 30px; background: var(--surface-0); border-radius: 8px; border: 1px solid var(--border); }
.timeline-bar { position: absolute; z-index: 1; top: 3px; bottom: 3px; border-radius: 8px; display: flex; align-items: center; gap: 4px; padding: 0 8px; font-size: 11px; font-weight: 600; cursor: grab; touch-action: none; user-select: none; overflow: hidden; }
.timeline-bar:active { cursor: grabbing; }
.timeline-bar-ghost { position: absolute; z-index: 1; top: 6px; bottom: 6px; border-radius: 8px; border: 1.5px dashed var(--border-strong); background: transparent; }
.timeline-bar-label { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; pointer-events: none; }
.timeline-handle { position: absolute; top: 0; bottom: 0; width: 8px; cursor: ew-resize; touch-action: none; }
.timeline-handle-start { left: 0; }
.timeline-handle-end { right: 0; }
.timeline-bar-remove { flex-shrink: 0; width: 14px; height: 14px; display: flex; align-items: center; justify-content: center; border-radius: 50%; background: rgba(0,0,0,.25); }
.timeline-bar-remove:hover { background: rgba(0,0,0,.45); }

/* Day view */
.day-view-wrap { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.day-view-toolbar { display: flex; align-items: center; gap: 20px; padding-bottom: 14px; margin-bottom: 14px; border-bottom: 1px solid var(--border); flex-shrink: 0; }
.day-view-header { display: flex; align-items: center; gap: 14px; flex-shrink: 0; }
.day-view-weekday { font-size: 16px; font-weight: 600; }
.day-view-month { font-size: 12px; color: var(--text-secondary); }
.day-view-timestep { position: relative; display: flex; align-items: center; gap: 8px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .02em; color: var(--text-secondary); flex-shrink: 0; }
.day-view-timestep-label { white-space: nowrap; }
.day-view-timestep-trigger { background: var(--surface-3); border: 1px solid var(--border); border-radius: 8px; padding: 6px 10px; font-size: 12px; font-weight: 600; color: var(--text-primary); text-transform: none; letter-spacing: normal; }
.day-view-timestep-trigger:hover { background: var(--surface-4); }
.time-scroller-popover { position: absolute; top: calc(100% + 6px); right: 0; z-index: 100; background: var(--surface-3); border: 1px solid var(--border-strong); border-radius: 12px; box-shadow: var(--shadow-lg); padding: 10px 14px; }
.time-scroller { display: flex; align-items: center; gap: 4px; }
.time-scroller-sep { font-size: 16px; font-weight: 700; color: var(--text-secondary); }
.time-scroller-unit { font-size: 11px; color: var(--text-tertiary); margin-right: 4px; }
.scroll-wheel-col { position: relative; width: 34px; }
.scroll-wheel-highlight { position: absolute; top: 50%; left: -4px; right: -4px; transform: translateY(-50%); background: var(--accent-soft-bg); border-radius: 8px; pointer-events: none; }
.scroll-wheel-viewport { position: relative; overflow-y: scroll; scroll-snap-type: y mandatory; scrollbar-width: none; cursor: grab; touch-action: none; user-select: none; }
.scroll-wheel-viewport:active { cursor: grabbing; }
.scroll-wheel-viewport::-webkit-scrollbar { display: none; }
.scroll-wheel-row { scroll-snap-align: center; display: flex; align-items: center; justify-content: center; font-size: 13px; color: var(--text-tertiary); font-variant-numeric: tabular-nums; }
.scroll-wheel-row.is-selected { color: var(--text-primary); font-weight: 700; }
.day-view-body { position: relative; min-height: 64px; }
.day-view-empty { display: flex; align-items: center; gap: 8px; width: 100%; border: 1.5px dashed var(--border-strong); border-radius: 12px; padding: 14px; color: var(--text-secondary); font-size: 13px; justify-content: center; }
.day-view-empty:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-soft-bg); }
.day-view-empty-static { padding: 14px; text-align: center; color: var(--text-tertiary); font-size: 13px; border: 1.5px dashed var(--border); border-radius: 12px; }
.day-view-tplinline { position: relative; display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; padding-left: 16px; border-left: 1px solid var(--border); }
.day-view-tplbar-name { font-size: 14px; font-weight: 700; flex-shrink: 0; }
.day-view-tplbar-comments { font-size: 12px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.day-view-tplbar-actions { display: inline-flex; align-items: center; gap: 4px; margin-left: auto; flex-shrink: 0; }
.day-view-tplbar-actions .roster-day-edit-btn { opacity: 1; }
.day-view-gantt-wrap { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.day-view-gantt-scroll { flex: 1; overflow: auto; min-height: 0; border: 1px solid var(--border); border-radius: 12px; }
.day-view-gantt-grid { display: grid; }
.gantt-shift-cell { position: relative; }
.gantt-shift-cell.is-drag-over { background: var(--accent-soft-bg); }
.gantt-shift-cell .roster-shift-badge { cursor: grab; }
.gantt-shift-cell .roster-shift-badge.is-active { outline: 2px solid var(--text-primary); outline-offset: 1px; }
.shift-edit-popover { position: absolute; top: 34px; left: 0; z-index: 100; width: 300px; max-height: 75vh; overflow-y: auto; box-shadow: var(--shadow-lg); border-radius: 12px; }
.shift-range-hrs { font-size: 11px; font-weight: 600; color: var(--text-secondary); white-space: nowrap; }
.gantt-head-cell { position: sticky; top: 0; z-index: 2; background: var(--surface-2); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .02em; color: var(--text-secondary); }
.gantt-head-left { justify-content: flex-start; padding-left: 10px; }
.gantt-ruler-cell { position: sticky; top: 0; z-index: 2; background: var(--surface-2); border-bottom: 1px solid var(--border); border-left: 1px solid var(--border); }
.gantt-cell { border-top: 1px solid var(--border); display: flex; align-items: center; justify-content: center; font-size: 12px; color: var(--text-primary); background: var(--surface-1); }
.gantt-cell-left { justify-content: flex-start; padding-left: 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.gantt-unassigned { color: var(--text-tertiary); font-style: italic; font-size: 12px; }
.gantt-bar-cell { position: relative; border-top: 1px solid var(--border); border-left: 1px solid var(--border); background: var(--surface-1); }
.gantt-bar-cell.is-editing { z-index: 50; }
.gantt-name-cell { position: relative; gap: 4px; }
.gantt-name-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.gantt-name-remove { flex-shrink: 0; width: 16px; height: 16px; display: flex; align-items: center; justify-content: center; border-radius: 50%; color: var(--text-tertiary); opacity: 0; transition: opacity var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease); }
.gantt-name-cell:hover .gantt-name-remove { opacity: 1; }
.gantt-name-remove:hover { color: var(--danger); }
.gantt-name-add { display: flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 600; color: var(--accent); padding: 3px 6px; border-radius: 8px; margin-left: -6px; }
.gantt-name-add:hover { background: var(--accent-soft-bg); }

/* Year view */
.year-grid { flex: 1; overflow-y: auto; display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; padding: 4px; align-content: start; }
.mini-month { background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px; padding: 12px; }
.mini-month-header { position: relative; display: flex; align-items: center; margin-bottom: 8px; height: 16px; }
.mini-month-header::before { content: ''; position: absolute; left: 0; right: 0; top: 50%; height: 1px; background: var(--border-strong); }
.mini-month-title-btn { position: relative; z-index: 1; background: var(--surface-2); padding-right: 8px; font-size: 12px; font-weight: 600; color: var(--text-primary); border-radius: 4px; }
.mini-month-title-btn:hover { color: var(--accent); }
.mini-weekday-row { display: grid; grid-template-columns: 13px repeat(7, 1fr); margin-bottom: 4px; }
.mini-weekday-row span { text-align: center; font-size: 10px; color: var(--text-tertiary); }
.mini-grid { display: grid; grid-template-columns: 13px repeat(7, 1fr); gap: 2px; align-items: center; }
.mini-week-num { width: 11px; height: 11px; border-radius: 50%; background: var(--text-tertiary); color: var(--surface-1); font-size: 10px; font-weight: 700; display: flex; align-items: center; justify-content: center; justify-self: center; transition: all var(--dur-fast) var(--ease); }
.mini-week-num:hover { background: var(--accent); color: var(--accent-on); transform: scale(1.15); }
.mini-day { width: 100%; aspect-ratio: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; font-size: 10px; color: var(--text-secondary); border-radius: 8px; position: relative; }
.mini-day:not(:disabled):hover { background: var(--surface-3); }
.mini-day.is-muted { color: var(--text-tertiary); opacity: .4; }
.mini-day.is-today .mini-day-num { background: var(--accent); color: var(--accent-on); font-weight: 700; border-radius: 50%; width: 15px; height: 15px; display: flex; align-items: center; justify-content: center; }
.mini-day-bar { width: 65%; height: 2.5px; border-radius: 4px; }

/* Custom view empty state / placeholders */
.custom-view { flex: 1; display: flex; align-items: center; justify-content: center; }
.custom-view-card { text-align: center; max-width: 340px; color: var(--text-secondary); }
.custom-view-card svg { color: var(--text-tertiary); margin-bottom: 10px; }
.custom-view-card h3 { font-size: 16px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px; }
.custom-view-card p { font-size: 13px; line-height: 1.5; }

/* Roster grid (Week & Custom) — spreadsheet-style table */
.roster-wrap { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.roster-scroll { flex: 1; overflow: auto; min-height: 0; border: 1px solid var(--border); border-radius: 12px; }
.roster-grid { display: grid; }

.roster-name-header { position: sticky; top: 0; z-index: 4; background: var(--surface-2); border-bottom: 1px solid var(--border); border-right: 1px solid var(--border); display: flex; align-items: center; padding: 0 12px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; color: var(--text-tertiary); }
.roster-id-header, .roster-id-cell { justify-content: center; text-align: center; }

.roster-day-info { position: sticky; top: 0; z-index: 2; grid-row: 1; background: var(--surface-2); border-bottom: 1px solid var(--border); border-left: 1px solid var(--border); display: flex; flex-direction: column; justify-content: center; gap: 1px; padding: 4px 10px; }
.roster-day-info.is-today { background: var(--accent-soft-bg); }
.roster-day-date { font-size: 10px; font-weight: 600; color: var(--text-secondary); white-space: nowrap; }
.roster-day-tplname { font-size: 13px; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.roster-day-tplname.is-empty { color: var(--text-tertiary); font-weight: 400; }
.roster-day-tplcomments { font-size: 10px; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.roster-day-assign-btn { align-self: flex-start; display: flex; align-items: center; gap: 4px; font-size: 11px; font-weight: 600; color: var(--accent); padding: 3px 6px; border-radius: 8px; margin-left: -6px; }
.roster-day-assign-btn:hover { background: var(--accent-soft-bg); }

.roster-subcol-group { position: sticky; top: 70px; z-index: 2; grid-row: 2; display: grid; background: var(--surface-2); border-bottom: 1px solid var(--border); border-left: 1px solid var(--border); }
.roster-subcol-group span { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .03em; color: var(--text-tertiary); text-align: center; align-self: center; padding: 4px 0; }

.roster-total-header { position: sticky; top: 0; right: 0; z-index: 4; grid-row: 1 / 3; background: var(--surface-2); border-bottom: 1px solid var(--border); border-left: 1px solid var(--border); display: flex; align-items: center; justify-content: center; text-align: center; font-size: 10px; font-weight: 700; color: var(--text-secondary); padding: 4px; line-height: 1.3; }

.roster-name-cell { position: sticky; z-index: 1; background: var(--surface-1); border-right: 1px solid var(--border); border-bottom: 1px solid var(--border); display: flex; align-items: center; padding: 0 12px; font-size: 13px; font-weight: 500; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; transition: background var(--dur-fast) var(--ease); }
.roster-name-cell:hover { background: var(--surface-2); }

.roster-schedule-cell { border-left: 1px solid var(--border); border-bottom: 1px solid var(--border); background: var(--surface-1); display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 2px 6px; font-size: 10px; color: var(--text-secondary); text-align: center; line-height: 1.3; gap: 1px; overflow: hidden; }
.roster-shift-cell { position: relative; border-bottom: 1px solid var(--border); background: var(--surface-1); display: flex; align-items: center; justify-content: center; }
.roster-shift-cell.is-editing { z-index: 50; }
.roster-hrs-cell { border-bottom: 1px solid var(--border); background: var(--surface-1); display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; color: var(--text-primary); }
.roster-schedule-cell:hover, .roster-shift-cell:hover, .roster-hrs-cell:hover { background: var(--surface-2); }

.roster-shift-badge { width: 26px; height: 26px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; }
.roster-shift-badge.tpl-blue, .shift-badge-icon.tpl-blue, .timeline-bar.tpl-blue { background: var(--tpl-blue-dot) !important; color: rgba(0,0,0,.75) !important; }
.roster-shift-badge.tpl-green, .shift-badge-icon.tpl-green, .timeline-bar.tpl-green { background: var(--tpl-green-dot) !important; color: rgba(0,0,0,.75) !important; }
.roster-shift-badge.tpl-amber, .shift-badge-icon.tpl-amber, .timeline-bar.tpl-amber { background: var(--tpl-amber-dot) !important; color: rgba(0,0,0,.75) !important; }
.roster-shift-badge.tpl-red, .shift-badge-icon.tpl-red, .timeline-bar.tpl-red { background: var(--tpl-red-dot) !important; color: rgba(0,0,0,.75) !important; }
.roster-shift-badge.tpl-purple, .shift-badge-icon.tpl-purple, .timeline-bar.tpl-purple { background: var(--tpl-purple-dot) !important; color: rgba(0,0,0,.75) !important; }
.roster-shift-badge-empty { background: transparent; border: 1.5px dashed var(--border-strong); color: var(--text-tertiary); opacity: 0; transition: opacity var(--dur-fast) var(--ease); filter: none; }
.roster-shift-cell:hover .roster-shift-badge-empty { opacity: 1; }
.roster-shift-badge-empty:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-soft-bg); }

.roster-total-cell { position: sticky; right: 0; background: var(--surface-1); border-left: 1px solid var(--border); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; color: var(--accent); }
.roster-empty-row { padding: 20px; text-align: center; color: var(--text-tertiary); font-size: 13px; }
.roster-remove-cell { justify-content: center; padding: 0 !important; }
.roster-minus-btn { width: 18px; height: 18px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: var(--text-tertiary); font-size: 14px; line-height: 1; opacity: 0; transition: opacity var(--dur-fast) var(--ease), background var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease); }
.roster-name-cell:hover .roster-minus-btn, .roster-remove-cell:hover .roster-minus-btn { opacity: 1; }
.roster-minus-btn:hover { background: var(--danger-soft-bg); color: var(--danger); }
.roster-add-crew-cell { position: relative; border-right: 1px solid var(--border); padding: 0 10px !important; justify-content: flex-start !important; }
.roster-plus-btn { display: flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 600; color: var(--accent); padding: 5px 10px; border-radius: 12px; }
.roster-plus-btn:hover { background: var(--accent-soft-bg); }
.add-crew-dept-field { display: flex; flex-direction: column; gap: 5px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .02em; color: var(--text-secondary); padding: 4px 4px 8px; }

/* Day view — mode toggle, working-hours shading, grid mode */
.day-view-mode-toggle { display: flex; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; flex-shrink: 0; }
.day-view-mode-toggle button { display: flex; align-items: center; gap: 5px; padding: 7px 13px; font-size: 12px; font-weight: 600; color: var(--text-secondary); }
.day-view-mode-toggle button:hover { background: var(--surface-3); }
.day-view-mode-toggle button.is-selected { background: var(--cta); color: var(--cta-on); }
.gantt-work-window { position: absolute; top: 0; bottom: 0; background: var(--accent-soft-bg); border-left: 1px solid var(--border); border-right: 1px solid var(--border); pointer-events: none; z-index: 0; }
.day-grid-table { border-collapse: separate; border-spacing: 0; font-size: 12px; width: max-content; min-width: 100%; }
.day-grid-table th, .day-grid-table td { border-right: 1px solid var(--border); border-bottom: 1px solid var(--border); padding: 0; }
.day-grid-table thead th { position: sticky; top: 0; z-index: 3; background: var(--surface-2); font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .03em; color: var(--text-secondary); padding: 8px 6px; white-space: nowrap; }
.day-grid-sticky { position: sticky; background: var(--surface-1); z-index: 2; }
.day-grid-th-shift, .day-grid-td-shift { left: 0; width: 52px; min-width: 52px; text-align: center; }
.day-grid-th-name, .day-grid-td-name { left: 52px; width: 150px; min-width: 150px; }
.day-grid-table thead .day-grid-sticky { z-index: 4; }
.day-grid-td-shift { padding: 5px !important; text-align: center; }
.day-grid-td-shift .roster-shift-badge { margin: 0 auto; }
.day-grid-td-name { padding: 5px 9px !important; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.day-grid-slot-head { min-width: 62px; }
.day-grid-cell { min-width: 62px; height: 34px; background: var(--surface-1); }
.day-grid-cell.is-working { background: var(--accent-soft-bg); }
.day-grid-input { width: 100%; height: 100%; background: none; border: none; text-align: center; font-size: 12px; font-weight: 600; color: var(--text-primary); padding: 0 4px; }
.day-grid-input:focus { outline: 2px solid var(--accent); outline-offset: -2px; border-radius: 4px; }
.day-grid-input::placeholder { color: var(--text-tertiary); font-weight: 400; }
.day-grid-readonly { display: flex; align-items: center; justify-content: center; height: 34px; font-weight: 600; }
.day-grid-empty { padding: 24px; text-align: center; color: var(--text-tertiary); }

/* Report Center */
.report-type-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.report-type-card { display: flex; flex-direction: column; gap: 4px; text-align: left; padding: 13px 14px; border-radius: 12px; background: var(--surface-2); border: 1px solid var(--border); transition: border-color var(--dur-fast) var(--ease), background var(--dur-fast) var(--ease); }
.report-type-card:hover { border-color: var(--border-strong); }
.report-type-card.is-active { border-color: var(--accent); background: var(--accent-soft-bg); }
.report-type-label { font-size: 13px; font-weight: 700; color: var(--text-primary); }
.report-type-desc { font-size: 11px; color: var(--text-secondary); line-height: 1.4; }
.report-output { flex: 1; min-height: 0; display: flex; flex-direction: column; background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
.report-output-title { font-size: 13px; font-weight: 700; padding: 14px 16px; border-bottom: 1px solid var(--border); }
.report-table-wrap { flex: 1; overflow: auto; min-height: 0; }
.report-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.report-table th { position: sticky; top: 0; background: var(--surface-3); text-align: left; padding: 9px 14px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .03em; color: var(--text-secondary); border-bottom: 1px solid var(--border); }
.report-table td { padding: 9px 14px; border-bottom: 1px solid var(--border); color: var(--text-primary); }
.report-table td.is-num { text-align: right; font-variant-numeric: tabular-nums; font-feature-settings: 'tnum'; }
.report-table th:not(:first-child) { text-align: right; }
.report-table th:first-child { text-align: left; }
.report-table tfoot td { position: sticky; bottom: 0; background: var(--surface-3); font-weight: 700; border-top: 2px solid var(--border-strong); border-bottom: none; color: var(--text-primary); }
.report-table tbody tr:hover td { background: var(--surface-3); }
.report-empty { text-align: center; color: var(--text-tertiary); padding: 24px !important; }

/* Settings — draggable chips */
.settings-hint { font-size: 12px; color: var(--text-tertiary); margin-bottom: 10px; line-height: 1.5; }
.settings-chip-empty { font-size: 12px; color: var(--text-tertiary); font-style: italic; }
.settings-chip.is-draggable { cursor: grab; }
.settings-chip.is-draggable:active { cursor: grabbing; }
.settings-chip.is-dragging { opacity: .4; }
.settings-chip.is-drag-over { box-shadow: inset 2px 0 0 var(--accent); background: var(--accent-soft-bg); }
.settings-chip-grip { color: var(--text-tertiary); flex-shrink: 0; }

/* Tab pages: Template / Team */
.tab-page { flex: 1; overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 14px; }
.tab-page-header { display: flex; align-items: center; justify-content: space-between; }
.tab-page-header h2 { font-size: 20px; font-weight: 650; letter-spacing: -0.02em; }
.dash-subtitle { font-size: 13px; color: var(--text-tertiary); }

/* Dashboard */
.dash-stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.dash-stat-card { background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px; padding: 16px 18px; display: flex; flex-direction: column; gap: 6px; transition: border-color var(--dur-fast) var(--ease), box-shadow var(--dur-fast) var(--ease); }
.dash-stat-card:hover { border-color: var(--border-strong); box-shadow: var(--shadow-sm); }
.dash-stat-card.is-primary { background: linear-gradient(160deg, var(--accent-soft-bg), var(--surface-2) 65%); }
.dash-stat-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 20px; }
.dash-stat-value { font-size: 28px; font-weight: 700; letter-spacing: -0.03em; line-height: 1.1; }
.dash-stat-unit { font-size: 16px; font-weight: 600; margin-left: 1px; opacity: .65; }
.dash-stat-value.is-good { color: var(--tpl-green-dot); }
.dash-stat-value.is-warn { color: var(--tpl-amber-dot); }
.dash-stat-label { font-size: 11px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: var(--text-secondary); }
.dash-stat-sub { font-size: 11px; color: var(--text-tertiary); }
.dash-stat-icon { color: var(--text-tertiary); display: flex; }
.dash-stat-chip { font-size: 10px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; padding: 3px 8px; border-radius: 999px; }
.dash-stat-chip.is-good { background: rgba(129,201,149,.18); color: var(--tpl-green-dot); }
.dash-stat-chip.is-warn { background: rgba(253,214,99,.18); color: var(--tpl-amber-dot); }
.dash-meter { height: 5px; border-radius: 999px; background: var(--surface-4); overflow: hidden; margin-top: 2px; }
.dash-meter-fill { height: 100%; border-radius: 999px; transition: width var(--dur-med) var(--ease); }
.dash-meter-fill.is-good { background: var(--tpl-green-dot); }
.dash-meter-fill.is-warn { background: var(--tpl-amber-dot); }
.dash-grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.dash-panel { background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px; padding: 16px; }
.dash-panel h3 { font-size: 13px; font-weight: 700; margin-bottom: 12px; }
.dash-panel-wide { grid-column: 1 / -1; }
.dash-upcoming-list, .dash-gaps-list, .dash-util-list { display: flex; flex-direction: column; gap: 8px; }
.dash-upcoming-row { display: flex; align-items: center; justify-content: space-between; font-size: 13px; padding: 7px 8px; border-radius: 8px; }
.dash-upcoming-row.is-today { background: var(--accent-soft-bg); }
.dash-upcoming-date { color: var(--text-secondary); }
.dash-upcoming-tpl { display: flex; align-items: center; gap: 6px; font-weight: 600; }
.dash-upcoming-empty { color: var(--text-tertiary); font-style: italic; }
.dash-empty-good { display: flex; align-items: center; gap: 8px; color: var(--tpl-green-dot); font-size: 13px; padding: 10px 4px; }
.dash-gap-row { display: flex; align-items: center; gap: 10px; font-size: 13px; }
.dash-gap-info { color: var(--text-secondary); }
.dash-gap-more { font-size: 12px; color: var(--text-tertiary); padding-left: 4px; }
.dash-util-row { display: grid; grid-template-columns: 130px 1fr 56px; align-items: center; gap: 12px; font-size: 13px; }
.dash-util-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dash-util-bar-track { height: 8px; border-radius: 4px; background: var(--surface-3); overflow: hidden; }
.dash-util-bar-fill { height: 100%; background: var(--cta); border-radius: 4px; }
.dash-util-hours { text-align: right; color: var(--text-secondary); font-weight: 600; }

/* Print Center */
.print-config-row { display: flex; flex-wrap: wrap; align-items: end; gap: 14px; background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px; }
.print-config-field { display: flex; flex-direction: column; gap: 5px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .02em; color: var(--text-secondary); }
.print-format-toggle { display: flex; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
.print-format-toggle button { padding: 7px 14px; font-size: 12px; font-weight: 600; text-transform: none; letter-spacing: normal; color: var(--text-secondary); }
.print-format-toggle button.is-selected { background: var(--cta); color: var(--cta-on); }
.print-preview-wrap { flex: 1; overflow: auto; background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px; padding: 24px; display: flex; justify-content: center; }
.print-preview-output { background: #fff; color: #111; width: 100%; max-width: 940px; padding: 40px 44px; border-radius: 4px; box-shadow: var(--shadow-lg); font-family: 'Inter', -apple-system, 'Segoe UI', Roboto, Arial, sans-serif; }
.print-header { margin-bottom: 26px; padding-bottom: 18px; border-bottom: 2px solid #111; }
.print-masthead { display: flex; align-items: flex-start; justify-content: space-between; gap: 32px; }
.print-eyebrow { font-size: 10px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: #6b7280; margin-bottom: 6px; }
.print-header h1 { font-size: 24px; line-height: 1.15; margin: 0 0 6px; font-weight: 700; letter-spacing: -0.01em; color: #111; }
.print-daterange { font-size: 13px; color: #4b5563; margin: 0; }
.print-meta { display: flex; gap: 26px; flex-shrink: 0; }
.print-meta div { display: flex; flex-direction: column; gap: 3px; text-align: right; }
.print-meta span { font-size: 10px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: #9ca3af; }
.print-meta strong { font-size: 13px; color: #111; font-weight: 600; }

.print-grid-table { width: 100%; border-collapse: collapse; font-size: 11px; }
.print-grid-table thead th { background: #111; color: #fff; font-weight: 600; font-size: 10px; letter-spacing: .05em; text-transform: uppercase; padding: 9px 8px; text-align: center; border: none; }
.print-grid-table thead th:first-child { text-align: left; }
.print-grid-table td { border-bottom: 1px solid #e5e7eb; padding: 8px; text-align: center; vertical-align: middle; line-height: 1.5; }
.print-grid-table tbody tr:nth-child(even) { background: #f9fafb; }
.print-grid-table tbody tr { page-break-inside: avoid; }
.print-name-cell { text-align: left !important; font-weight: 600; white-space: nowrap; color: #111; border-right: 1px solid #e5e7eb; }
.print-off { color: #d1d5db; }
.print-empty { color: #6b7280; padding: 40px 0; text-align: center; font-size: 13px; }

.print-list-view { display: flex; flex-direction: column; gap: 18px; }
.print-list-day { page-break-inside: avoid; border-left: 3px solid #111; padding-left: 14px; }
.print-list-day h3 { font-size: 13px; margin: 0 0 7px; font-weight: 700; color: #111; }
.print-list-day ul { margin: 0; padding-left: 18px; font-size: 12px; line-height: 1.8; color: #374151; }
.print-list-day li::marker { color: #9ca3af; }

.print-footer { margin-top: 32px; padding-top: 14px; border-top: 1px solid #e5e7eb; display: flex; justify-content: space-between; align-items: center; font-size: 10px; color: #9ca3af; letter-spacing: .02em; }
.print-footer-sign { color: #6b7280; }

/* Off Tracker */
.off-tracker-table th, .off-tracker-table td { text-align: center; }
.off-name-col { text-align: left !important; white-space: nowrap; position: sticky; left: 0; background: var(--surface-2); z-index: 1; }
.off-tracker-table tbody .off-name-col { background: var(--surface-2); }
.off-day-col { min-width: 34px; padding: 8px 4px !important; }
.off-dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; }
.off-dot.is-on { background: var(--tpl-green-dot); }
.off-dot.is-off { background: var(--surface-4); }
.off-count { font-weight: 700; color: var(--accent); }

/* Notifications */
.notif-list { display: flex; flex-direction: column; gap: 8px; }
.notif-row { display: flex; gap: 12px; align-items: flex-start; background: var(--surface-2); border: 1px solid var(--border); border-left-width: 3px; border-radius: 12px; padding: 12px 14px; }
.notif-row.is-warn { border-left-color: var(--tpl-amber-dot); }
.notif-row.is-info { border-left-color: var(--accent); }
.notif-icon { display: flex; align-items: center; justify-content: center; width: 26px; height: 26px; border-radius: 50%; background: var(--surface-3); color: var(--text-secondary); flex-shrink: 0; }
.notif-title { font-size: 13px; font-weight: 700; margin-bottom: 2px; }
.notif-detail { font-size: 12px; color: var(--text-secondary); }

/* Inline confirm inside pickers */
.picker-confirm { padding: 10px 12px; background: var(--danger-soft-bg); border-radius: 8px; margin: 4px; }
.picker-confirm-text { font-size: 12px; color: var(--text-primary); line-height: 1.5; margin-bottom: 10px; }
.picker-confirm-actions { display: flex; gap: 8px; justify-content: flex-end; }
.picker-confirm-cancel { font-size: 12px; font-weight: 600; padding: 6px 12px; border-radius: 8px; color: var(--text-secondary); }
.picker-confirm-cancel:hover { background: var(--surface-3); }
.picker-confirm-delete { font-size: 12px; font-weight: 600; padding: 6px 12px; border-radius: 8px; background: var(--danger); color: var(--danger-on); }
.picker-confirm-delete:hover { filter: brightness(1.1); }

/* Range truncation notice */
.range-truncated-notice { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-secondary); background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px; padding: 9px 13px; margin-bottom: 12px; flex-shrink: 0; }

@page { size: landscape; margin: 12mm 10mm; }
@media print {
  body * { visibility: hidden; }
  .print-preview-output, .print-preview-output * { visibility: visible; }
  .print-preview-output { position: absolute; top: 0; left: 0; width: 100%; max-width: none; box-shadow: none; padding: 0; border-radius: 0; }
  .no-print { display: none !important; }
  /* Repeat the header row on every printed page */
  .print-grid-table thead { display: table-header-group; }
  .print-grid-table tfoot { display: table-footer-group; }
  /* Keep backgrounds/zebra striping when printing */
  .print-preview-output, .print-grid-table thead th, .print-grid-table tbody tr:nth-child(even) {
    -webkit-print-color-adjust: exact; print-color-adjust: exact;
  }
  .print-footer { position: fixed; bottom: 0; left: 0; right: 0; }
}

/* Guide */
.guide-role-tabs { display: flex; gap: 8px; }
.guide-role-tab { display: flex; align-items: center; gap: 7px; padding: 9px 16px; border-radius: 12px; background: var(--surface-2); border: 1px solid var(--border); font-size: 13px; font-weight: 600; color: var(--text-secondary); }
.guide-role-tab.is-active { background: var(--cta); color: var(--cta-on); border-color: transparent; }
.guide-steps { display: flex; flex-direction: column; gap: 4px; }
.guide-step { display: flex; gap: 14px; padding: 14px 4px; border-bottom: 1px solid var(--border); }
.guide-step:last-child { border-bottom: none; }
.guide-step-num { flex-shrink: 0; width: 26px; height: 26px; border-radius: 50%; background: var(--accent-soft-bg); color: var(--accent); display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; }
.guide-step-title { font-size: 14px; font-weight: 700; margin-bottom: 3px; }
.guide-step-body { font-size: 13px; color: var(--text-secondary); line-height: 1.5; }

/* About */
.about-card { background: var(--surface-2); border: 1px solid var(--border); border-radius: 16px; padding: 32px; max-width: 480px; text-align: center; }
.about-logo { width: 52px; height: 52px; border-radius: 16px; background: var(--cta); color: var(--cta-on); display: flex; align-items: center; justify-content: center; margin: 0 auto 14px; }
.about-card h3 { font-size: 20px; margin-bottom: 4px; letter-spacing: -0.02em; font-weight: 650; }
.about-version { font-size: 12px; color: var(--text-tertiary); margin-bottom: 14px; }
.about-card p { font-size: 13px; color: var(--text-secondary); line-height: 1.6; }

.tab-filter-row { display: flex; align-items: center; gap: 16px; }
.tab-search { display: flex; align-items: center; gap: 8px; background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px; padding: 7px 12px; flex: 1; max-width: 320px; color: var(--text-tertiary); }
.tab-search input { flex: 1; background: none; border: none; color: var(--text-primary); font-size: 13px; }
.tab-search input:focus { outline: none; }
.tab-filter-hint { display: flex; align-items: center; gap: 5px; font-size: 11px; color: var(--text-tertiary); }
.tab-table { border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
.tab-table-row { display: grid; gap: 10px; align-items: center; padding: 10px 14px; border-bottom: 1px solid var(--border); font-size: 13px; color: var(--text-primary); }
.tab-table-row:last-child { border-bottom: none; }
.tab-table-head { background: var(--surface-2); font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .02em; color: var(--text-secondary); }
.tab-sort-btn { display: flex; align-items: center; gap: 4px; color: inherit; font: inherit; text-transform: inherit; letter-spacing: inherit; }
.tab-sort-btn:hover { color: var(--accent); }
.tab-table-name { display: flex; align-items: center; gap: 7px; font-weight: 600; }
.tab-table-comments { color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tab-table-actions, .tab-actions-head { display: flex; align-items: center; gap: 16px; }
.tab-table-empty { padding: 24px; text-align: center; color: var(--text-tertiary); font-size: 13px; }
.template-table-row { grid-template-columns: 1.5fr 2.4fr 1fr .6fr .8fr; }
.team-table-row { grid-template-columns: .9fr .9fr .7fr .9fr 1.1fr 1.6fr .5fr .7fr .7fr .5fr; }
.team-table-row.is-archived { opacity: .5; }
.team-email { display: flex; align-items: center; gap: 5px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.team-text-action { font-size: 12px; font-weight: 600; color: var(--accent); padding: 4px 8px; border-radius: 8px; }
.team-text-action:hover { background: var(--accent-soft-bg); }

/* Settings */
.settings-page { max-width: 640px; }
.settings-section { background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px; padding: 16px; display: flex; flex-direction: column; gap: 10px; }
.settings-section h3 { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 600; }
.settings-field { display: flex; flex-direction: column; gap: 5px; font-size: 12px; font-weight: 600; color: var(--text-secondary); max-width: 320px; }
.settings-hint { font-size: 12px; line-height: 1.5; color: var(--text-secondary); }
.settings-role-list { display: flex; flex-wrap: wrap; gap: 8px; }
.settings-role-btn { display: flex; align-items: center; gap: 6px; padding: 8px 14px; border-radius: 999px; background: var(--surface-3); border: 1px solid var(--border); font-size: 13px; font-weight: 600; color: var(--text-secondary); }
.settings-role-btn:hover { background: var(--surface-4); }
.settings-role-btn.is-selected { background: var(--accent-soft-bg); border-color: var(--accent); color: var(--accent); }
.settings-chip-list { display: flex; flex-wrap: wrap; gap: 8px; }
.settings-chip { display: flex; align-items: center; gap: 6px; background: var(--surface-3); padding: 6px 10px; border-radius: 16px; font-size: 12px; font-weight: 500; color: var(--text-primary); }
.settings-chip button { color: var(--text-tertiary); display: flex; }
.settings-chip button:hover { color: var(--danger); }
.settings-add-row { display: flex; align-items: center; gap: 8px; max-width: 320px; }
.settings-add-row .quick-edit-input { flex: 1; }
.settings-add-btn { background: var(--accent-soft-bg); color: var(--accent); flex-shrink: 0; width: 30px; height: 30px; }
.settings-add-btn:hover { background: var(--accent); color: var(--accent-on); }
.settings-mode-row { display: flex; gap: 8px; }
.settings-mode-btn { display: flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: 999px; background: var(--surface-3); border: 1px solid var(--border); font-size: 13px; font-weight: 600; color: var(--text-secondary); }
.settings-mode-btn:hover { background: var(--surface-4); }
.settings-mode-btn.is-selected { background: var(--accent-soft-bg); border-color: var(--accent); color: var(--accent); }
.settings-theme-row { display: flex; gap: 10px; margin-top: 4px; }
.settings-theme-swatch { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid transparent; transition: transform var(--dur-fast) var(--ease); }
.settings-theme-swatch:hover { transform: scale(1.08); }
.settings-theme-swatch.is-selected { border-color: var(--text-primary); }

/* Danger / confirm-delete */
.danger-btn { display: flex; align-items: center; gap: 6px; background: var(--danger); color: var(--danger-on); padding: 8px 16px; border-radius: 16px; font-size: 13px; font-weight: 600; }
.danger-btn:hover { filter: brightness(1.1); }
.danger-btn-ghost { display: flex; align-items: center; gap: 6px; color: var(--danger); padding: 7px 12px; border-radius: 16px; font-size: 13px; font-weight: 600; border: 1px solid var(--danger); }
.danger-btn-ghost:hover { background: var(--danger-soft-bg); }
.confirm-dialog-panel { max-width: 420px; }
.confirm-dialog-message { font-size: 13px; line-height: 1.6; color: var(--text-secondary); }

/* Template picker: edit-current entry + divider */
.template-picker-edit-current { color: var(--accent); font-weight: 600; }
.template-picker-edit-current:hover { background: var(--accent-soft-bg); }
.template-picker-remove-current { color: var(--danger); font-weight: 600; }
.template-picker-remove-current:hover { background: var(--danger-soft-bg); }
.template-picker-divider { height: 1px; background: var(--border); margin: 4px 2px 6px; }

/* Big color swatches (template full-view editor) */
.color-swatch-row { display: flex; gap: 10px; }
.color-swatch-lg { width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid transparent; color: rgba(0,0,0,.75); }
.color-swatch-lg:hover { transform: scale(1.06); }
.color-swatch-lg.is-selected { border-color: var(--text-primary); }
.color-swatch-lg.tpl-blue { background: var(--tpl-blue-dot); }
.color-swatch-lg.tpl-green { background: var(--tpl-green-dot); }
.color-swatch-lg.tpl-amber { background: var(--tpl-amber-dot); }
.color-swatch-lg.tpl-red { background: var(--tpl-red-dot); }
.color-swatch-lg.tpl-purple { background: var(--tpl-purple-dot); }

/* Roster day header: template name + edit pencil */
.roster-day-edit-btn { flex-shrink: 0; width: 18px; height: 18px; display: flex; align-items: center; justify-content: center; border-radius: 4px; color: var(--text-secondary); opacity: 0; transition: opacity var(--dur-fast) var(--ease); }
.roster-day-info:hover .roster-day-edit-btn { opacity: 1; }
.roster-day-tpl-actions { display: inline-flex; align-items: center; gap: 4px; margin-left: auto; }
.roster-day-remove-btn:hover { background: var(--danger-soft-bg); color: var(--danger); }
.roster-day-edit-btn:hover { background: var(--surface-4); color: var(--accent); }

/* Template full-view editor */
.template-full-view { height: 100%; display: flex; flex-direction: column; background: var(--surface-1); }
.template-full-topbar { display: flex; align-items: center; gap: 16px; height: 56px; flex-shrink: 0; padding: 0 20px; background: var(--surface-2); border-bottom: 1px solid var(--border); }
.template-full-back { display: flex; align-items: center; gap: 4px; font-size: 13px; font-weight: 600; color: var(--text-secondary); padding: 6px 10px 6px 4px; border-radius: 8px; }
.template-full-back:hover { background: var(--surface-3); color: var(--text-primary); }
.template-full-topbar-title { font-size: 16px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.template-full-topbar-actions { margin-left: auto; display: flex; align-items: center; gap: 14px; flex-shrink: 0; }
.template-full-body { flex: 1; overflow-y: auto; padding: 24px 28px 60px; max-width: 900px; width: 100%; margin: 0 auto; }
.template-editor-fieldset { display: flex; flex-direction: column; gap: 18px; }
.template-editor-fieldset:disabled { opacity: .6; }
.template-full-fields { display: grid; grid-template-columns: minmax(200px, 360px) minmax(160px, 240px); gap: 14px; }
.template-full-fields label { display: flex; flex-direction: column; gap: 5px; font-size: 12px; font-weight: 600; color: var(--text-secondary); }
.template-full-row2 { display: grid; grid-template-columns: 1fr auto; gap: 20px; align-items: start; }
.shift-editor-section-full { border-top: 1px solid var(--border); padding-top: 16px; }
.shift-editor-section-full .shift-editor-section-head { margin-bottom: 12px; }
.shift-editor-section-full .shift-editor-section-head h4 { font-size: 16px; }
.shift-editor-section-full .shift-editor-list { gap: 14px; }
.shift-editor-section-full .shift-editor-row { padding: 14px; }

/* Toast */
.toast { position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); background: var(--surface-4); color: var(--text-primary); padding: 12px 20px; border-radius: 12px; box-shadow: var(--shadow-lg); font-size: 13px; font-weight: 500; z-index: 200; animation: toast-in var(--dur-med) var(--ease); }
@keyframes toast-in { from { opacity: 0; transform: translateX(-50%) translateY(8px); } to { opacity: 1; transform: translateX(-50%) translateY(0); } }
`;

/* ------------------------------------------------------------------ */
/* Root app                                                              */
/* ------------------------------------------------------------------ */

export default function RostaStudioSchedule() {
  const [sidebarExpanded, setSidebarExpanded] = useState(false);
  const [activeNavItem, setActiveNavItem] = useState('schedule');
  const [department, setDepartment] = useState('Dealers');
  const [departments, setDepartments] = useState(INITIAL_DEPARTMENTS);
  const [roles, setRoles] = useState(INITIAL_ROLES);
  const [workspace, setWorkspace] = useState(WORKSPACES[0]);
  const [userRole, setUserRole] = useState('Manager');
  const [scale, setScale] = useState('Month');
  const [anchorDate, setAnchorDate] = useState(new Date(2026, 7, 5));
  const [customRange, setCustomRange] = useState({ start: addDays(TODAY, -1), end: addDays(TODAY, 3) });
  const [weekStartsOn, setWeekStartsOn] = useState(0);
  const [templates, setTemplates] = useState(TEMPLATES);
  const [assignments, setAssignments] = useState(INITIAL_ASSIGNMENTS);
  const [roster, setRoster] = useState(INITIAL_ROSTER);
  const [staff, setStaff] = useState(STAFF);
  const [pickerKey, setPickerKey] = useState(null);
  const [templateEditorState, setTemplateEditorState] = useState(null);
  const [toast, setToast] = useState(null);
  const [hiddenStaffIds, setHiddenStaffIds] = useState({});
  const [positions, setPositions] = useState(INITIAL_POSITIONS);
  const [positionCells, setPositionCells] = useState({});
  const [extraStaffIds, setExtraStaffIds] = useState({});
  const [themeMode, setThemeMode] = useState('dark');
  const [colorTheme, setColorTheme] = useState('blue');

  const canEdit = userRole !== 'Supervisor';

  useEffect(() => { setPickerKey(null); }, [scale, activeNavItem, anchorDate, department]);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 2600);
    return () => clearTimeout(t);
  }, [toast]);

  function handleStep(dir) {
    if (scale === 'Custom') setCustomRange((r) => stepCustomRange(r, dir));
    else setAnchorDate((d) => stepDate(scale, d, dir));
  }
  function handleDrillDown(newScale, date) { setScale(newScale); setAnchorDate(date); }

  function openPicker(key) { setPickerKey(key); }
  function closePicker() { setPickerKey(null); }

  function assignTemplate(dateKey, dept, templateId) {
    setAssignments((prev) => ({ ...prev, [`${dateKey}__${dept}`]: templateId }));
  }
  function unassignTemplate(dateKey, dept) {
    setAssignments((prev) => {
      const next = { ...prev };
      delete next[`${dateKey}__${dept}`];
      return next;
    });
  }
  function dropAssignment(fromKey, toDateKey, toDept, isCopy) {
    const toFull = `${toDateKey}__${toDept}`;
    if (fromKey === toFull) return;
    setAssignments((prev) => {
      if (prev[toFull]) return prev;
      const next = { ...prev };
      next[toFull] = prev[fromKey];
      if (!isCopy) delete next[fromKey];
      return next;
    });
  }
  function openTemplateEditorForNew(presetDepartment, forDateKey) {
    closePicker();
    setTemplateEditorState({
      template: null,
      presetDepartment,
      onDone: (saved) => {
        setTemplates((prev) => [...prev, saved]);
        if (forDateKey) assignTemplate(forDateKey, saved.department, saved.id);
        setTemplateEditorState(null);
      },
    });
  }
  function openTemplateEditorForEdit(template) {
    closePicker();
    setTemplateEditorState({
      template,
      onDone: (saved) => {
        saveTemplateFromTab(saved);
        setTemplateEditorState(null);
      },
    });
  }
  function saveTemplateFromTab(saved) {
    setTemplates((prev) => (prev.some((t) => t.id === saved.id) ? prev.map((t) => (t.id === saved.id ? saved : t)) : [...prev, saved]));
  }
  function deleteTemplate(id) {
    setTemplates((prev) => prev.filter((t) => t.id !== id));
    setAssignments((prev) => {
      const next = {};
      Object.entries(prev).forEach(([k, v]) => { if (v !== id) next[k] = v; });
      return next;
    });
  }
  function updateTemplateShift(templateId, shiftId, nextShift) {
    setTemplates((prev) => prev.map((t) => (t.id === templateId ? { ...t, shifts: t.shifts.map((s) => (s.id === shiftId ? nextShift : s)) } : t)));
  }
  function addTemplateShift(templateId) {
    const tpl = templates.find((t) => t.id === templateId);
    if (!tpl) return;
    const newShift = mkShift(String(tpl.shifts.length + 1), '08:00', '16:00', 'Dealer', 'blue');
    setTemplates((prev) => prev.map((t) => (t.id === templateId ? { ...t, shifts: [...t.shifts, newShift] } : t)));
    openPicker(`dayshift:${templateId}:${newShift.id}`);
  }
  function removeTemplateShift(templateId, shiftId) {
    setTemplates((prev) => prev.map((t) => (t.id === templateId ? { ...t, shifts: t.shifts.filter((s) => s.id !== shiftId) } : t)));
    closePicker();
  }
  function reorderTemplateShift(templateId, draggedShiftId, targetShiftId) {
    setTemplates((prev) => prev.map((t) => {
      if (t.id !== templateId) return t;
      const shifts = [...t.shifts];
      const fromIdx = shifts.findIndex((s) => s.id === draggedShiftId);
      const toIdx = shifts.findIndex((s) => s.id === targetShiftId);
      if (fromIdx === -1 || toIdx === -1) return t;
      const [moved] = shifts.splice(fromIdx, 1);
      shifts.splice(toIdx, 0, moved);
      return { ...t, shifts };
    }));
  }
  function createShiftAndAssign(templateId, staffName, dateKey) {
    const tpl = templates.find((t) => t.id === templateId);
    if (!tpl) return;
    const newShift = mkShift(String(tpl.shifts.length + 1), '08:00', '16:00', 'Dealer', 'blue');
    setTemplates((prev) => prev.map((t) => (t.id === templateId ? { ...t, shifts: [...t.shifts, newShift] } : t)));
    assignShift(staffName, dateKey, newShift);
    closePicker();
  }
  function hideStaffFromView(department, staffId) {
    setHiddenStaffIds((prev) => {
      const set = new Set(prev[department] || []);
      set.add(staffId);
      return { ...prev, [department]: set };
    });
  }
  function addStaffToView(department, staffId) {
    setExtraStaffIds((prev) => {
      const set = new Set(prev[department] || []);
      set.add(staffId);
      return { ...prev, [department]: set };
    });
    setHiddenStaffIds((prev) => {
      if (!prev[department] || !prev[department].has(staffId)) return prev;
      const set = new Set(prev[department]);
      set.delete(staffId);
      return { ...prev, [department]: set };
    });
    closePicker();
  }

  function assignShift(staffName, dateKey, shiftDef) {
    setRoster((prev) => ({ ...prev, [rk(staffName, dateKey)]: { shiftId: shiftDef.id, ranges: shiftDef.ranges.map((r) => ({ ...r })) } }));
  }
  function unassignShift(staffName, dateKey) {
    setRoster((prev) => {
      const next = { ...prev };
      delete next[rk(staffName, dateKey)];
      return next;
    });
  }
  function updateRosterRangeTime(staffName, dateKey, rangeIdx, start, end) {
    setRoster((prev) => {
      const existing = prev[rk(staffName, dateKey)];
      if (!existing) return prev;
      const ranges = existing.ranges.map((r, i) => (i === rangeIdx ? { start, end } : r));
      return { ...prev, [rk(staffName, dateKey)]: { ...existing, ranges } };
    });
  }

  function handleSaveStaff(saved, isNew) {
    setStaff((prev) => (isNew ? [...prev, saved] : prev.map((s) => (s.id === saved.id ? saved : s))));
  }
  function handleArchiveStaff(id) { setStaff((prev) => prev.map((s) => (s.id === id ? { ...s, archived: !s.archived } : s))); }
  function handleDeleteStaff(id) { setStaff((prev) => prev.filter((s) => s.id !== id)); }
  function reorderList(setter) {
    return (from, to) => setter((prev) => {
      const next = [...prev];
      const fromIdx = next.indexOf(from);
      const toIdx = next.indexOf(to);
      if (fromIdx === -1 || toIdx === -1) return prev;
      next.splice(toIdx, 0, next.splice(fromIdx, 1)[0]);
      return next;
    });
  }
  function handleAddDepartment(name) { setDepartments((prev) => (prev.includes(name) ? prev : [...prev, name])); }
  function handleRemoveDepartment(name) { setDepartments((prev) => prev.filter((d) => d !== name)); }
  function handleAddRole(name) { setRoles((prev) => (prev.includes(name) ? prev : [...prev, name])); }
  function handleRemoveRole(name) { setRoles((prev) => prev.filter((r) => r !== name)); }
  function handleAddPosition(name) { setPositions((prev) => (prev.includes(name) ? prev : [...prev, name])); }
  function handleRemovePosition(name) { setPositions((prev) => prev.filter((p) => p !== name)); }
  const handleReorderDepartment = reorderList(setDepartments);
  const handleReorderRole = reorderList(setRoles);
  const handleReorderPosition = reorderList(setPositions);

  const handlers = {
    pickerKey, openPicker, closePicker,
    assignTemplate, unassignTemplate, dropAssignment, openTemplateEditorForNew, openTemplateEditorForEdit,
    assignShift, unassignShift, updateRosterRangeTime,
    updateTemplateShift, addTemplateShift, removeTemplateShift, reorderTemplateShift,
    createShiftAndAssign, hideStaffFromView, addStaffToView,
    positions, positionCells,
    setPositionCell: (key, value) => setPositionCells((prev) => ({ ...prev, [key]: value })),
  };

  function renderSection() {
    switch (activeNavItem) {
      case 'schedule':
        return (
          <CalendarArea
            scale={scale} anchorDate={anchorDate} department={department} departments={departments} staff={staff}
            templates={templates} assignments={assignments} roster={roster}
            customRange={customRange} weekStartsOn={weekStartsOn}
            hiddenStaffIds={hiddenStaffIds} extraStaffIds={extraStaffIds}
            handlers={handlers} onDrillDown={handleDrillDown} canEdit={canEdit}
          />
        );
      case 'templates':
        return (
          <TemplateTab
            templates={templates}
            onOpenNew={() => openTemplateEditorForNew(department)}
            onOpenEdit={(t) => openTemplateEditorForEdit(t)}
            onDeleteTemplate={deleteTemplate}
            canEdit={canEdit}
          />
        );
      case 'team':
        return <TeamTab staff={staff} departments={departments} roles={roles} onSaveStaff={handleSaveStaff} onArchiveStaff={handleArchiveStaff} onDeleteStaff={handleDeleteStaff} canEdit={canEdit} />;
      case 'settings':
        return (
          <SettingsTab
            workspace={workspace} onWorkspace={setWorkspace} role={userRole} onRole={setUserRole}
            departments={departments} onAddDepartment={handleAddDepartment} onRemoveDepartment={handleRemoveDepartment} onReorderDepartment={handleReorderDepartment}
            roles={roles} onAddRole={handleAddRole} onRemoveRole={handleRemoveRole} onReorderRole={handleReorderRole}
            positions={positions} onAddPosition={handleAddPosition} onRemovePosition={handleRemovePosition} onReorderPosition={handleReorderPosition}
            themeMode={themeMode} onThemeMode={setThemeMode} colorTheme={colorTheme} onColorTheme={setColorTheme}
            canEdit={canEdit}
          />
        );
      case 'about': return <AboutTab />;
      case 'help': return <GuideTab />;
      case 'print': return <PrintCenterTab department={department} departments={departments} staff={staff} templates={templates} assignments={assignments} roster={roster} workspace={workspace} />;
      case 'dashboard': return <DashboardTab department={department} staff={staff} templates={templates} assignments={assignments} roster={roster} />;
      case 'reports': return <ReportCenterTab department={department} departments={departments} staff={staff} templates={templates} assignments={assignments} roster={roster} />;
      case 'offtracker': return <OffTrackerTab department={department} departments={departments} staff={staff} roster={roster} />;
      case 'notifications': return <NotificationsTab department={department} staff={staff} templates={templates} assignments={assignments} roster={roster} />;
      default: return null;
    }
  }

  const isScheduleSection = activeNavItem === 'schedule';
  const themeVars = getThemeVars(themeMode, colorTheme);

  return (
    <div className="rosta-app" style={themeVars}>
      <style>{STYLES}</style>

      {templateEditorState ? (
        <TemplateEditor
          initial={templateEditorState.template}
          departments={departments}
          canEdit={canEdit}
          onSave={(saved) => templateEditorState.onDone(saved)}
          onCancel={() => setTemplateEditorState(null)}
          onDelete={(id) => { deleteTemplate(id); setTemplateEditorState(null); }}
        />
      ) : (
        <>
          <TopBar
            section={activeNavItem}
            department={department} onDepartment={setDepartment} departments={departments}
            scale={scale} onScale={setScale}
            anchorDate={anchorDate} onStep={handleStep} onDateSelect={setAnchorDate}
            customRange={customRange} onSelectRange={setCustomRange}
            weekStartsOn={weekStartsOn} onWeekStartsOn={setWeekStartsOn}
            onPublish={() => setToast('Schedule published')}
          />

          <div className="app-body">
            <Sidebar
              expanded={sidebarExpanded} onToggle={() => setSidebarExpanded((e) => !e)}
              activeItem={activeNavItem} onSelectItem={setActiveNavItem}
              workspace={workspace} onWorkspace={setWorkspace} role={userRole} onRole={setUserRole}
            />
            <main className="calendar-area">
              {isScheduleSection ? (
                <div className="calendar-area-inner">{renderSection()}</div>
              ) : (
                renderSection()
              )}
            </main>
          </div>
        </>
      )}

      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}
