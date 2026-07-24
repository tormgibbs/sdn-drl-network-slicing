import { z } from "zod";

export const SliceMetricsSchema = z.object({
  latency_ms: z.number(),
  loss_pct: z.number(),
  tx_throughput_bps: z.number(),
});

export const MetricsResponseSchema = z.record(z.string(), SliceMetricsSchema);
// keys are slice names: "vle" | "student_portal" | "admin" | "iot" | "general"

export const HealthResponseSchema = z.object({
  status: z.string(),
  registry_frozen: z.boolean(),
});

export const AllocateRequestSchema = z
  .record(z.string(), z.number())
  .refine((v) => Math.abs(Object.values(v).reduce((a, b) => a + b, 0) - 1) < 1e-6, {
    message: "fractions must sum to 1.0",
  });

export const AllocateResponseSchema = z.object({
  status: z.string(),
  rates_kbps: z.record(z.string(), z.number()),
});

export const SliceConfigSchema = z.object({
  name: z.string(),
  priority: z.number(),
  priority_label: z.string(),
  max_latency_ms: z.number(),
  max_loss_pct: z.number(),
  min_throughput_bps: z.number(),
});

// NOTE: MetricSchema/Metric is a near-duplicate of SliceMetricsSchema above
// with different nullability (latency_ms/loss_pct nullable here, not there).
// MetricsResponseSchema — which validates the real /ws/metrics envelope —
// uses SliceMetricsSchema, NOT this one, so live WS data is never actually
// null for these fields.
//
// CONFIRMED (grep + inspection, not just assumed): Metric IS load-bearing —
// re-exported as SliceMetrics via types/slice.ts, and computeSlaStatus
// (lib/sla.ts) genuinely branches on latency_ms !== null / loss_pct !== null.
// Likely serves callers using mock/dashboard-shaped data (e.g. index.tsx's
// initialData) where nulls may legitimately occur, unlike live WS data.
// Do NOT delete or consolidate into SliceMetricsSchema — both schemas are
// intentionally different and both are in active use.
//
// SEPARATE, UNRESOLVED ISSUE: types/slice.ts's SLAStatus ("NOMINAL" |
// "WARNING" | "VIOLATION", used by computeSlaStatus) is a different type
// from types/slice1.ts's SLAStatus ("MET" | "VIOLATION", used by all five
// slice components). Same name, different shape, per Section 4/8 of the
// handoff doc. Not yet reconciled — flag before assuming SLA status means
// the same thing across index.tsx and the slice pages.
export const MetricSchema = z.object({
  tx_throughput_bps: z.number(),
  latency_ms: z.number().nullable(),
  loss_pct: z.number().nullable(),
});

export const AgentStateSchema = z.object({
  timestamp: z.string(),
  step: z.number().int(),
  reward: z.number(),
  allocation_kbps: z.record(z.string(), z.number()),
  done: z.boolean(),
});

// The actual full envelope /ws/metrics now sends
export const WsMetricsEnvelopeSchema = z.object({
  timestamp: z.string(),
  metrics: MetricsResponseSchema,
  agent: AgentStateSchema.nullable(),
});

export const TrafficScenarioRequestSchema = z.object({
  scenario: z.string(),
});

export const TrafficStatusSchema = z.object({
  running: z.boolean(),
  last_loop: z.object({
    loop: z.number(),
    scenario: z.string(),
    results: z.record(z.string(), z.unknown()),
    failed_slices: z.array(z.string()),
    timestamp: z.string(),
  }).nullable(),
});

export const AgentControlRequestSchema = z.object({
  action: z.enum(["start", "stop"]),
  model_path: z.string().optional(),
  vecnorm_path: z.string().optional(),
});

export const AgentStatusSchema = z.object({
  running: z.boolean(),
  last_result: AgentStateSchema.nullable(),
});


export type AgentControlRequest = z.infer<typeof AgentControlRequestSchema>;
export type AgentStatus = z.infer<typeof AgentStatusSchema>;
export type TrafficStatus = z.infer<typeof TrafficStatusSchema>;
export type TrafficScenarioRequest = z.infer<typeof TrafficScenarioRequestSchema>;
export type WsMetricsEnvelope = z.infer<typeof WsMetricsEnvelopeSchema>;
export type AgentState = z.infer<typeof AgentStateSchema>;
export type SliceConfig = z.infer<typeof SliceConfigSchema>;
export type Metric = z.infer<typeof MetricSchema>;
export type MetricsResponse = z.infer<typeof MetricsResponseSchema>;
export type AllocateRequest = z.input<typeof AllocateRequestSchema>;
export type AllocateResponse = z.infer<typeof AllocateResponseSchema>;