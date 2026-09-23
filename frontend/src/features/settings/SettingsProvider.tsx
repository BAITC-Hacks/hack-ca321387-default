import { createContext, useCallback, useEffect, useLayoutEffect, useMemo, useState, type ReactNode } from 'react'
import { themePalettes } from '../../app/theme'
import { DEFAULT_SETTINGS, type AppSettings, type MotionPreference, type ResolvedTheme, type ThemeMode } from '../../shared/types/settings'

const SETTINGS_KEY = 'eventlens.settings'

interface SettingsContextValue {
  settings: AppSettings
  resolvedTheme: ResolvedTheme
  isMotionReduced: boolean
  setTheme: (theme: ThemeMode) => void
  toggleTheme: () => void
  setMotionPreference: (motion: MotionPreference) => void
  setCompactResults: (compact: boolean) => void
  resetSettings: () => void
}

const SettingsContext = createContext<SettingsContextValue | null>(null)

function readSettings(): AppSettings {
  try {
    const raw = window.localStorage.getItem(SETTINGS_KEY)
    if (!raw) return DEFAULT_SETTINGS
    const saved: unknown = JSON.parse(raw)
    if (!saved || typeof saved !== 'object') return DEFAULT_SETTINGS

    const value = saved as Partial<AppSettings>
    return {
      theme: value.theme === 'light' || value.theme === 'dark' || value.theme === 'system' ? value.theme : DEFAULT_SETTINGS.theme,
      reducedMotion: value.reducedMotion === 'reduced' || value.reducedMotion === 'full' || value.reducedMotion === 'system'
        ? value.reducedMotion
        : DEFAULT_SETTINGS.reducedMotion,
      compactResults: typeof value.compactResults === 'boolean' ? value.compactResults : DEFAULT_SETTINGS.compactResults,
    }
  } catch {
    return DEFAULT_SETTINGS
  }
}

function saveSettings(settings: AppSettings) {
  try {
    window.localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings))
  } catch {
    // The app remains usable when browser storage is blocked or full.
  }
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState(readSettings)
  const [systemDark, setSystemDark] = useState(() => window.matchMedia('(prefers-color-scheme: dark)').matches)
  const [systemReduced, setSystemReduced] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches)

  useEffect(() => {
    const colorQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    const onColorChange = (event: MediaQueryListEvent) => setSystemDark(event.matches)
    const onMotionChange = (event: MediaQueryListEvent) => setSystemReduced(event.matches)
    colorQuery.addEventListener('change', onColorChange)
    motionQuery.addEventListener('change', onMotionChange)
    return () => {
      colorQuery.removeEventListener('change', onColorChange)
      motionQuery.removeEventListener('change', onMotionChange)
    }
  }, [])

  const resolvedTheme: ResolvedTheme = settings.theme === 'system' ? (systemDark ? 'dark' : 'light') : settings.theme
  const isMotionReduced = settings.reducedMotion === 'system' ? systemReduced : settings.reducedMotion === 'reduced'

  useLayoutEffect(() => {
    const root = document.documentElement
    root.dataset.theme = resolvedTheme
    root.dataset.motion = isMotionReduced ? 'reduced' : 'full'
    root.style.colorScheme = resolvedTheme
    Object.entries(themePalettes[resolvedTheme]).forEach(([name, value]) => root.style.setProperty(name, value))
  }, [resolvedTheme, isMotionReduced])

  const update = useCallback((next: AppSettings) => {
    setSettings(next)
    saveSettings(next)
  }, [])

  const value = useMemo<SettingsContextValue>(() => ({
    settings,
    resolvedTheme,
    isMotionReduced,
    setTheme: (theme) => update({ ...settings, theme }),
    toggleTheme: () => update({ ...settings, theme: resolvedTheme === 'light' ? 'dark' : 'light' }),
    setMotionPreference: (reducedMotion) => update({ ...settings, reducedMotion }),
    setCompactResults: (compactResults) => update({ ...settings, compactResults }),
    resetSettings: () => update(DEFAULT_SETTINGS),
  }), [settings, resolvedTheme, isMotionReduced, update])

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>
}

export { SettingsContext }
