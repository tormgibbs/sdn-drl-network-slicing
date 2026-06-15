import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_app/agent')({
  component: RouteComponent,
})

function RouteComponent() {
  return <div className="text-foreground">Hello "/agent"!</div>;
}
