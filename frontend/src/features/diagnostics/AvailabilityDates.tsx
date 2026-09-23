import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { AvailabilityDay, SearchParams } from '../../shared/types/match'
import { getAvailability } from '../../shared/api/discovery.api'
import { formatDate, pluralVariants } from '../../shared/format'

export function AvailabilityDates({ days, selected, pending, onSelect, query }: {
  days: AvailabilityDay[]
  selected: string
  pending: boolean
  onSelect: (date: string) => void
  query: SearchParams
}) {
  const [expanded, setExpanded] = useState(false)
  const calendar = useQuery({
    queryKey: ['availability', query], queryFn: () => getAvailability(query),
    enabled: expanded, staleTime: 60_000, retry: 1,
  })
  const shown = expanded && calendar.data ? calendar.data.days : days
  if (days.length < 2) return null

  return <section className="date-navigator" aria-labelledby="dates-title">
    <div className="date-heading">
      <span className="eyebrow">Календарь</span>
      <h3 id="dates-title">Доступность по датам</h3>
      <p>Количество подходящих подрядчиков при тех же условиях поиска.</p>
    </div>
    <div className="date-strip" role="group" aria-label="Выбрать другую дату">
      {shown.map((day) => <button key={day.date} type="button" className={`date-tile ${day.date === selected ? 'is-selected' : ''}`} onClick={() => onSelect(day.date)} disabled={pending || day.date === selected} aria-pressed={day.date === selected}>
        <span>{formatDate(day.date, true)}</span><strong>{day.available}</strong><small>{pluralVariants(day.available)}</small>
      </button>)}
    </div>
    {expanded && calendar.data?.recommended_date && <p className="date-recommendation">Больше вариантов: {formatDate(calendar.data.recommended_date, true)}</p>}
    {expanded && calendar.isPending && <p role="status">Загружаем расширенный календарь…</p>}
    {expanded && calendar.isError && <p role="alert">Календарь недоступен. <button type="button" onClick={() => void calendar.refetch()}>Повторить</button></p>}
    <button type="button" className="secondary-button date-expand" aria-expanded={expanded} onClick={() => setExpanded((value) => !value)}>
      {expanded ? 'Показать ближайшие даты' : 'Показать до 29 дней'}
    </button>
  </section>
}
