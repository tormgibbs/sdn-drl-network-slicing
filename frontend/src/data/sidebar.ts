// frontend/src/data/sidebar.ts
import type { SideBarItem } from "#/types/dashboard";
import { Bot, Layers3, LayoutDashboard } from "lucide-react";

export const sidebarItems: SideBarItem[] = [
    {
       icon: LayoutDashboard,
       href: "/",
       label: "Dashboard"
    },
    {
       icon: Layers3,
       href: "/slices",
       label: "Slices"
    },
    {
       icon: Bot,
       href: "/controller",
       label: "Controller"
    },
]
