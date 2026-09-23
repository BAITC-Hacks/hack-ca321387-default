import { Box, Button, Flex, Heading, Text } from '@chakra-ui/react'
import { useState, type FormEvent } from 'react'
import type { Metadata, SearchParams } from '../../shared/types/match'
import { FALLBACK_METADATA } from './search.constants'
import { GlassPanel } from '../../shared/ui/GlassPanel'
import { SearchFields, type SearchErrors } from './SearchFields'

interface SearchFormProps {
  value: SearchParams
  onChange: (value: SearchParams) => void
  onSubmit: (value: SearchParams) => void
  metadata?: Metadata
  pending: boolean
  serverErrors?: Array<{ field: string | null; message: string }>
}

export function SearchForm({ value, onChange, onSubmit, metadata, pending, serverErrors = [] }: SearchFormProps) {
  const [errors, setErrors] = useState<SearchErrors>({})
  const options = metadata || FALLBACK_METADATA

  const update = <K extends keyof SearchParams>(key: K, next: SearchParams[K]) => {
    onChange({ ...value, [key]: next })
    setErrors((current) => ({ ...current, [key]: undefined }))
  }

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const next: SearchErrors = {}
    if (!value.city) next.city = 'Выберите город.'
    if (!value.date || value.date < options.min_date || value.date > options.max_date) next.date = 'Выберите дату в диапазоне каталога.'
    if (!value.event_type) next.event_type = 'Выберите тип мероприятия.'
    if (!value.category) next.category = 'Выберите категорию.'
    if (!Number.isFinite(value.budget) || value.budget <= 0 || value.budget > 100_000_000) next.budget = 'Укажите бюджет от 1 до 100 000 000 ₸.'
    if (value.duration != null && (value.duration <= 0 || value.duration > 12)) next.duration = 'Выберите длительность до 12 часов.'
    setErrors(next)

    const firstInvalid = Object.keys(next)[0]
    if (firstInvalid) {
      document.getElementById(`field-${firstInvalid}`)?.focus()
      return
    }
    onSubmit(value)
  }

  return (
    <GlassPanel as="section" className="search-panel" aria-labelledby="search-title">
      <Flex justify="space-between" align="start" gap={4} mb={7} wrap="wrap">
        <Box>
          <Text className="eyebrow">01 / Параметры поиска</Text>
          <Heading id="search-title" className="section-heading">Расскажите о мероприятии</Heading>
        </Box>
        <Text className="field-hint">* Обязательные поля</Text>
      </Flex>
      <form onSubmit={submit} noValidate>
        <SearchFields value={value} options={options} errors={{ ...Object.fromEntries(serverErrors.filter((item) => item.field).map((item) => [item.field, item.message])), ...errors }} update={update} />
        <Flex className="search-actions" align="center" justify="space-between" gap={4} wrap="wrap">
          <Text>Покажем до трёх доступных вариантов и объясним выбор.</Text>
          <Button type="submit" className="primary-button" disabled={pending} aria-busy={pending}>
            {pending ? 'Подбираем…' : 'Найти подрядчиков'}
          </Button>
        </Flex>
      </form>
    </GlassPanel>
  )
}
