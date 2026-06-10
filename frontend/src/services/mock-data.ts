import { MOCK_INTERVAL_MS } from '@/lib/constants'
import type { StateResponse, WsMessage } from '@/types/api'
import type { SliceName } from '@/types/slice'

// Flip this to false when the real backend is ready
export const USE_MOCK = true

export const MOCK_STATE: StateResponse = {
	metrics: {
		vle: { tx_throughput_bps: 48000000, latency_ms: 1.2, loss_pct: 0.0 },
		student_portal: {
			tx_throughput_bps: 24000000,
			latency_ms: 0.8,
			loss_pct: 0.0,
		},
		admin: { tx_throughput_bps: 9800000, latency_ms: 0.6, loss_pct: 0.0 },
		iot: { tx_throughput_bps: 62000, latency_ms: 0.9, loss_pct: 0.03 },
		general: { tx_throughput_bps: 4900000, latency_ms: 0.7, loss_pct: 0.0 },
	},
	allocations: {
		vle: 50000000,
		student_portal: 25000000,
		admin: 10000000,
		iot: 10000000,
		general: 5000000,
	},
	mode: 'agent',
	slices: {
		vle: {
			max_latency_ms: 100,
			max_loss_pct: 0.5,
			min_throughput_bps: 50000000,
			priority: 5,
		},
		student_portal: {
			max_latency_ms: 50,
			max_loss_pct: 0.1,
			min_throughput_bps: 25000000,
			priority: 4,
		},
		admin: {
			max_latency_ms: 150,
			max_loss_pct: 1.0,
			min_throughput_bps: 10000000,
			priority: 3,
		},
		iot: {
			max_latency_ms: 200,
			max_loss_pct: 5.0,
			min_throughput_bps: 64000,
			priority: 2,
		},
		general: {
			max_latency_ms: 500,
			max_loss_pct: 10.0,
			min_throughput_bps: 5000000,
			priority: 1,
		},
	},
	traffic: {
		vle: {
			device_count: 3000,
			pattern: 'mixed',
			continuous_bps: 50000000,
			on_off_bps: 30000000,
			mean_on_sec: 15,
			mean_off_sec: 45,
		},
		student_portal: {
			device_count: 2000,
			pattern: 'mixed',
			continuous_bps: 25000000,
			on_off_bps: 20000000,
			mean_on_sec: 8,
			mean_off_sec: 20,
		},
		admin: { device_count: 500, pattern: 'continuous', target_bps: 10000000 },
		iot: { device_count: 4000, pattern: 'continuous', target_bps: 64000 },
		general: { device_count: 500, pattern: 'continuous', target_bps: 5000000 },
	},
	system: {
		ues_attached: 5,
		switches_connected: 8,
		controller_healthy: true,
	},
}

// Adds small random drift to metrics so charts show live movement in mock mode
function driftMetrics(state: StateResponse): WsMessage {
	const slices = Object.keys(state.metrics) as SliceName[]

	const metrics = Object.fromEntries(
		slices.map((slice) => {
			const m = state.metrics[slice]
			return [
				slice,
				{
					tx_throughput_bps: Math.max(
						0,
						m.tx_throughput_bps * (0.92 + Math.random() * 0.16),
					),
					latency_ms:
						m.latency_ms !== null
							? +(m.latency_ms * (0.9 + Math.random() * 0.2)).toFixed(2)
							: null,
					loss_pct:
						m.loss_pct !== null
							? +(m.loss_pct * (0.8 + Math.random() * 0.4)).toFixed(4)
							: null,
				},
			]
		}),
	) as StateResponse['metrics']

	return {
		metrics,
		allocations: { ...state.allocations },
		traffic: { ...state.traffic },
		timestamp: new Date().toISOString(),
	}
}

// Calls onMessage on an interval simulating WebSocket pushes
// Returns a cleanup function — call it to stop the interval
export function startMockWebSocket(
	onMessage: (msg: WsMessage) => void,
): () => void {
	const id = setInterval(() => {
		onMessage(driftMetrics(MOCK_STATE))
	}, MOCK_INTERVAL_MS)

	return () => clearInterval(id)
}
