import type { Metric, SliceKey, Mode, Scenario } from "#/types/slice";

export type MockDashboardSnapshot = {
  metrics: Record<SliceKey, Metric>;
  allocations: Record<SliceKey, number>;
  timestamp: string;
};

export const initialData = {
  slices: {
    // Values below are the single source of truth for SLA thresholds and
    // must match config/slices.yaml exactly. They previously matched this
    // file's own mock dynamicStates numbers instead (5-10x too high for
    // four of five slices), which caused computeSlaStatus to report
    // VIOLATION against genuinely healthy real throughput once live data
    // replaced the mocks. If slices.yaml's thresholds ever change, update
    // here to match — this is the only place min_throughput_bps should be
    // defined; the five slice detail pages read from here rather than
    // holding their own copies.
    vle: {
      name: "VLE",
      priority: 5,
      priority_label: "PR5",
      max_latency_ms: 100,
      max_loss_pct: 0.5,
      min_throughput_bps: 5_000_000,
    },
    student_portal: {
      name: "Student Portal",
      priority: 4,
      priority_label: "PR4",
      max_latency_ms: 50,
      max_loss_pct: 0.1,
      min_throughput_bps: 3_000_000,
    },
    admin: {
      name: "Admin",
      priority: 3,
      priority_label: "PR3",
      max_latency_ms: 150,
      max_loss_pct: 1.0,
      min_throughput_bps: 2_000_000,
    },
    iot: {
      name: "IoT",
      priority: 2,
      priority_label: "PR2",
      max_latency_ms: 200,
      max_loss_pct: 5.0,
      min_throughput_bps: 64_000,
    },
    general: {
      name: "General",
      priority: 1,
      priority_label: "PR1",
      max_latency_ms: 500,
      max_loss_pct: 10.0,
      min_throughput_bps: 1_000_000,
    },
  },
};

// Simulates what the WebSocket pushes every 5 seconds
export const dynamicStates: Record<string, MockDashboardSnapshot> = {
  agent_normal: {
    timestamp: "",
    allocations: {
      vle: 50000000,
      student_portal: 25000000,
      admin: 10000000,
      iot: 10000000,
      general: 5000000,
    },
    metrics: {
      vle: { tx_throughput_bps: 55000000, latency_ms: 1.2, loss_pct: 0.0 },
      student_portal: {
        tx_throughput_bps: 26000000,
        latency_ms: 0.8,
        loss_pct: 0.0,
      },
      admin: { tx_throughput_bps: 11000000, latency_ms: 0.6, loss_pct: 0.0 },
      iot: { tx_throughput_bps: 65000, latency_ms: 0.9, loss_pct: 0.03 },
      general: { tx_throughput_bps: 5500000, latency_ms: 0.7, loss_pct: 0.0 },
    },
  },

  agent_registration_spike: {
    timestamp: "",
    allocations: {
      vle: 300000000,
      student_portal: 180000000,
      admin: 80000000,
      iot: 50000000,
      general: 40000000,
    },
    metrics: {
      vle: { tx_throughput_bps: 428000000, latency_ms: 11.8, loss_pct: 0.0 },
      student_portal: {
        tx_throughput_bps: 151200000,
        latency_ms: 24.2,
        loss_pct: 0.0,
      },
      admin: { tx_throughput_bps: 84200000, latency_ms: 9.0, loss_pct: 0.0 },
      iot: { tx_throughput_bps: 13000000, latency_ms: 113.7, loss_pct: 0.06 },
      general: {
        tx_throughput_bps: 310700000,
        latency_ms: 45.7,
        loss_pct: 0.0,
      },
    },
  },

  agent_quiz_spike: {
    timestamp: "",
    allocations: {
      vle: 350000000,
      student_portal: 100000000,
      admin: 80000000,
      iot: 80000000,
      general: 40000000,
    },
    metrics: {
      vle: { tx_throughput_bps: 390000000, latency_ms: 18.4, loss_pct: 0.0 },
      student_portal: {
        tx_throughput_bps: 60000000,
        latency_ms: 8.1,
        loss_pct: 0.0,
      },
      admin: { tx_throughput_bps: 70000000, latency_ms: 7.2, loss_pct: 0.0 },
      iot: { tx_throughput_bps: 65000, latency_ms: 1.1, loss_pct: 0.03 },
      general: { tx_throughput_bps: 30000000, latency_ms: 12.0, loss_pct: 0.0 },
    },
  },

  static_normal: {
    timestamp: "",
    allocations: {
      vle: 130000000,
      student_portal: 130000000,
      admin: 130000000,
      iot: 130000000,
      general: 130000000,
    },
    metrics: {
      vle: { tx_throughput_bps: 55000000, latency_ms: 1.4, loss_pct: 0.0 },
      student_portal: {
        tx_throughput_bps: 26000000,
        latency_ms: 0.9,
        loss_pct: 0.0,
      },
      admin: { tx_throughput_bps: 11000000, latency_ms: 0.7, loss_pct: 0.0 },
      iot: { tx_throughput_bps: 65000, latency_ms: 1.0, loss_pct: 0.03 },
      general: { tx_throughput_bps: 5500000, latency_ms: 0.8, loss_pct: 0.0 },
    },
  },

  static_registration_spike: {
    timestamp: "",
    allocations: {
      vle: 130000000,
      student_portal: 130000000,
      admin: 130000000,
      iot: 130000000,
      general: 130000000,
    },
    metrics: {
      vle: { tx_throughput_bps: 40000000, latency_ms: 95.0, loss_pct: 0.45 },
      student_portal: {
        tx_throughput_bps: 20000000,
        latency_ms: 55.0,
        loss_pct: 0.12,
      },
      admin: { tx_throughput_bps: 80000000, latency_ms: 14.0, loss_pct: 0.0 },
      iot: { tx_throughput_bps: 65000, latency_ms: 185.0, loss_pct: 0.08 },
      general: { tx_throughput_bps: 5500000, latency_ms: 62.0, loss_pct: 0.0 },
    },
  },

  static_quiz_spike: {
    timestamp: "",
    allocations: {
      vle: 130000000,
      student_portal: 130000000,
      admin: 130000000,
      iot: 130000000,
      general: 130000000,
    },
    metrics: {
      vle: { tx_throughput_bps: 45000000, latency_ms: 82.0, loss_pct: 0.38 },
      student_portal: {
        tx_throughput_bps: 26000000,
        latency_ms: 6.0,
        loss_pct: 0.0,
      },
      admin: { tx_throughput_bps: 11000000, latency_ms: 5.0, loss_pct: 0.0 },
      iot: { tx_throughput_bps: 65000, latency_ms: 1.2, loss_pct: 0.03 },
      general: { tx_throughput_bps: 5500000, latency_ms: 4.0, loss_pct: 0.0 },
    },
  },

  heuristic_normal: {
    timestamp: "",
    allocations: {
      vle: 200000000,
      student_portal: 140000000,
      admin: 110000000,
      iot: 100000000,
      general: 100000000,
    },
    metrics: {
      vle: { tx_throughput_bps: 55000000, latency_ms: 1.3, loss_pct: 0.0 },
      student_portal: {
        tx_throughput_bps: 26000000,
        latency_ms: 0.8,
        loss_pct: 0.0,
      },
      admin: { tx_throughput_bps: 11000000, latency_ms: 0.6, loss_pct: 0.0 },
      iot: { tx_throughput_bps: 65000, latency_ms: 0.9, loss_pct: 0.03 },
      general: { tx_throughput_bps: 5500000, latency_ms: 0.7, loss_pct: 0.0 },
    },
  },

  heuristic_registration_spike: {
    timestamp: "",
    allocations: {
      vle: 240000000,
      student_portal: 160000000,
      admin: 100000000,
      iot: 80000000,
      general: 70000000,
    },
    metrics: {
      vle: { tx_throughput_bps: 320000000, latency_ms: 28.0, loss_pct: 0.0 },
      student_portal: {
        tx_throughput_bps: 140000000,
        latency_ms: 44.0,
        loss_pct: 0.09,
      },
      admin: { tx_throughput_bps: 90000000, latency_ms: 11.0, loss_pct: 0.0 },
      iot: { tx_throughput_bps: 65000, latency_ms: 168.0, loss_pct: 0.06 },
      general: { tx_throughput_bps: 5500000, latency_ms: 49.0, loss_pct: 0.0 },
    },
  },

  heuristic_quiz_spike: {
    timestamp: "",
    allocations: {
      vle: 280000000,
      student_portal: 120000000,
      admin: 100000000,
      iot: 90000000,
      general: 60000000,
    },
    metrics: {
      vle: { tx_throughput_bps: 340000000, latency_ms: 22.0, loss_pct: 0.0 },
      student_portal: {
        tx_throughput_bps: 55000000,
        latency_ms: 7.0,
        loss_pct: 0.0,
      },
      admin: { tx_throughput_bps: 60000000, latency_ms: 6.0, loss_pct: 0.0 },
      iot: { tx_throughput_bps: 65000, latency_ms: 162.0, loss_pct: 0.03 },
      general: { tx_throughput_bps: 5500000, latency_ms: 15.0, loss_pct: 0.0 },
    },
  },
};

export function getDynamicState(mode: Mode, scenario: Scenario): MockDashboardSnapshot {
  const key = `${mode}_${scenario}`;
  return dynamicStates[key];
}

export function generateHistory(
  snapshot: MockDashboardSnapshot,
  points: number,
): MockDashboardSnapshot[] {
  return Array.from({ length: points }, (_, i) => ({
    ...snapshot,
    metrics: {
      vle: {
        ...snapshot.metrics.vle,
        tx_throughput_bps:
          snapshot.metrics.vle.tx_throughput_bps * (0.85 + Math.random() * 0.3),
        latency_ms:
          (snapshot.metrics.vle.latency_ms ?? 0) * (0.85 + Math.random() * 0.3),
      },
      student_portal: {
        ...snapshot.metrics.student_portal,
        tx_throughput_bps:
          snapshot.metrics.student_portal.tx_throughput_bps *
          (0.85 + Math.random() * 0.3),
        latency_ms:
          (snapshot.metrics.student_portal.latency_ms ?? 0) *
          (0.85 + Math.random() * 0.3),
      },
      admin: {
        ...snapshot.metrics.admin,
        tx_throughput_bps:
          snapshot.metrics.admin.tx_throughput_bps *
          (0.85 + Math.random() * 0.3),
        latency_ms:
          (snapshot.metrics.admin.latency_ms ?? 0) *
          (0.85 + Math.random() * 0.3),
      },
      iot: {
        ...snapshot.metrics.iot,
        tx_throughput_bps:
          snapshot.metrics.iot.tx_throughput_bps * (0.85 + Math.random() * 0.3),
        latency_ms:
          (snapshot.metrics.iot.latency_ms ?? 0) * (0.85 + Math.random() * 0.3),
      },
      general: {
        ...snapshot.metrics.general,
        tx_throughput_bps:
          snapshot.metrics.general.tx_throughput_bps *
          (0.85 + Math.random() * 0.3),
        latency_ms:
          (snapshot.metrics.general.latency_ms ?? 0) *
          (0.85 + Math.random() * 0.3),
      },
    },
    timestamp: new Date(Date.now() - (points - i) * 5000).toISOString(),
  }));
}