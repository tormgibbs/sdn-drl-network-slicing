import { createFileRoute } from '@tanstack/react-router'
import { StudentPortalSlice } from '../../../slice/StudentPortalSlice'

export const Route = createFileRoute('/_app/slices/student-portal')({
  component: StudentPortalSlice,
})