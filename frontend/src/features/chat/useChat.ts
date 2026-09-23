import { useCallback, useState } from 'react'
import type { ChatMessage } from './chat.types'
import { sendChatMessageMock } from './chat.mock'

function createMessage(role: ChatMessage['role'], content: string, status: ChatMessage['status']): ChatMessage {
  return { id: crypto.randomUUID(), role, content, createdAt: Date.now(), status }
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [pending, setPending] = useState(false)
  const [lastRequest, setLastRequest] = useState<string>()

  const request = useCallback(async (message: string, assistantMessage: ChatMessage) => {
    setPending(true)
    try {
      const content = await sendChatMessageMock(message)
      setMessages((current) => current.map((item) => item.id === assistantMessage.id
        ? { ...item, content, status: 'sent' }
        : item))
    } catch {
      setMessages((current) => current.map((item) => item.id === assistantMessage.id
        ? { ...item, content: 'Не удалось получить ответ.', status: 'error', retryable: true }
        : item))
    } finally {
      setPending(false)
    }
  }, [])

  const send = useCallback((rawMessage: string) => {
    const message = rawMessage.trim()
    if (!message || pending) return
    setLastRequest(message)
    const assistantMessage = createMessage('assistant', '', 'sending')
    setMessages((current) => [...current, createMessage('user', message, 'sent'), assistantMessage])
    void request(message, assistantMessage)
  }, [pending, request])

  const retry = useCallback(() => {
    if (!lastRequest || pending) return
    const assistantMessage = createMessage('assistant', '', 'sending')
    setMessages((current) => [...current.slice(0, -1), assistantMessage])
    void request(lastRequest, assistantMessage)
  }, [lastRequest, pending, request])
  return { messages, pending, send, retry }
}
