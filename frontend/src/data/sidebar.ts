import type { SideBarItem } from "#/types/dashboard";
import { Bot, Layers3, LayoutDashboard, Settings } from "lucide-react";

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
       href: "/agent",
       label: "Agent" 
    },
    {
       icon: Settings,
       href: "/settings",
       label: "Settings" 
    },
    
]