import type { MatchResponse, SearchParams } from '../../shared/types/match'
import { AvailabilityDates } from '../diagnostics/AvailabilityDates'
import { ConstraintDoctor } from '../diagnostics/ConstraintDoctor'
import { ContractorCard } from './ContractorCard'

interface ResultsSectionProps {
  response?: MatchResponse
  query?: SearchParams
  pending: boolean
  error: string | null
  onRetry: () => void
  onFocusField: (field: 'city' | 'category') => void
  onDateSelect: (date: string) => void
}

const resultCount = (count: number) => {
  if (count === 1) return 'подходящий вариант'
  if (count % 10 >= 2 && count % 10 <= 4 && (count % 100 < 12 || count % 100 > 14)) return 'подходящих варианта'
  return 'подходящих вариантов'
}

function LoadingResults() {
  return (
    <section className="results-section" aria-live="polite" aria-busy="true">
      <p className="eyebrow">02 / Результаты</p>
      <h2>Проверяем доступность подрядчиков…</h2>
      <div className="skeleton-grid" aria-hidden="true">
        {[1, 2, 3].map((item) => <div className="skeleton-card" key={item}><i /><i /><i /><i /></div>)}
      </div>
    </section>
  )
}

function InitialResults() {
  return (
    <section className="results-section initial-flow" aria-labelledby="start-title">
      <p className="eyebrow">02 / Что дальше</p>
      <h2 id="start-title">От запроса к ясному выбору</h2>
      <div className="flow-steps">
        <div><span>01</span><strong>Укажите параметры</strong><p>Дата, город и условия мероприятия.</p></div>
        <div><span>02</span><strong>Проверим ограничения</strong><p>Оставим доступных подрядчиков.</p></div>
        <div><span>03</span><strong>Объясним рекомендации</strong><p>Покажем факты по каждому профилю.</p></div>
      </div>
    </section>
  )
}

function ErrorResults({ error, onRetry }: { error: string; onRetry: () => void }) {
  return (
    <section className="results-section" role="alert">
      <p className="eyebrow">02 / Результаты</p>
      <div className="state-panel error-panel">
        <span className="state-mark" aria-hidden="true">!</span>
        <h2>Не удалось получить результаты</h2>
        <p>{error}</p>
        <button type="button" className="secondary-button" onClick={onRetry}>Повторить запрос</button>
      </div>
    </section>
  )
}

export function ResultsSection({ response, query, pending, error, onRetry, onFocusField, onDateSelect }: ResultsSectionProps) {
  if (pending) return <LoadingResults />
  if (error) return <ErrorResults error={error} onRetry={onRetry} />
  if (!response) return <InitialResults />

  const count = response.results.length
  const lexicalMode = response.model_info?.semantic_model === 'tfidf-v1'
  const matched = response.status === 'matched'
  const categoryMissing = response.status === 'category_not_found'
  const title = matched
    ? `Найдено ${count} ${resultCount(count)}`
    : categoryMissing ? 'В этой категории пока никого нет' : 'Подходящих вариантов нет'
  const summary = matched
    ? count < 3
      ? 'Все показанные подрядчики свободны на выбранную дату. Другие не прошли обязательные условия.'
      : 'Все показанные подрядчики свободны на выбранную дату и прошли обязательные условия.'
    : categoryMissing
      ? 'В выбранном городе нет подрядчиков этой категории. Измените город или категорию.'
      : 'Посмотрите, на каком условии закончились кандидаты.'

  return (
    <section className="results-section" aria-live="polite" aria-labelledby="results-title">
      <div className="results-heading">
        <p className="eyebrow">02 / Результаты поиска</p>
        <h2 id="results-title">{title}</h2>
        <p>{summary}</p>
      </div>

      {matched ? (
        <div className="cards-grid">
          {response.results.slice(0, 3).map((contractor, index) => (
            <ContractorCard key={contractor.id} contractor={contractor} index={index} lexicalMode={lexicalMode} />
          ))}
        </div>
      ) : (
        <div className="no-result-layout">
          <ConstraintDoctor diagnostics={response.diagnostics} />
          {categoryMissing && (
            <div className="field-change">
              <p>Попробуйте другой город или категорию.</p>
              <div>
                <button className="secondary-button" type="button" onClick={() => onFocusField('city')}>Изменить город</button>
                <button className="secondary-button" type="button" onClick={() => onFocusField('category')}>Изменить категорию</button>
              </div>
            </div>
          )}
        </div>
      )}

      {!categoryMissing && response.availability && query && (
        <AvailabilityDates days={response.availability} selected={query.date} pending={pending} onSelect={onDateSelect} />
      )}
    </section>
  )
}
