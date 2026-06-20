import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_app/slices')({
  component: RouteComponent,
})

function RouteComponent() {
  return <div className="text-foreground">Hello "/slices"!</div>;
}
