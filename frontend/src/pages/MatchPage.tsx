import { Box, Heading, Text } from '@chakra-ui/react'
import { useEffect, useRef, useState } from 'react'
import { AppShell } from '../components/layout/AppShell'
import { SearchPanel } from '../components/search/SearchPanel'
import { ResultsSection } from '../components/results/ResultsSection'
import { DEFAULT_SEARCH } from '../constants/app'
import { useMatch } from '../hooks/useMatch'
import { useMetadata } from '../hooks/useMetadata'
import type { SearchParams } from '../types/match'

export function MatchPage() {
  const [draft, setDraft] = useState<SearchParams>({ ...DEFAULT_SEARCH })
  const [submitted, setSubmitted] = useState<SearchParams>()
  const resultsRef = useRef<HTMLDivElement>(null)
  const match = useMatch()
  const metadata = useMetadata()

  const submit = (value: SearchParams) => {
    setSubmitted(value)
    match.mutate(value)
  }
  useEffect(() => {
    if (match.isSuccess || match.isError) {
      const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      resultsRef.current?.scrollIntoView({ behavior: reduced ? 'instant' : 'smooth', block: 'start' })
    }
  }, [match.isSuccess, match.isError, match.data, match.error])
  const focusField = (field: 'city' | 'category') => {
    const element = document.getElementById(`field-${field}`)
    element?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    element?.focus({ preventScroll: true })
  }
  const selectDate = (date: string) => {
    const next = { ...draft, date }
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
      <SearchPanel value={draft} onChange={setDraft} onSubmit={submit} metadata={metadata.data} pending={match.isPending} />
      <div ref={resultsRef} className="results-anchor">
        <ResultsSection response={match.data} query={submitted} pending={match.isPending} error={match.isError ? match.error.message : null} onRetry={() => submitted && submit(submitted)} onFocusField={focusField} onDateSelect={selectDate} />
      </div>
    </main>
  </AppShell>
}
