import { createFileRoute } from '@tanstack/react-router'
import { VLESlice } from '../../../slice/VLESlice'

export const Route = createFileRoute('/_app/slices/vle')({
  component: VLESlice,
})