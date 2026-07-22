import { MetricsResponseSchema } from "./schemas";
import { useLiveMetricsStore } from "../stores/live-metrics-store";

let socket: WebSocket | null = null;

export function connectMetricsSocket() {
  if (typeof window === "undefined" || socket) return; // SSR guard + singleton

  socket = new WebSocket("ws://localhost:8080/ws/metrics");

  socket.onmessage = (event) => {
    const parsed = MetricsResponseSchema.safeParse(JSON.parse(event.data));
    if (parsed.success) {
      useLiveMetricsStore.getState().setMetrics(parsed.data);
    } else {
      console.error("bad WS payload", parsed.error);
    }
  };

  socket.onclose = () => {
    socket = null;
    setTimeout(connectMetricsSocket, 2000); // reconnect, since teammates run scripts independently of dashboard uptime
  };
}