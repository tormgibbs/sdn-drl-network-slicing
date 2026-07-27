import {
  HealthResponseSchema,
  MetricsResponseSchema,
  AllocateResponseSchema,
  TrafficScenarioRequestSchema,
  TrafficStatusSchema,
  AgentControlRequestSchema,
  AgentStatusSchema,
  type AllocateRequest,
  type TrafficScenarioRequest,
  type AgentControlRequest,
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
  const parsedBody = TrafficScenarioRequestSchema.parse(body);
  const res = await fetch(`${BASE_URL}/traffic/scenario`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(parsedBody),
  });
  if (!res.ok) throw new Error(`scenario switch failed: ${res.status}`);
  return TrafficStatusSchema.parse(await res.json());
}

// GET /traffic/state — same {running, last_loop} shape as postTrafficScenario's
// own response (both backed by tm.status()). Used to poll for scenario-switch
// confirmation: watch last_loop.scenario until it matches the requested value.
// Worst-case lag is one full loop duration + inter_loop_gap_sec (~65s default,
// confirmed from traffic/runner.py) — this is real backend behavior, not a bug.
export async function getTrafficState() {
  const res = await fetch(`${BASE_URL}/traffic/state`);
  if (!res.ok) throw new Error(`traffic state fetch failed: ${res.status}`);
  return TrafficStatusSchema.parse(await res.json());
}

// POST /agent/control — {action: "start", model_path, vecnorm_path?} or
// {action: "stop"}. Response is am.status() — same shape as GET /agent/state.
// Note: "start" synchronously loads a PPO model from disk (PPO.load in
// AgentRunner.__init__) before returning, so this call is not instant — treat
// as optimistic/pending in the UI, same pattern as scenario switching.
export async function postAgentControl(body: AgentControlRequest) {
  const parsedBody = AgentControlRequestSchema.parse(body);
  const res = await fetch(`${BASE_URL}/agent/control`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(parsedBody),
  });
  if (!res.ok) throw new Error(`agent control failed: ${res.status}`);
  return AgentStatusSchema.parse(await res.json());
}