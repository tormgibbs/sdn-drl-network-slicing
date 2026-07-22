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

export const MetricSchema = z.object({
  tx_throughput_bps: z.number(),
  latency_ms: z.number().nullable(),
  loss_pct: z.number().nullable(),
});

export type SliceConfig = z.infer<typeof SliceConfigSchema>;
export type Metric = z.infer<typeof MetricSchema>;
export type MetricsResponse = z.infer<typeof MetricsResponseSchema>;
export type AllocateRequest = z.input<typeof AllocateRequestSchema>;
export type AllocateResponse = z.infer<typeof AllocateResponseSchema>;