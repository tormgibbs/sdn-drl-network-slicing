// frontend/src/hooks/use-traffic-control.ts

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
	getTrafficState,
	postTrafficControl,
	postTrafficScenario,
} from "@/lib/api";
import type { TrafficControlRequest, TrafficStatus } from "@/lib/schemas";
import type { Scenario } from "@/types/slice";

export function useTrafficControl() {
	const queryClient = useQueryClient();
	const [pendingScenario, setPendingScenario] = useState<Scenario | null>(null);

	const trafficState = useQuery({
		queryKey: ["trafficState"],
		queryFn: getTrafficState,
		refetchInterval: pendingScenario ? 2500 : 5000,
	});

	useEffect(() => {
		if (
			pendingScenario &&
			trafficState.data?.last_loop?.scenario === pendingScenario
		) {
			setPendingScenario(null);
		}
	}, [trafficState.data, pendingScenario]);

	const scenarioMutation = useMutation({
		mutationFn: postTrafficScenario,
		onMutate: (vars) => setPendingScenario(vars.scenario as Scenario),
		onError: (err: Error) => {
			toast.error(err.message);
			setPendingScenario(null);
		},
		onSuccess: () =>
			queryClient.invalidateQueries({ queryKey: ["trafficState"] }),
	});

	const controlMutation = useMutation<
		TrafficStatus,
		Error,
		TrafficControlRequest
	>({
		mutationFn: postTrafficControl,
		onError: (err) => toast.error(err.message),
		onSuccess: () =>
			queryClient.invalidateQueries({ queryKey: ["trafficState"] }),
	});

	const running = trafficState.data?.running ?? false;

	return {
		running,
		isTrafficBusy: controlMutation.isPending,
		lastLoop: trafficState.data?.last_loop ?? null,
		scenarioMode: (pendingScenario ?? trafficState.data?.last_loop?.scenario) as
			| Scenario
			| undefined,
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
