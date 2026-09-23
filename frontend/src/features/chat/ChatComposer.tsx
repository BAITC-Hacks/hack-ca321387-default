import { useEffect, useRef, type FormEvent, type KeyboardEvent } from 'react'

export function ChatComposer({ value, pending, onChange, onSend }: {
  value: string
  pending: boolean
  onChange: (value: string) => void
  onSend: (message: string) => void
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const canSend = value.trim().length > 0 && !pending

  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, 144)}px`
    textarea.style.overflowY = textarea.scrollHeight > 144 ? 'auto' : 'hidden'
  }, [value])

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (canSend) onSend(value)
  }

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing && !window.matchMedia('(max-width: 600px)').matches) {
      event.preventDefault()
      if (canSend) event.currentTarget.form?.requestSubmit()
    }
  }

  return (
    <form className="chat-composer" onSubmit={submit}>
      <label className="sr-only" htmlFor="chat-composer-input">Сообщение ассистенту</label>
      <textarea
        ref={textareaRef}
        id="chat-composer-input"
        rows={1}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Спросите о подборе подрядчиков…"
      />
      <button className="chat-send" type="submit" disabled={!canSend} aria-label="Отправить сообщение" title="Отправить">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 19V5m-6 6 6-6 6 6" /></svg>
      </button>
      <p className="chat-composer-hint">Enter — отправить <span>·</span> Shift + Enter — новая строка</p>
    </form>
  )
}