import { Box, Button, Flex, Heading, Input, Text } from '@chakra-ui/react'
import { useState, type FormEvent } from 'react'
import { GlassPanel } from '../ui/GlassPanel'
import type { Metadata, SearchParams } from '../../types/match'
import { FALLBACK_METADATA } from '../../constants/app'
import { formatKZT } from '../../utils/format'

type Errors = Partial<Record<keyof SearchParams, string>>

interface Props {
  value: SearchParams
  onChange: (value: SearchParams) => void
  onSubmit: (value: SearchParams) => void
  metadata?: Metadata
  pending: boolean
}

export function SearchPanel({ value, onChange, onSubmit, metadata, pending }: Props) {
  const [errors, setErrors] = useState<Errors>({})
  const options = metadata || FALLBACK_METADATA
  const update = <K extends keyof SearchParams>(key: K, next: SearchParams[K]) => {
    onChange({ ...value, [key]: next })
    setErrors((current) => ({ ...current, [key]: undefined }))
  }
  const submit = (event: FormEvent) => {
    event.preventDefault()
    const next: Errors = {}
    if (!value.city) next.city = 'Выберите город.'
    if (!value.date || value.date < options.min_date || value.date > options.max_date) next.date = 'Выберите дату в диапазоне каталога.'
    if (!value.event_type) next.event_type = 'Выберите тип мероприятия.'
    if (!value.category) next.category = 'Выберите категорию.'
    if (!Number.isFinite(value.budget) || value.budget <= 0 || value.budget > 100_000_000) next.budget = 'Укажите бюджет от 1 до 100 000 000 ₸.'
    if (value.duration !== undefined && (value.duration <= 0 || value.duration > 12)) next.duration = 'Выберите длительность до 12 часов.'
    setErrors(next)
    const first = Object.keys(next)[0]
    if (first) {
      document.getElementById(`field-${first}`)?.focus()
      return
    }
    onSubmit(value)
  }

  return (
    <GlassPanel className="search-panel" as="section" aria-labelledby="search-title">
      <Flex justify="space-between" align="start" gap={4} mb={7} wrap="wrap">
        <Box>
          <Text className="eyebrow">01 / Параметры поиска</Text>
          <Heading id="search-title" className="section-heading">Расскажите о мероприятии</Heading>
        </Box>
        <Text className="field-hint">* Обязательные поля</Text>
      </Flex>
      <form onSubmit={submit} noValidate>
        <div className="search-grid">
          <label className="field" htmlFor="field-city"><span>Город *</span>
            <select id="field-city" className="control" value={value.city} onChange={(e) => update('city', e.target.value)} aria-invalid={!!errors.city} aria-describedby={errors.city ? 'error-city' : undefined}>
              <option value="">Выберите город</option>
              {options.cities.map((city) => <option key={city} value={city}>{city}</option>)}
            </select>
            {errors.city && <small id="error-city" className="field-error">{errors.city}</small>}
          </label>
          <label className="field" htmlFor="field-date"><span>Дата мероприятия *</span>
            <Input id="field-date" className="control" type="date" min={options.min_date} max={options.max_date} value={value.date} onChange={(e) => update('date', e.target.value)} aria-invalid={!!errors.date} aria-describedby={errors.date ? 'error-date' : undefined} />
            {errors.date && <small id="error-date" className="field-error">{errors.date}</small>}
          </label>
          <label className="field" htmlFor="field-event_type"><span>Тип мероприятия *</span>
            <select id="field-event_type" className="control" value={value.event_type} onChange={(e) => update('event_type', e.target.value)} aria-invalid={!!errors.event_type} aria-describedby={errors.event_type ? 'error-event_type' : undefined}>
              <option value="">Выберите формат</option>
              {options.event_types.map((item) => <option key={item} value={item}>{item[0].toLocaleUpperCase('ru-RU') + item.slice(1)}</option>)}
            </select>
            {errors.event_type && <small id="error-event_type" className="field-error">{errors.event_type}</small>}
          </label>
          <label className="field" htmlFor="field-category"><span>Категория подрядчика *</span>
            <select id="field-category" className="control" value={value.category} onChange={(e) => update('category', e.target.value)} aria-invalid={!!errors.category} aria-describedby={errors.category ? 'error-category' : undefined}>
              <option value="">Выберите категорию</option>
              {options.categories.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
            {errors.category && <small id="error-category" className="field-error">{errors.category}</small>}
          </label>
          <label className="field" htmlFor="field-budget"><span>Бюджет *</span>
            <div className="input-suffix"><Input id="field-budget" className="control" type="text" inputMode="numeric" autoComplete="off" value={value.budget ? formatKZT(value.budget).replace(' ₸', '') : ''} onChange={(e) => update('budget', Number(e.target.value.replace(/\D/g, '')))} placeholder="800 000" aria-invalid={!!errors.budget} aria-describedby={errors.budget ? 'error-budget' : undefined} /><span aria-hidden="true">₸</span></div>
            {errors.budget && <small id="error-budget" className="field-error">{errors.budget}</small>}
          </label>
          <label className="field" htmlFor="field-language"><span>Язык</span>
            <select id="field-language" className="control" value={value.language || ''} onChange={(e) => update('language', e.target.value || undefined)}>
              <option value="">Не важно</option>
              {options.languages.map((item) => <option key={item} value={item}>{item[0].toLocaleUpperCase('ru-RU') + item.slice(1)}</option>)}
            </select>
          </label>
          <label className="field" htmlFor="field-duration"><span>Длительность</span>
            <select id="field-duration" className="control" value={value.duration || ''} onChange={(e) => update('duration', e.target.value ? Number(e.target.value) : undefined)} aria-invalid={!!errors.duration}>
              <option value="">Не важно</option>
              {Array.from({ length: 12 }, (_, index) => index + 1).map((hours) => <option key={hours} value={hours}>{hours} ч</option>)}
            </select>
            {errors.duration && <small className="field-error">{errors.duration}</small>}
          </label>
        </div>
        <Flex className="search-actions" align="center" justify="space-between" gap={4} wrap="wrap">
          <Text>Мы покажем до трёх доступных вариантов и объясним выбор.</Text>
          <Button type="submit" className="primary-button" disabled={pending} aria-busy={pending}>
            {pending ? 'Подбираем…' : 'Найти подрядчиков'}
          </Button>
        </Flex>
      </form>
    </GlassPanel>
  )
}
