// frontend/src/hooks/use-traffic-control.ts
import { useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useLiveMetricsStore } from "#/stores/live-metrics-store";
import { postTrafficControl, postTrafficScenario } from "@/lib/api";
import type { TrafficControlRequest } from "@/lib/schemas";
import type { Scenario } from "@/types/slice";

export function useTrafficControl() {
	const [pendingScenario, setPendingScenario] = useState<Scenario | null>(null);
	const trafficStatus = useLiveMetricsStore((s) => s.trafficStatus);
	const running = trafficStatus?.running ?? false;
	const currentScenario = trafficStatus?.current_scenario as
		| Scenario
		| undefined;

	useEffect(() => {
		if (pendingScenario && currentScenario === pendingScenario) {
			setPendingScenario(null);
		}
	}, [currentScenario, pendingScenario]);

	const scenarioMutation = useMutation({
		mutationFn: postTrafficScenario,
		onMutate: (vars) => setPendingScenario(vars.scenario as Scenario),
		onError: (err: Error) => {
			toast.error(err.message);
			setPendingScenario(null);
		},
	});

	const controlMutation = useMutation<unknown, Error, TrafficControlRequest>({
		mutationFn: postTrafficControl,
		onError: (err) => toast.error(err.message),
	});

	return {
		running,
		isTrafficBusy: controlMutation.isPending,
		lastLoop: trafficStatus?.last_loop ?? null,
		scenarioMode: pendingScenario ?? currentScenario,
		isSwitchingScenario: pendingScenario !== null,
		switchScenario: (scenario: Scenario) => {
			if (!running) {
				toast.error("Start traffic before switching scenario");
				return;
			}
			scenarioMutation.mutate({ scenario });
		},
		startTraffic: () => controlMutation.mutate({ action: "start", loops: 0 }),
		stopTraffic: () => controlMutation.mutate({ action: "stop" }),
	};
}
