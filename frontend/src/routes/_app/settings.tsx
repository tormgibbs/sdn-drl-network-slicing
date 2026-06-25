import { createFileRoute } from '@tanstack/react-router'
import { SettingsPage } from '../../settings/SettingsPage'

export const Route = createFileRoute('/_app/settings')({
  component: SettingsPage,
})