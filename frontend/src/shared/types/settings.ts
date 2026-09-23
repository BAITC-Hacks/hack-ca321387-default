export type ThemeMode = 'light' | 'dark' | 'system'
export type MotionPreference = 'system' | 'reduced' | 'full'
export type ResolvedTheme = 'light' | 'dark'

export interface AppSettings {
  theme: ThemeMode
  reducedMotion: MotionPreference
  compactResults: boolean
}

export const DEFAULT_SETTINGS: AppSettings = {
  theme: 'system',
  reducedMotion: 'system',
  compactResults: false,
}
