import { formatKZT } from '../../shared/format'
import type { Diagnostics } from '../../shared/types/match'
import { GlassPanel } from '../../shared/ui/GlassPanel'

export function ConstraintDoctor({ diagnostics }: { diagnostics?: Diagnostics }) {
  const steps = diagnostics?.steps || []
  if (!steps.length) return diagnostics?.summary ? <p className="doctor-summary">{diagnostics.summary}</p> : null
  const blocker = diagnostics?.primary_blocker || steps.find((step, index) => index > 0 && step.count === 0)?.stage
  return (
    <GlassPanel as="section" className="doctor-panel" aria-labelledby="doctor-title">
      <span className="eyebrow">Диагностика поиска</span>
      <h3 id="doctor-title">Что ограничило поиск</h3>
      <div className="doctor-steps">
        {steps.map((step, index) => <div className={`doctor-step ${step.stage === blocker ? 'is-blocker' : ''}`} key={step.stage}>
          <div className="doctor-index">{String(index + 1).padStart(2, '0')}</div>
          <div className="doctor-description"><strong>{step.label}</strong><span>{`${step.before} → ${step.after}; исключено ${step.excluded}`}</span></div>
          <div className="doctor-count">{step.count}</div>
        </div>)}
      </div>
      {diagnostics?.budget_alternative && <p className="doctor-summary">При бюджете {formatKZT(diagnostics.budget_alternative.budget)} подходят {diagnostics.budget_alternative.available} кандидатов. Остальные условия сохранены.</p>}
      {diagnostics?.summary && <p className="doctor-summary">{diagnostics.summary}</p>}
    </GlassPanel>
  )
}
