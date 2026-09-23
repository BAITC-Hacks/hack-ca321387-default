import { Box, Heading, Text } from '@chakra-ui/react'
import { useEffect, useRef, useState } from 'react'
import { AppShell } from '../shared/layout/AppShell'
import { SearchForm } from '../features/search/SearchForm'
import { useMetadata } from '../features/search/useMetadata'
import { ResultsSection } from '../features/matching/ResultsSection'
import { useMatch } from '../features/matching/useMatch'
import { DEFAULT_SEARCH } from '../features/search/search.constants'
import { useSettings } from '../features/settings/useSettings'
import { ApiError } from '../shared/api/client'
import type { SearchParams } from '../shared/types/match'

export function MatchPage() {
  const [draft, setDraft] = useState<SearchParams>({ ...DEFAULT_SEARCH })
  const [submitted, setSubmitted] = useState<SearchParams>()
  const resultsRef = useRef<HTMLDivElement>(null)
  const match = useMatch()
  const metadata = useMetadata()
  const { isMotionReduced } = useSettings()

  const submit = (value: SearchParams) => {
    setSubmitted(value)
    match.mutate(value)
  }
  useEffect(() => {
    if (match.isSuccess || match.isError) {
      resultsRef.current?.scrollIntoView({ behavior: isMotionReduced ? 'auto' : 'smooth', block: 'start' })
    }
  }, [isMotionReduced, match.isSuccess, match.isError, match.data, match.error])
  const focusField = (field: 'city' | 'category') => {
    const element = document.getElementById(`field-${field}`)
    element?.scrollIntoView({ behavior: isMotionReduced ? 'auto' : 'smooth', block: 'center' })
    element?.focus({ preventScroll: true })
  }
  const selectDate = (date: string) => {
    const next = { ...(submitted ?? draft), date }
    setDraft(next)
    submit(next)
  }

  return <AppShell>
    <main>
      <Box className="hero" as="section">
        <Text className="eyebrow"><span className="eyebrow-line" /> Умный подбор подрядчиков</Text>
        <Heading as="h1">Найдём подрядчика,<br /><span>которого можно объяснить.</span></Heading>
        <Text className="hero-description">EventLens проверяет дату, бюджет и параметры мероприятия, ранжирует доступных подрядчиков и показывает факты, которые повлияли на результат.</Text>
        <Text className="hero-note">До 3 рекомендаций <span>·</span> Повторяемый результат <span>·</span> Прозрачные причины</Text>
      </Box>
      {metadata.isError && <div className="state-panel error-panel" role="alert">
        <p>{metadata.error.message}</p><button className="secondary-button" type="button" onClick={() => void metadata.refetch()}>Повторить загрузку справочников</button>
      </div>}
      {metadata.isPending && <p role="status">Загружаем справочники…</p>}
      <SearchForm value={draft} onChange={setDraft} onSubmit={submit} metadata={metadata.data} pending={match.isPending} serverErrors={match.error instanceof ApiError && submitted === draft ? match.error.fields : []} />
      <div ref={resultsRef} className="results-anchor">
        <ResultsSection response={match.data} query={submitted} pending={match.isPending} error={match.isError ? match.error.message : null} onRetry={() => submitted && submit(submitted)} onFocusField={focusField} onDateSelect={selectDate} />
      </div>
    </main>
  </AppShell>
}
