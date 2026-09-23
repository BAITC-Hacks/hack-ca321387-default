import { Input } from '@chakra-ui/react'
import type { Metadata, SearchParams } from '../../shared/types/match'
import { formatKZT } from '../../shared/format'

export type SearchErrors = Partial<Record<keyof SearchParams, string>>

interface SearchFieldsProps {
  value: SearchParams
  options: Metadata
  errors: SearchErrors
  update: <K extends keyof SearchParams>(key: K, value: SearchParams[K]) => void
}

function FieldError({ name, message }: { name: string; message?: string }) {
  return message ? <small id={`error-${name}`} className="field-error">{message}</small> : null
}

export function SearchFields({ value, options, errors, update }: SearchFieldsProps) {
  return (
    <div className="search-grid">
      <label className="field" htmlFor="field-city"><span>Город *</span>
        <select id="field-city" className="control" value={value.city} onChange={(event) => update('city', event.target.value)} aria-invalid={!!errors.city} aria-describedby={errors.city ? 'error-city' : undefined}>
          <option value="">Выберите город</option>
          {options.cities.map((city) => <option key={city} value={city}>{city}</option>)}
        </select>
        <FieldError name="city" message={errors.city} />
      </label>

      <label className="field" htmlFor="field-date"><span>Дата мероприятия *</span>
        <Input id="field-date" className="control" type="date" min={options.min_date} max={options.max_date} value={value.date} onChange={(event) => update('date', event.target.value)} aria-invalid={!!errors.date} aria-describedby={errors.date ? 'error-date' : undefined} />
        <FieldError name="date" message={errors.date} />
      </label>

      <label className="field" htmlFor="field-event_type"><span>Тип мероприятия *</span>
        <select id="field-event_type" className="control" value={value.event_type} onChange={(event) => update('event_type', event.target.value)} aria-invalid={!!errors.event_type} aria-describedby={errors.event_type ? 'error-event_type' : undefined}>
          <option value="">Выберите формат</option>
          {options.event_types.map((item) => <option key={item} value={item}>{item[0].toLocaleUpperCase('ru-RU') + item.slice(1)}</option>)}
        </select>
        <FieldError name="event_type" message={errors.event_type} />
      </label>

      <label className="field" htmlFor="field-category"><span>Категория подрядчика *</span>
        <select id="field-category" className="control" value={value.category} onChange={(event) => update('category', event.target.value)} aria-invalid={!!errors.category} aria-describedby={errors.category ? 'error-category' : undefined}>
          <option value="">Выберите категорию</option>
          {options.categories.map((item) => <option key={item} value={item}>{item}</option>)}
        </select>
        <FieldError name="category" message={errors.category} />
      </label>

      <label className="field" htmlFor="field-budget"><span>Бюджет *</span>
        <div className="input-suffix">
          <Input id="field-budget" className="control" type="text" inputMode="numeric" autoComplete="off" value={value.budget ? formatKZT(value.budget).replace(' ₸', '') : ''} onChange={(event) => update('budget', Number(event.target.value.replace(/\D/g, '')))} placeholder="800 000" aria-invalid={!!errors.budget} aria-describedby={errors.budget ? 'error-budget' : undefined} />
          <span aria-hidden="true">₸</span>
        </div>
        <FieldError name="budget" message={errors.budget} />
      </label>

      <label className="field" htmlFor="field-language"><span>Язык</span>
        <select id="field-language" className="control" value={value.language || ''} onChange={(event) => update('language', event.target.value || undefined)}>
          <option value="">Не важно</option>
          {options.languages.map((item) => <option key={item} value={item}>{item[0].toLocaleUpperCase('ru-RU') + item.slice(1)}</option>)}
        </select>
      </label>

      <label className="field" htmlFor="field-duration"><span>Длительность</span>
        <select id="field-duration" className="control" value={value.duration || ''} onChange={(event) => update('duration', event.target.value ? Number(event.target.value) : undefined)} aria-invalid={!!errors.duration} aria-describedby={errors.duration ? 'error-duration' : undefined}>
          <option value="">Не важно</option>
          {Array.from({ length: 12 }, (_, index) => index + 1).map((hours) => <option key={hours} value={hours}>{hours} ч</option>)}
        </select>
        <FieldError name="duration" message={errors.duration} />
      </label>
    </div>
  )
}
