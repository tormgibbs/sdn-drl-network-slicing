import AppSidebar from '#/components/primitives/sidebar'
import { SidebarInset, SidebarProvider, SidebarTrigger } from '#/components/ui/sidebar'
import { createFileRoute, Outlet } from '@tanstack/react-router'
import { useEffect } from 'react'
import { connectMetricsSocket } from '#/lib/websocket'

export const Route = createFileRoute('/_app')({
  component: RouteComponent,
})

function RouteComponent() {
  useEffect(() => {
    connectMetricsSocket()
  }, [])

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header>
          <SidebarTrigger className='text-foreground' /> 
        </header>
        <Outlet />
      </SidebarInset>
    </SidebarProvider>
  );
}