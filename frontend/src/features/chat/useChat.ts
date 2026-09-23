import { useCallback, useRef, useState } from 'react'
import type { ChatContext, ChatMessage } from './chat.types'
import { sendChatMessage } from './chat.api'

function createMessage(role: ChatMessage['role'], content: string, status: ChatMessage['status']): ChatMessage {
  return { id: crypto.randomUUID(), role, content, createdAt: Date.now(), status }
}

export function useChat(context: ChatContext) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const messagesRef = useRef<ChatMessage[]>([])
  const [pending, setPending] = useState(false)
  const [lastRequest, setLastRequest] = useState<string>()

  const request = useCallback(async (message: string, assistantMessage: ChatMessage, history: ChatMessage[]) => {
    setPending(true)
    try {
      const { answer } = await sendChatMessage(message, history, context)
      setMessages((current) => {
        const next = current.map((item) => item.id === assistantMessage.id
          ? { ...item, content: answer, status: 'sent' as const }
          : item)
        messagesRef.current = next
        return next
      })
    } catch (error) {
      setMessages((current) => {
        const next = current.map((item) => item.id === assistantMessage.id
          ? { ...item, content: error instanceof Error ? error.message : 'Не удалось получить ответ.', status: 'error' as const, retryable: true }
          : item)
        messagesRef.current = next
        return next
      })
    } finally {
      setPending(false)
    }
  }, [context])

  const send = useCallback((rawMessage: string) => {
    const message = rawMessage.trim()
    if (!message || pending) return
    setLastRequest(message)
    const assistantMessage = createMessage('assistant', '', 'sending')
    const history = messagesRef.current
    const next = [...history, createMessage('user', message, 'sent'), assistantMessage]
    messagesRef.current = next
    setMessages(next)
    void request(message, assistantMessage, history)
  }, [pending, request])

  const retry = useCallback(() => {
    if (!lastRequest || pending) return
    const assistantMessage = createMessage('assistant', '', 'sending')
    const current = messagesRef.current
    const next = [...current.slice(0, -1), assistantMessage]
    messagesRef.current = next
    setMessages(next)
    void request(lastRequest, assistantMessage, current.slice(0, -2))
  }, [lastRequest, pending, request])
  return { messages, pending, send, retry }
}
