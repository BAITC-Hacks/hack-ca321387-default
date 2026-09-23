export type MatchStatus = 'matched' | 'category_not_found' | 'no_match'

export interface SearchParams {
  city: string
  date: string
  event_type: string
  category: string
  budget: number
  language?: string
  duration?: number
}

export interface EvidenceItem {
  matched: boolean | null
  reason: string
  score?: number
  source_field?: string
}

export interface EvidenceLedger {
  date?: EvidenceItem
  city?: EvidenceItem
  category?: EvidenceItem
  budget?: EvidenceItem
  format?: EvidenceItem
  language?: EvidenceItem
  duration?: EvidenceItem
  semantic?: EvidenceItem
}

export interface Contractor {
  id: string
  name: string
  categories: string[]
  city: string
  price: number
  score: number
  semantic_score: number
  synthetic: boolean
  evidence: EvidenceLedger
  explanation: string
  score_breakdown?: Record<string, number>
  max_hours?: number | null
  languages?: string[]
  description?: string
}

export interface DiagnosticStep {
  stage: string
  label: string
  count: number
}

export interface Diagnostics {
  counts?: Record<string, number>
  steps?: DiagnosticStep[]
  primary_blocker?: string
  summary?: string
}

export interface AvailabilityDay {
  date: string
  available: number
}

export interface MatchResponse {
  status: MatchStatus
  results: Contractor[]
  diagnostics?: Diagnostics
  availability?: AvailabilityDay[]
  total_eligible?: number
  model_info?: Record<string, string | boolean>
}

export interface Metadata {
  cities: string[]
  categories: string[]
  event_types: string[]
  languages: string[]
  min_date: string
  max_date: string
}
