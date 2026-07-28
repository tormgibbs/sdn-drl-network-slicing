// frontend/src/lib/websocket.ts
import { useLiveMetricsStore } from "../stores/live-metrics-store";
import { WsMetricsEnvelopeSchema } from "./schemas";

let socket: WebSocket | null = null;

export function connectMetricsSocket() {
	if (typeof window === "undefined" || socket) return; // SSR guard + singleton
	socket = new WebSocket("ws://localhost:8080/ws/metrics");
	socket.onmessage = (event) => {
		const parsed = WsMetricsEnvelopeSchema.safeParse(JSON.parse(event.data));
		if (parsed.success) {
			const store = useLiveMetricsStore.getState();
			store.setMetrics(parsed.data.metrics);
			store.setActiveController(parsed.data.active_controller);
			store.setAgentState(parsed.data.agent);
			store.setHeuristicState(parsed.data.heuristic);
			store.setTrafficStatus(parsed.data.traffic);
		} else {
			console.error("bad WS payload", parsed.error);
		}
	};
	socket.onclose = () => {
		socket = null;
		setTimeout(connectMetricsSocket, 2000); // reconnect, since teammates run scripts independently of dashboard uptime
	};
}
