import { createFileRoute } from '@tanstack/react-router'
import { SettingsPage } from '../../settings/settings-page'

export const Route = createFileRoute('/_app/settings')({
  component: SettingsPage,
})