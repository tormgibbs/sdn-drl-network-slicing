// frontend/src/routes/_app.tsx
import { createFileRoute, Outlet, useLocation } from "@tanstack/react-router";
import { useEffect } from "react";
import AppSidebar from "#/components/primitives/sidebar";
import { sidebarItems } from "#/data/sidebar";
import { Separator } from "#/components/ui/separator";
import {
	SidebarInset,
	SidebarProvider,
	SidebarTrigger,
} from "#/components/ui/sidebar";
import { connectMetricsSocket } from "#/lib/websocket";

export const Route = createFileRoute("/_app")({
	component: RouteComponent,
});

function RouteComponent() {
	const location = useLocation();

	useEffect(() => {
		connectMetricsSocket();
	}, []);

	const currentLabel = sidebarItems.find(
		(item) => item.href === location.pathname,
	)?.label;

	return (
		<SidebarProvider>
			<AppSidebar />
			<SidebarInset>
				<header className="flex h-12 shrink-0 items-center gap-3 border-b border-border bg-background px-4">
					<SidebarTrigger className="-ml-1 text-foreground" />
					<Separator orientation="vertical" className="h-4" />
					<span className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
						{currentLabel ?? "—"}
					</span>
				</header>
				<div className="flex-1 min-h-0 flex flex-col">
					<Outlet />
				</div>
			</SidebarInset>
		</SidebarProvider>
	);
}
