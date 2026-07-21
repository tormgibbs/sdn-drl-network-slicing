import { createFileRoute } from '@tanstack/react-router';
import { GeneralSlice } from '../../../slice/GeneralSlice';
export const Route = createFileRoute('/_app/slices/general')({
  component: GeneralSlice,
})