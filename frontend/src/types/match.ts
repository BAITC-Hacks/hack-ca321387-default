// Generated from backend/app/schemas.py. Run python -m backend.scripts.export_contract.
export type SearchParams = {
  city: string
  date: string
  event_type: string
  category: string
  budget: number
  language?: string | null
  duration?: number | null
}

export type AvailabilityDay = {
  date: string
  available: number
}

export type BudgetAlternative = {
  budget: number
  available: number
}

export type Contractor = {
  id: string
  name: string
  categories: Array<string>
  city: string
  price: number
  price_basis: "event_from"
  score: number
  semantic_score: number | null
  synthetic: boolean
  city_imputed: boolean
  price_imputed: boolean
  evidence: EvidenceLedger
  explanation: string
  score_breakdown: ScoreBreakdown
  score_weights: ScoreBreakdown
  max_hours: number | null
  duration_policy: "limited" | "not_applicable" | "unknown"
  languages: Array<string>
  description: string
}

export type DiagnosticStep = {
  stage: "category" | "city" | "date" | "format" | "budget" | "language" | "duration"
  label: string
  before: number
  after: number
  excluded: number
  count: number
}

export type Diagnostics = {
  counts: Record<string, number>
  steps: Array<DiagnosticStep>
  primary_blocker: "category" | "city" | "date" | "format" | "budget" | "language" | "duration" | null
  summary: string
  budget_alternative: BudgetAlternative | null
}

export type EvidenceItem = {
  matched: boolean | null
  reason: string
  score: number | null
  source_field: string
  code: string
  requested: string | number | null
  actual: string | number | Array<string> | null
}

export type EvidenceLedger = {
  category: EvidenceItem
  city: EvidenceItem
  date: EvidenceItem
  format: EvidenceItem
  budget: EvidenceItem
  language: EvidenceItem
  duration: EvidenceItem
  semantic: EvidenceItem
}

export type ModelInfo = {
  ranking_version: string
  data_version: string
  semantic_model: "tfidf-v1" | "unavailable" | "disabled" | "not_used"
  fallback_used: boolean
}

export type ScoreBreakdown = {
  semantic: number | null
  lexical: number | null
  budget: number
  duration: number | null
}

export type MatchResponse = {
  status: "matched" | "category_not_found" | "no_match"
  results: Array<Contractor>
  diagnostics: Diagnostics
  availability: Array<AvailabilityDay>
  total_eligible: number
  model_info: ModelInfo
}

export type Metadata = {
  cities: Array<string>
  categories: Array<string>
  event_types: Array<string>
  languages: Array<string>
  min_date: string
  max_date: string
  min_budget_exclusive: number
  max_budget: number
  min_duration: number
  max_duration: number
}

export type FieldError = {
  field: string | null
  code: string
  message: string
}

export type ErrorResponse = {
  code: string
  message: string
  detail: Array<FieldError>
}

export type MatchStatus = MatchResponse['status']
