import type { StateResponse } from '@/types/api'

export async function fetchState(): Promise<StateResponse> {
	const res = await fetch('/api/state')
	if (!res.ok) throw new Error('Failed to fetch controller state')
	return res.json()
}

export async function postMode(mode: string) {
	const res = await fetch('/api/mode', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ mode }),
	})
	if (!res.ok) throw new Error('Failed to set mode')
	return res.json()
}

export async function postScenario(scenario: string) {
	const res = await fetch('/api/scenario', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ scenario }),
	})
	if (!res.ok) throw new Error('Failed to set scenario')
	return res.json()
}

export async function postAllocate(allocations: Record<string, number>) {
	const res = await fetch('/api/allocate', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(allocations),
	})
	if (!res.ok) throw new Error('Failed to set allocations')
	return res.json()
}

export async function postTraffic(params: Record<string, unknown>) {
	const res = await fetch('/api/traffic', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(params),
	})
	if (!res.ok) throw new Error('Failed to update traffic')
	return res.json()
}
