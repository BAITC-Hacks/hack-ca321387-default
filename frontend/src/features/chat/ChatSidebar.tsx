import { Drawer, Portal } from '@chakra-ui/react'
import { useCallback, useState } from 'react'
import { formatDate } from '../../shared/format'
import { ChatComposer } from './ChatComposer'
import { ChatMessages } from './ChatMessages'
import { useChat } from './useChat'
import type { ChatContext } from './chat.types'

export function ChatSidebar({ open, onOpenChange, context }: {
  open: boolean
  onOpenChange: (open: boolean) => void
  context: ChatContext
}) {
  const { messages, pending, send, retry } = useChat(context)
  const [draft, setDraft] = useState("")
  const chooseSuggestion = useCallback((prompt: string) => setDraft(prompt), [])
  const searchSummary = [context.city, context.eventType, context.category, formatDate(context.date, true)].filter(Boolean).join(' · ')

  return (
    <Drawer.Root open={open} onOpenChange={(details) => onOpenChange(details.open)} placement="end" size="md">
      <Portal>
        <Drawer.Backdrop className="chat-backdrop" />
        <Drawer.Positioner className="chat-positioner">
          <Drawer.Content className="chat-drawer liquid-glass liquid-glass-elevated" aria-describedby="chat-description">
            <Drawer.Header className="chat-header">
              <div className="chat-header-identity">
                <div className="chat-brand-mark" aria-hidden="true"><span /></div>
                <div>
                  <Drawer.Title className="chat-title">EventLens Assistant</Drawer.Title>
                  <Drawer.Description id="chat-description" className="chat-subtitle">Помощник по подбору подрядчиков</Drawer.Description>
                </div>
              </div>
              <Drawer.CloseTrigger asChild>
                <button className="chat-close" type="button" aria-label="Закрыть ассистента"><span aria-hidden="true">×</span></button>
              </Drawer.CloseTrigger>
            </Drawer.Header>
            <div className="chat-context" aria-label="Текущий поиск">
              <span className="chat-context-label">Текущий поиск</span>
              <span className="chat-context-value">{searchSummary || context.category}</span>
            </div>
            <ChatMessages messages={messages} onChooseSuggestion={chooseSuggestion} onRetry={retry} />
            <ChatComposer value={draft} pending={pending} onChange={setDraft} onSend={(message) => { setDraft(""); send(message) }} />
          </Drawer.Content>
        </Drawer.Positioner>
      </Portal>
    </Drawer.Root>
  )
}
