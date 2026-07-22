import { HealthResponseSchema, MetricsResponseSchema, AllocateResponseSchema, type AllocateRequest } from "./schemas";

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