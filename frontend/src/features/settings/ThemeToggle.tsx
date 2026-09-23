import { useSettings } from './useSettings'

export function ThemeToggle() {
  const { resolvedTheme, toggleTheme } = useSettings()
  const nextTheme = resolvedTheme === 'light' ? 'тёмную' : 'светлую'

  return (
    <button
      className="icon-button theme-toggle"
      type="button"
      onClick={toggleTheme}
      aria-label={`Переключить на ${nextTheme} тему`}
      title={`Переключить на ${nextTheme} тему`}
    >
      {resolvedTheme === 'light' ? (
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.2 15.1A8.4 8.4 0 0 1 8.9 3.8a8.6 8.6 0 1 0 11.3 11.3Z" /></svg>
      ) : (
        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3.8" /><path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42" /></svg>
      )}
    </button>
  )
}
