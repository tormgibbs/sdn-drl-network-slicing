import type { SLAStatus } from "../types/slice1";

export function buildRecentCycles<T extends { id: string; thrpt: number; lat: number | null; sla: SLAStatus }>(
  history: T[],
  count = 7,
) {
  return history.slice(0, count).map((r) => ({
    id: r.id,
    thrpt: r.thrpt,
    lat: r.lat ?? 0,
    status: r.sla,
  }));
}