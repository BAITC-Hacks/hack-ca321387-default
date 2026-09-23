export type ChatRole = 'user' | 'assistant'

export type ChatMessageStatus = 'sending' | 'sent' | 'error'

export interface ChatMessage {
  id: string
  role: ChatRole
  content: string
  createdAt: number
  status?: ChatMessageStatus
  retryable?: boolean
}

export interface ChatContext {
  city: string
  date: string
  eventType: string
  category: string
}
