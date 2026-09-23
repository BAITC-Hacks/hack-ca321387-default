import type { Diagnostics } from '../../shared/types/match'

const fallbackStages = [
  ['category', 'В категории'], ['city', 'В выбранном городе'],
  ['date', 'Свободны на дату'], ['available_date', 'Свободны на дату'],
  ['format', 'Подходят по формату'], ['budget', 'В пределах бюджета'],
  ['language', 'Работают на языке'], ['duration', 'Подходят по длительности'],
] as const

export function ConstraintDoctor({ diagnostics }: { diagnostics?: Diagnostics }) {
  const steps = diagnostics?.steps || fallbackStages
    .filter(([stage]) => diagnostics?.counts?.[stage] !== undefined)
    .map(([stage, label]) => ({ stage, label, count: diagnostics?.counts?.[stage] || 0 }))
  if (!steps.length) return diagnostics?.summary ? <p className="doctor-summary">{diagnostics.summary}</p> : null
  const blocker = diagnostics?.primary_blocker || steps.find((step, index) => index > 0 && step.count === 0)?.stage
  return (
    <section className="doctor-panel" aria-labelledby="doctor-title">
      <span className="eyebrow">Диагностика поиска</span>
      <h3 id="doctor-title">Что ограничило поиск</h3>
      <div className="doctor-steps">
        {steps.map((step, index) => <div className={`doctor-step ${step.stage === blocker ? 'is-blocker' : ''}`} key={step.stage}>
          <div className="doctor-index">{String(index + 1).padStart(2, '0')}</div>
          <div className="doctor-description"><strong>{step.label}</strong><span>{index > 0 ? `−${Math.max(0, steps[index - 1].count - step.count)} после проверки` : 'Исходный набор'}</span></div>
          <div className="doctor-count">{step.count}</div>
        </div>)}
      </div>
      {diagnostics?.summary && <p className="doctor-summary">{diagnostics.summary}</p>}
    </section>
  )
}
