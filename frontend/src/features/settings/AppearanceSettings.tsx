import type { MotionPreference, ThemeMode } from '../../shared/types/settings'
import { useSettings } from './useSettings'

const themeChoices: { value: ThemeMode; label: string; preview: string }[] = [
  { value: 'light', label: 'Светлая', preview: 'theme-preview-light' },
  { value: 'dark', label: 'Тёмная', preview: 'theme-preview-dark' },
  { value: 'system', label: 'Система', preview: 'theme-preview-system' },
]

const motionChoices: { value: MotionPreference; label: string }[] = [
  { value: 'system', label: 'Система' },
  { value: 'reduced', label: 'Уменьшенная' },
  { value: 'full', label: 'Полная' },
]

export function AppearanceSettings() {
  const { settings, setTheme, setMotionPreference, setCompactResults } = useSettings()

  return (
    <>
      <section className="settings-section" aria-labelledby="appearance-title">
        <div className="settings-section-heading">
          <h3 id="appearance-title">Внешний вид</h3>
          <p>Выберите оформление и поведение анимации.</p>
        </div>
        <fieldset className="settings-fieldset">
          <legend>Тема</legend>
          <div className="theme-options">
            {themeChoices.map((choice) => (
              <button
                className={`theme-choice ${settings.theme === choice.value ? 'is-selected' : ''}`}
                type="button"
                key={choice.value}
                aria-pressed={settings.theme === choice.value}
                onClick={() => setTheme(choice.value)}
              >
                <span className={`theme-preview ${choice.preview}`} aria-hidden="true"><i /><i /><i /></span>
                <span>{choice.label}</span>
              </button>
            ))}
          </div>
        </fieldset>
        <fieldset className="settings-fieldset">
          <legend>Движение</legend>
          <div className="motion-options">
            {motionChoices.map((choice) => (
              <button
                className={`motion-choice ${settings.reducedMotion === choice.value ? 'is-selected' : ''}`}
                type="button"
                key={choice.value}
                aria-pressed={settings.reducedMotion === choice.value}
                onClick={() => setMotionPreference(choice.value)}
              >
                {choice.label}
              </button>
            ))}
          </div>
          <p className="settings-hint">«Система» учитывает настройку уменьшения движения в ОС.</p>
        </fieldset>
      </section>

      <section className="settings-section" aria-labelledby="results-settings-title">
        <div className="settings-section-heading">
          <h3 id="results-settings-title">Результаты</h3>
          <p>Управляйте объёмом информации в карточках.</p>
        </div>
        <label className="settings-checkbox">
          <input
            type="checkbox"
            checked={settings.compactResults}
            onChange={(event) => setCompactResults(event.target.checked)}
          />
          <span><strong>Компактные карточки</strong><small>Скрывать подробности, пока вы их не откроете.</small></span>
        </label>
      </section>

      <section className="settings-section interface-setting" aria-labelledby="interface-title">
        <div className="settings-section-heading">
          <h3 id="interface-title">Интерфейс</h3>
        </div>
        <div className="language-setting"><span>Язык интерфейса</span><strong>Русский</strong></div>
      </section>
    </>
  )
}
