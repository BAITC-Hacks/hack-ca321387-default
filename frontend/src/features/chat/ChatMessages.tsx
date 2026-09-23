import { useEffect, useRef } from 'react'
import type { ChatMessage } from './chat.types'
import { useSettings } from '../settings/useSettings'
import { ChatWelcome } from './ChatWelcome'

export function ChatMessages({ messages, onChooseSuggestion, onRetry }: {
  messages: ChatMessage[]
  onChooseSuggestion: (prompt: string) => void
  onRetry: () => void
}) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const { isMotionReduced } = useSettings()
  const endRef = useRef<HTMLDivElement>(null)
  const shouldFollowRef = useRef(true)

  useEffect(() => {
    if (shouldFollowRef.current) endRef.current?.scrollIntoView({ behavior: isMotionReduced ? 'auto' : 'smooth', block: 'end' })
  }, [isMotionReduced, messages])

  return (
    <div className="chat-messages-scroll" ref={scrollRef} onScroll={(event) => {
      const element = event.currentTarget
      shouldFollowRef.current = element.scrollHeight - element.scrollTop - element.clientHeight < 100
    }}>
      <div className="chat-messages" aria-live="polite" aria-relevant="additions text">
        {messages.length === 0 && <ChatWelcome onChoose={onChooseSuggestion} />}
        {messages.map((message) => (
          <article className={`chat-message chat-message-${message.role}`} key={message.id}>
            {message.role === 'assistant' && <div className="chat-message-mark" aria-hidden="true"><span /></div>}
            <div className="chat-message-content">
              {message.status === 'sending' ? (
                <span className="chat-typing" role="status" aria-label="Формирую ответ"><i /><i /><i /></span>
              ) : <p>{message.content}</p>}
              {message.status === 'error' && message.retryable && <button className="chat-retry" type="button" onClick={onRetry}>Повторить</button>}
            </div>
          </article>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  )
}
