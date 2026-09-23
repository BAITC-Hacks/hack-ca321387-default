import type { AvailabilityDay } from '../../types/match'
import { formatDate, pluralVariants } from '../../utils/format'

export function DateNavigator({ days, selected, pending, onSelect }: { days: AvailabilityDay[]; selected: string; pending: boolean; onSelect: (date: string) => void }) {
  if (days.length < 2 || !days.some((day) => day.date !== selected && day.available > 0)) return null
  return (
    <section className="date-navigator" aria-labelledby="dates-title">
      <div className="date-heading"><span className="eyebrow">Календарь</span><h3 id="dates-title">Соседние даты</h3><p>Число вариантов рассчитано для тех же параметров поиска.</p></div>
      <div className="date-strip" role="group" aria-label="Выбрать другую дату">
        {days.map((day) => <button key={day.date} type="button" className={`date-tile ${day.date === selected ? 'is-selected' : ''}`} onClick={() => onSelect(day.date)} disabled={pending || day.date === selected} aria-pressed={day.date === selected}>
          <span>{formatDate(day.date, true)}</span><strong>{day.available}</strong><small>{pluralVariants(day.available)}</small>
        </button>)}
      </div>
    </section>
  )
}
