// ── Per-slice data: SLA configs, telemetry generators, history builders ───────
import type { SLAConfig, TelemetryPoint, HistoryRow, RecentCycle, TrafficSource } from "../types/slice1";

// ─────────────────────────────────────────────────────────────────────────────
// Shared helper
// ─────────────────────────────────────────────────────────────────────────────

function buildTimestamp(base: Date, offsetMinutes: number): string {
  const d   = new Date(base.getTime() - offsetMinutes * 60000);
  const pad = (x: number) => String(x).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:00`;
}

// ─────────────────────────────────────────────────────────────────────────────
// VLE  (P5 · Critical)
// ─────────────────────────────────────────────────────────────────────────────

export const VLE_SLA: SLAConfig = { minThrpt: 50, maxLat: 100, maxLoss: 0.5 };

export function genVLETelemetry(pts: number): TelemetryPoint[] {
  return Array.from({ length: pts }, (_, i) => ({
    i,
    thrpt: +(44  + Math.random() * 10).toFixed(2),
    lat:   +(0.8 + Math.random() *  5.5).toFixed(2),
    loss:  +(Math.random() < 0.04 ? Math.random() * 0.8 : 0).toFixed(2),
    alloc: +(48  + Math.random() *  4).toFixed(2),
  }));
}

export function buildVLEHistory(n: number): HistoryRow[] {
  const base = new Date("2023-10-27T14:05:00");
  return Array.from({ length: n }, (_, i) => {
    const thrpt = +(44 + Math.random() * 8).toFixed(1);
    const lat   = +(+thrpt < 46 ? 1 + Math.random() * 5 : 0.8 + Math.random() * 0.6).toFixed(1);
    const loss  = +(Math.random() < 0.04 ? Math.random() * 0.4 : 0).toFixed(1);
    return {
      ts:    buildTimestamp(base, i),
      id:    `cyc-${8800 + i}`,
      thrpt: +thrpt,
      lat:   +lat,
      loss:  +loss,
      alloc: 50.0,
      sla:   +lat > VLE_SLA.maxLat || +thrpt < VLE_SLA.minThrpt || +loss > VLE_SLA.maxLoss
               ? "VIOLATION" : "MET",
    };
  });
}

export const VLE_RECENT: RecentCycle[] = [
  { id: "cyc-882a", thrpt: 48.2, lat: 1.2, status: "MET" },
  { id: "cyc-8829", thrpt: 49.1, lat: 1.1, status: "MET" },
  { id: "cyc-8828", thrpt: 48.8, lat: 1.3, status: "MET" },
  { id: "cyc-8827", thrpt: 44.5, lat: 5.2, status: "VIOLATION" },
  { id: "cyc-8826", thrpt: 49.9, lat: 1.0, status: "MET" },
  { id: "cyc-8825", thrpt: 50.1, lat: 0.9, status: "MET" },
  { id: "cyc-8824", thrpt: 48.0, lat: 1.4, status: "MET" },
];

// ─────────────────────────────────────────────────────────────────────────────
// Student Portal  (P4 · High)
// ─────────────────────────────────────────────────────────────────────────────

export const STUDENT_PORTAL_SLA: SLAConfig = { minThrpt: 25, maxLat: 50, maxLoss: 0.1 };

export function genStudentPortalTelemetry(pts: number): TelemetryPoint[] {
  return Array.from({ length: pts }, (_, i) => ({
    i,
    thrpt:    +(24 + Math.random() * 8).toFixed(2),
    lat:      +(18 + Math.random() * 25).toFixed(1),
    loss:     +(Math.random() < 0.03 ? Math.random() * 0.18 : 0).toFixed(3),
    reqRate:  +(3  + Math.random() * 6).toFixed(1),
    sessions: Math.floor(80 + Math.random() * 120),
  }));
}

export function buildStudentPortalHistory(n: number): HistoryRow[] {
  const base = new Date("2026-06-19T14:05:00");
  const sla  = STUDENT_PORTAL_SLA;
  return Array.from({ length: n }, (_, i) => {
    const thrpt = +(24 + Math.random() * 10).toFixed(1);
    const lat   = +(18 + Math.random() * 40).toFixed(1);
    const loss  = +(Math.random() < 0.03 ? Math.random() * 0.15 : 0).toFixed(3);
    return {
      ts:    buildTimestamp(base, i),
      id:    `cyc-sp${7800 + i}`,
      thrpt: +thrpt,
      lat:   +lat,
      loss:  +loss,
      alloc: 25.0,
      sla:   +lat > sla.maxLat || +thrpt < sla.minThrpt || +loss > sla.maxLoss
               ? "VIOLATION" : "MET",
    };
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Admin  (P3 · Medium)
// ─────────────────────────────────────────────────────────────────────────────

export const ADMIN_SLA: SLAConfig = { minThrpt: 10, maxLat: 150, maxLoss: 1.0 };

export function genAdminTelemetry(pts: number): TelemetryPoint[] {
  return Array.from({ length: pts }, (_, i) => ({
    i,
    thrpt:  +(9  + Math.random() * 4).toFixed(2),
    lat:    +(55 + Math.random() * 80).toFixed(1),
    loss:   +(Math.random() < 0.05 ? Math.random() * 0.8 : 0).toFixed(2),
    txRate: +(2  + Math.random() * 5).toFixed(1),
    flows:  Math.floor(30 + Math.random() * 50),
  }));
}

export function buildAdminHistory(n: number): HistoryRow[] {
  const base = new Date("2026-06-19T14:05:00");
  const sla  = ADMIN_SLA;
  return Array.from({ length: n }, (_, i) => {
    const thrpt = +(9  + Math.random() * 4.5).toFixed(1);
    const lat   = +(55 + Math.random() * 100).toFixed(1);
    const loss  = +(Math.random() < 0.05 ? Math.random() * 0.7 : 0).toFixed(2);
    return {
      ts:    buildTimestamp(base, i),
      id:    `cyc-ad${6400 + i}`,
      thrpt: +thrpt,
      lat:   +lat,
      loss:  +loss,
      alloc: 10.0,
      sla:   +lat > sla.maxLat || +thrpt < sla.minThrpt || +loss > sla.maxLoss
               ? "VIOLATION" : "MET",
    };
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// IoT  (P2 · Low)
// ─────────────────────────────────────────────────────────────────────────────

export const IOT_SLA: SLAConfig = { minThrpt: 0.064, maxLat: 200, maxLoss: 5.0 };

export function genIoTTelemetry(pts: number): TelemetryPoint[] {
  return Array.from({ length: pts }, (_, i) => {
    const onPhase = Math.sin(i * 0.3) > 0.3;
    const pktRate = onPhase
      ? +(20 + Math.random() * 30).toFixed(1)
      : +(2  + Math.random() *  5).toFixed(1);
    return {
      i,
      thrpt:   +(+pktRate * 0.00096).toFixed(4),
      lat:     +(onPhase ? 40 + Math.random() * 80 : 60 + Math.random() * 120).toFixed(1),
      loss:    +(Math.random() < 0.08 ? Math.random() * 3.5 : 0).toFixed(2),
      pktRate: +pktRate,
      sources: Math.floor(onPhase ? 6 + Math.random() * 2 : 3 + Math.random() * 3),
    };
  });
}

export function buildIoTHistory(n: number): HistoryRow[] {
  const base = new Date("2026-06-19T14:05:00");
  const sla  = IOT_SLA;
  return Array.from({ length: n }, (_, i) => {
    const lat   = +(60 + Math.random() * 150).toFixed(1);
    const loss  = +(Math.random() < 0.08 ? Math.random() * 3 : 0).toFixed(2);
    const thrpt = +(0.03 + Math.random() * 0.08).toFixed(4);
    return {
      ts:    buildTimestamp(base, i),
      id:    `cyc-io${5200 + i}`,
      thrpt: +thrpt,
      lat:   +lat,
      loss:  +loss,
      alloc: 0.064,
      sla:   +lat > sla.maxLat || +loss > sla.maxLoss ? "VIOLATION" : "MET",
    };
  });
}

export const STATUS_COLOR: Record<TrafficSource["status"], string> = {
  "on-schedule": "#4ADE80",
  delayed:       "#EAB308",
  missed:        "#FB2C36",
};

export const INIT_SOURCES: TrafficSource[] = [
  { id: "SRC-001", name: "SW-A1 Heartbeat",  lastArrival: 800,   pktRate: 6,  latency: 42,  status: "on-schedule" },
  { id: "SRC-002", name: "AP-104 Keepalive", lastArrival: 1200,  pktRate: 4,  latency: 58,  status: "on-schedule" },
  { id: "SRC-003", name: "CTRL-E2 Beacon",   lastArrival: 3100,  pktRate: 2,  latency: 145, status: "delayed"     },
  { id: "SRC-004", name: "AP-LIB-F2 Pulse",  lastArrival: 900,   pktRate: 4,  latency: 51,  status: "on-schedule" },
  { id: "SRC-005", name: "SENS-LAB3 Tick",   lastArrival: 1500,  pktRate: 12, latency: 33,  status: "on-schedule" },
  { id: "SRC-006", name: "METER-M1 Poll",    lastArrival: 62000, pktRate: 0,  latency: 0,   status: "missed"      },
  { id: "SRC-007", name: "HUM-SRV-A Ping",   lastArrival: 1800,  pktRate: 8,  latency: 29,  status: "on-schedule" },
  { id: "SRC-008", name: "MOT-G4 Probe",     lastArrival: 8200,  pktRate: 1,  latency: 178, status: "delayed"     },
];

export function fmtArrival(ms: number): string {
  if (ms < 2000)  return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(0)}s`;
  return `${(ms / 60000).toFixed(0)}m`;
}

// ─────────────────────────────────────────────────────────────────────────────
// General  (P1 · Lowest)
// ─────────────────────────────────────────────────────────────────────────────

export const GENERAL_SLA: SLAConfig = { minThrpt: 5, maxLat: 500, maxLoss: 10.0 };

export const PROTO_COLORS = {
  https: "#2B7FFF",
  udp:   "#EAB308",
  tcp:   "#4ADE80",
  dns:   "#C4C7C6",
};

export function genGeneralTelemetry(pts: number): TelemetryPoint[] {
  return Array.from({ length: pts }, (_, i) => {
    const thrpt  = +(4 + Math.random() * 8).toFixed(2);
    const httpsP = +(0.40 + Math.random() * 0.15);
    const udpP   = +(0.28 + Math.random() * 0.12);
    const tcpP   = +(0.20 + Math.random() * 0.08);
    const dnsP   = 1 - httpsP - udpP - tcpP;
    return {
      i,
      thrpt: +thrpt,
      lat:   +(180 + Math.random() * 280).toFixed(1),
      loss:  +(Math.random() < 0.12 ? Math.random() * 7 : Math.random() * 1.5).toFixed(2),
      https: +(+thrpt * httpsP).toFixed(2),
      udp:   +(+thrpt * udpP).toFixed(2),
      tcp:   +(+thrpt * tcpP).toFixed(2),
      dns:   +(+thrpt * dnsP).toFixed(2),
    };
  });
}

export function buildGeneralHistory(n: number): HistoryRow[] {
  const base = new Date("2026-06-19T14:05:00");
  const sla  = GENERAL_SLA;
  return Array.from({ length: n }, (_, i) => {
    const thrpt = +(4   + Math.random() * 8).toFixed(1);
    const lat   = +(180 + Math.random() * 300).toFixed(1);
    const loss  = +(Math.random() < 0.12 ? Math.random() * 6 : Math.random() * 1.2).toFixed(2);
    return {
      ts:    buildTimestamp(base, i),
      id:    `cyc-gn${4100 + i}`,
      thrpt: +thrpt,
      lat:   +lat,
      loss:  +loss,
      alloc: 5.0,
      sla:   +lat > sla.maxLat || +thrpt < sla.minThrpt || +loss > sla.maxLoss
               ? "VIOLATION" : "MET",
    };
  });
}