import { createFileRoute } from '@tanstack/react-router'
export const Route = createFileRoute('/_app/')({ component: Home })

function Home() {
  return (
   <div className='text-foreground'>Hello "/dashboard"!</div>

  )
}
