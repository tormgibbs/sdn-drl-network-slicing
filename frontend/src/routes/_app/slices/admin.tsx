import { createFileRoute } from '@tanstack/react-router'
import { AdminSlice } from '../../../slice/AdminSlice'
export const Route = createFileRoute('/_app/slices/admin')({
  component: AdminSlice,
})