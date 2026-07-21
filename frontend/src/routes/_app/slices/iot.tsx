import { createFileRoute } from '@tanstack/react-router'
import { IoTSlice } from '../../../slice/IoTSlice'
export const Route = createFileRoute('/_app/slices/iot')({
  component: IoTSlice,
})