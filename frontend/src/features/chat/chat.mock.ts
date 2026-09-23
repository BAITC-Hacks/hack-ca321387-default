const delay = (duration: number) => new Promise<void>((resolve) => window.setTimeout(resolve, duration))

/** Replace this adapter with the chat API call when the backend endpoint is ready. */
export async function sendChatMessageMock(message: string): Promise<string> {
  void message
  if (import.meta.env.DEV && import.meta.env.VITE_CHAT_MOCK_ERROR === 'true') {
    await delay(550)
    throw new Error('Mock chat request failed')
  }

  await delay(550)
  return 'Я помогу разобраться с подбором. Сейчас ответы в чате работают в демонстрационном режиме.'
}
