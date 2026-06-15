import AppSidebar from '#/components/primitives/sidebar'
import { SidebarInset, SidebarProvider } from '#/components/ui/sidebar'
import { createFileRoute, Outlet } from '@tanstack/react-router'

export const Route = createFileRoute('/_app')({
  component: RouteComponent,
})

function RouteComponent() {
  return (
    <SidebarProvider>
      <AppSidebar/>
      <SidebarInset>
        <Outlet/>
      </SidebarInset>
    </SidebarProvider>
  )
}
