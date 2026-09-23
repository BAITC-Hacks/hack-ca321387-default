const suggestions = [
  { title: 'Найти подрядчика', detail: 'Подбор по параметрам мероприятия', prompt: 'Помоги подобрать подрядчика для моего мероприятия' },
  { title: 'Объяснить результат', detail: 'Почему эти варианты выше остальных', prompt: 'Объясни результаты подбора' },
  { title: 'Проверить другую дату', detail: 'Посмотреть альтернативную доступность', prompt: 'Есть варианты на другую дату?' },
]

export function ChatWelcome({ onChoose }: { onChoose: (prompt: string) => void }) {
  return (
    <section className="chat-welcome" aria-labelledby="chat-welcome-title">
      <div className="chat-welcome-mark" aria-hidden="true"><span /></div>
      <p className="chat-welcome-kicker">EVENTLENS ASSISTANT</p>
      <h3 id="chat-welcome-title">Чем помочь с мероприятием?</h3>
      <p className="chat-welcome-copy">Опишите задачу или спросите о результатах подбора.</p>
      <div className="chat-suggestions">
        {suggestions.map((suggestion) => (
          <button className="chat-suggestion" type="button" key={suggestion.title} onClick={() => onChoose(suggestion.prompt)}>
            <span>{suggestion.title}</span>
            <small>{suggestion.detail}</small>
            <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M5 10h10m-4-4 4 4-4 4" /></svg>
          </button>
        ))}
      </div>
    </section>
  )
}
