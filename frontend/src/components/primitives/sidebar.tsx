import { Sidebar, SidebarContent, SidebarHeader, SidebarMenu, SidebarMenuButton, SidebarMenuItem } from "../ui/sidebar"
import { sidebarItems } from "#/data/sidebar"
import { Link } from "@tanstack/react-router"
import { useLocation } from "@tanstack/react-router";

export default function AppSidebar({ ...props}: React.ComponentProps<typeof Sidebar>) {
    const location = useLocation();
    return (
      <Sidebar className="dark bg-background text-foreground" { ...props}>
        <SidebarHeader>
          <div className="flex flex-col gap-2 leading-none">
            <p className="font-medium text-3xl">UMaT 5G SDN</p>
          </div>
        </SidebarHeader>
        <SidebarContent>
          <SidebarMenu>
            {sidebarItems.map((item) => (
              <SidebarMenuItem key={item.label}>
                <SidebarMenuButton asChild isActive={location.pathname === item.href}>
                  <Link to={item.href} className="flex items-center gap-2">
                  <item.icon className="size-4"/>
                  <span>{item.label}</span>
                  </Link>

                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarContent>
      </Sidebar>
    );
}