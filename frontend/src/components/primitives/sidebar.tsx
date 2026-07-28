// frontend/src/components/primitives/sidebar.tsx
import { Link, useLocation } from "@tanstack/react-router";
import { sidebarItems } from "#/data/sidebar";
import {
  Sidebar,
  SidebarContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "../ui/sidebar";

export default function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const location = useLocation();
  return (
    <Sidebar className="bg-background text-foreground" collapsible="offcanvas" {...props}>
      <SidebarHeader className="border-b border-border px-3 py-4">
        <p className="text-xl tracking-tight font-medium">UMaT 5G SDN</p>
      </SidebarHeader>
      <SidebarContent>
        <SidebarMenu>
          {sidebarItems.map((item) => (
            <SidebarMenuItem key={item.label}>
              <SidebarMenuButton
                asChild
                isActive={location.pathname === item.href}
                className="rounded-none"
              >
                <Link to={item.href} className="flex items-center gap-2">
                  <item.icon className="size-4" />
                  <span className="font-mono text-[11px] uppercase tracking-wider">
                    {item.label}
                  </span>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarContent>
    </Sidebar>
  );
}
