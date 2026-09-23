import { createContext } from 'react'
import type { AppSettings, MotionPreference, ResolvedTheme, ThemeMode } from '../../shared/types/settings'

export interface SettingsContextValue {
  settings: AppSettings
  resolvedTheme: ResolvedTheme
  isMotionReduced: boolean
  setTheme: (theme: ThemeMode) => void
  toggleTheme: () => void
  setMotionPreference: (motion: MotionPreference) => void
  setCompactResults: (compact: boolean) => void
  resetSettings: () => void
}

export const SettingsContext = createContext<SettingsContextValue | null>(null)