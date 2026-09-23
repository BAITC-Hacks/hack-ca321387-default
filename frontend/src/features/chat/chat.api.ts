import { apiClient } from '../../shared/api/client'
import type { ChatContext, ChatMessage } from './chat.types'

interface ChatResponse {
  answer: string
  provider: 'openai' | 'local'
}

export async function sendChatMessage(message: string, history: ChatMessage[], context: ChatContext): Promise<ChatResponse> {
  return apiClient<ChatResponse>('/chat', {
    method: 'POST',
    body: JSON.stringify({
      message,
      history: history.filter((item) => item.status === 'sent').slice(-12)
        .map(({ role, content }) => ({ role, content })),
      context,
    }),
    signal: AbortSignal.timeout(80_000),
  })
}
