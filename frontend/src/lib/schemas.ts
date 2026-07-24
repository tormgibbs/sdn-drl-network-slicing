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

// NOTE: MetricSchema/Metric (below) is a near-duplicate of SliceMetricsSchema
// above with different nullability (latency_ms/loss_pct nullable here, not
// there). MetricsResponseSchema — the schema that actually validates the real
// /ws/metrics envelope's `metrics` field — uses SliceMetricsSchema, NOT this
// one. MetricSchema/Metric is currently disconnected from the real data
// pipeline; it's only reachable via types/slice.ts's re-export and
// `SliceMetrics` alias, and it's not yet confirmed whether anything actually
// depends on that alias.
//
// Before consolidating or deleting either schema: (1) grep for MetricSchema
// and `: Metric` usage across src/ to confirm what's really load-bearing, and
// (2) check whether computeSlaStatus's call sites (slice-table.tsx, index.tsx,
// the slice components) type their metric parameter as nullable defensively —
// if so, tightening this schema later could surface those call sites as
// having handled a null case that, per SliceMetricsSchema, never actually
// occurs. See handoff doc Section 8 re: not deleting based on assumed-unused
// names without verifying first.
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

export type TrafficStatus = z.infer<typeof TrafficStatusSchema>;
export type TrafficScenarioRequest = z.infer<typeof TrafficScenarioRequestSchema>;
export type WsMetricsEnvelope = z.infer<typeof WsMetricsEnvelopeSchema>;
export type AgentState = z.infer<typeof AgentStateSchema>;
export type SliceConfig = z.infer<typeof SliceConfigSchema>;
export type Metric = z.infer<typeof MetricSchema>;
export type MetricsResponse = z.infer<typeof MetricsResponseSchema>;
export type AllocateRequest = z.input<typeof AllocateRequestSchema>;
export type AllocateResponse = z.infer<typeof AllocateResponseSchema>;