export function formatBps(bps: number): string {
	if (bps >= 1_000_000) return `${(bps / 1_000_000).toFixed(1)} Mbps`;
	if (bps >= 1_000) return `${(bps / 1_000).toFixed(1)} Kbps`;
	return `${bps} bps`;
}

export function formatMs(ms: number | null): string {
	if (ms === null) return "—";
	return `${ms.toFixed(1)} ms`;
}

export function formatPct(pct: number | null): string {
	if (pct === null) return "—";
	return `${pct.toFixed(2)}%`;
}

export function formatDeviceCount(count: number): string {
	if (count >= 1000) return `${(count / 1000).toFixed(1)}k`;
	return `${count}`;
}
