import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getMatchDetails } from '../../shared/api/discovery.api'
import type { SearchParams } from '../../shared/types/match'
import { percent } from '../../shared/format'

const componentLabels: Record<string, string> = {
  semantic: 'Сходство описания', lexical: 'Текстовое совпадение',
  budget: 'Бюджет', duration: 'Длительность',
}

export function RankingDetails({ query, dataVersion }: { query: SearchParams; dataVersion: string }) {
  const [open, setOpen] = useState(false)
  const details = useQuery({
    queryKey: ['match-details', query], queryFn: () => getMatchDetails(query),
    enabled: open, staleTime: 60_000, retry: 1,
  })

  return <section className="ranking-details" aria-labelledby="ranking-details-title">
    <button type="button" className="secondary-button" aria-expanded={open} onClick={() => setOpen((value) => !value)}>
      {open ? 'Скрыть расчёт' : 'Как рассчитан рейтинг и порядок?' }
    </button>
    {open && <div className="ranking-details-body">
      <h3 id="ranking-details-title">Разбор ранжирования</h3>
      {details.isPending ? <p role="status">Загружаем расчёт…</p>
        : details.isError ? <div role="alert">Не удалось загрузить расчёт. <button type="button" onClick={() => void details.refetch()}>Повторить</button></div>
          : details.data.match.model_info.data_version !== dataVersion
            ? <p role="alert">Каталог изменился после поиска. Повторите подбор для актуального сравнения.</p>
            : <>
              <p>Оценка показывает соответствие условиям, а не вероятность успеха.</p>
              <div className="ranking-details-grid">
                {details.data.ranking.map((entry) => {
                  const contractor = details.data.match.results.find((item) => item.id === entry.candidate_id)
                  return <article className="ranking-detail" key={entry.candidate_id}>
                    <h4>{entry.position}. {contractor?.name ?? entry.candidate_id} <span>{percent(entry.score)}</span></h4>
                    {entry.components.map((component) => <div className="ranking-component" key={component.component}>
                      <strong>{componentLabels[component.component]}</strong>
                      <span>{component.contribution === null ? '—' : `+${percent(component.contribution)}`}</span>
                      <p>{component.reason}</p>
                    </div>)}
                  </article>
                })}
              </div>
              {details.data.comparison.decisions.length > 0 && <div className="ranking-comparison">
                <h4>Почему такой порядок</h4>
                {details.data.comparison.decisions.map((decision) => <p key={`${decision.higher_id}-${decision.lower_id}`}>
                  {details.data.match.results.find((item) => item.id === decision.higher_id)?.name ?? decision.higher_id} выше
                  {' '}{details.data.match.results.find((item) => item.id === decision.lower_id)?.name ?? decision.lower_id}: {decision.reason}
                </p>)}
              </div>}
              <p className="ranking-price-note">{details.data.comparison.price_note}</p>
            </>}
    </div>}
  </section>
}
