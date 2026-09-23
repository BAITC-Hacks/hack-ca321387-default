import type { MatchResponse, SearchParams } from '../../types/match'
import { ContractorCard } from './ContractorCard'
import { ConstraintDoctor } from '../diagnostics/ConstraintDoctor'
import { DateNavigator } from '../availability/DateNavigator'

interface Props {
  response?: MatchResponse
  query?: SearchParams
  pending: boolean
  error: string | null
  onRetry: () => void
  onFocusField: (field: 'city' | 'category') => void
  onDateSelect: (date: string) => void
}

export function ResultsSection({ response, query, pending, error, onRetry, onFocusField, onDateSelect }: Props) {
  if (pending) return <section className="results-section" aria-live="polite" aria-busy="true"><p className="eyebrow">02 / Результаты</p><h2>Проверяем доступность подрядчиков…</h2><div className="skeleton-grid">{[1, 2, 3].map((item) => <div className="skeleton-card" key={item}><i /><i /><i /><i /></div>)}</div></section>
  if (error) return <section className="results-section" role="alert"><p className="eyebrow">02 / Результаты</p><div className="state-panel error-panel"><span className="state-mark" aria-hidden="true">!</span><h2>Не удалось получить результаты</h2><p>{error}</p><button type="button" className="secondary-button" onClick={onRetry}>Повторить запрос</button></div></section>
  if (!response) return <section className="results-section initial-flow" aria-labelledby="start-title"><p className="eyebrow">02 / Что дальше</p><h2 id="start-title">От запроса к ясному выбору</h2><div className="flow-steps"><div><span>01</span><strong>Укажите параметры</strong><p>Дата, город и условия мероприятия.</p></div><div><span>02</span><strong>Проверим ограничения</strong><p>Оставим доступных подрядчиков.</p></div><div><span>03</span><strong>Объясним рекомендации</strong><p>Покажем факты по каждому профилю.</p></div></div></section>

  const count = response.results.length
  const lexicalMode = response.model_info.semantic_model === 'tfidf-v1'
  return <section className="results-section" aria-live="polite" aria-labelledby="results-title">
    <div className="results-heading"><p className="eyebrow">02 / Результаты поиска</p>
      <h2 id="results-title">{response.status === 'matched' ? `Найдено ${count} ${count === 1 ? 'подходящий вариант' : count < 5 ? 'подходящих варианта' : 'подходящих вариантов'}` : response.status === 'category_not_found' ? 'В этой категории пока никого нет' : 'Подходящих вариантов нет'}</h2>
      <p>{response.diagnostics.summary}</p>
      {response.model_info.semantic_model === 'unavailable' && <p role="status">Текстовая оценка временно недоступна. Порядок рассчитан по бюджету и применимой длительности.</p>}
      {response.model_info.semantic_model === 'disabled' && <p>Текстовая оценка отключена; используются бюджет и применимая длительность.</p>}
    </div>
    {response.status === 'matched' ? <div className="cards-grid">{response.results.slice(0, 3).map((contractor, index) => <ContractorCard key={contractor.id} contractor={contractor} index={index} lexicalMode={lexicalMode} />)}</div> :
      <div className="no-result-layout"><ConstraintDoctor diagnostics={response.diagnostics} />{response.status === 'category_not_found' && <div className="field-change"><p>Попробуйте другой город или категорию.</p><div><button className="secondary-button" type="button" onClick={() => onFocusField('city')}>Изменить город</button><button className="secondary-button" type="button" onClick={() => onFocusField('category')}>Изменить категорию</button></div></div>}</div>}
    {response.status !== 'category_not_found' && response.availability && query && <DateNavigator days={response.availability} selected={query.date} pending={pending} onSelect={onDateSelect} />}
  </section>
}
