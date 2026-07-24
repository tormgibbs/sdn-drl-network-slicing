import {
  HealthResponseSchema,
  MetricsResponseSchema,
  AllocateResponseSchema,
  TrafficScenarioRequestSchema,
  type AllocateRequest,
  type TrafficScenarioRequest,
  TrafficStatusSchema,
} from "./schemas";

const BASE_URL = "http://localhost:8080";

export async function getHealth() {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error(`health check failed: ${res.status}`);
  return HealthResponseSchema.parse(await res.json());
}

export async function getMetrics() {
  const res = await fetch(`${BASE_URL}/metrics`);
  if (!res.ok) throw new Error(`metrics fetch failed: ${res.status}`);
  return MetricsResponseSchema.parse(await res.json());
}

export async function postAllocate(body: AllocateRequest) {
  const res = await fetch(`${BASE_URL}/allocate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`allocate failed: ${res.status}`);
  return AllocateResponseSchema.parse(await res.json());
}

export async function postTrafficScenario(body: TrafficScenarioRequest) {
  TrafficScenarioRequestSchema.parse(body);
  const res = await fetch(`${BASE_URL}/traffic/scenario`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => null);
    throw new Error(errorBody?.detail ?? `scenario switch failed: ${res.status}`);
  }
  return TrafficStatusSchema.parse(await res.json());
}