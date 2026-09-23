import { Box, Flex, Text } from '@chakra-ui/react'
import { useRef, useState } from 'react'
import { SettingsDrawer } from '../../features/settings/SettingsDrawer'
import { ThemeToggle } from '../../features/settings/ThemeToggle'
import { ChatSidebar } from '../../features/chat/ChatSidebar'
import type { ChatContext } from '../../features/chat/chat.types'

export function AppHeader({ chatContext }: { chatContext: ChatContext }) {
  const infoDialog = useRef<HTMLDialogElement>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)

  return (
    <>
      <header className="site-header liquid-glass">
        <Flex className="site-header-inner" px={{ base: 4, md: 6 }} align="center" justify="space-between" minH={{ base: '62px', md: '68px' }} gap={4}>
          <Flex align="center" gap="11px" minW={0}>
            <Box className="brand-mark" aria-hidden="true"><span /></Box>
            <Text className="brand-name">EventLens</Text>
            <span className="brand-divider" aria-hidden="true" />
            <Text className="brand-caption">Подбор с объяснением</Text>
          </Flex>
          <Flex align="center" gap={{ base: 1, sm: 2 }} flexShrink={0}>
            <button className="text-button how-button" type="button" onClick={() => infoDialog.current?.showModal()}>
              Как это работает
            </button>
            <ThemeToggle />
            <button className="assistant-button" type="button" aria-haspopup="dialog" aria-expanded={chatOpen} onClick={() => setChatOpen(true)}>
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11.4a7.6 7.6 0 0 1-8 7.6 8.5 8.5 0 0 1-3.4-.7L4 20l1.3-3.7A7.2 7.2 0 0 1 4 12.5C4 8.4 7.6 5 12 5s8 2.9 8 6.4Z" /><path d="M8.5 12h.01m3.49 0h.01m3.49 0h.01" /></svg>
              <span>Ассистент</span>
            </button>
            <button
              className="icon-button"
              type="button"
              aria-label="Открыть настройки"
              title="Настройки"
              aria-haspopup="dialog"
              onClick={() => setSettingsOpen(true)}
            >
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 8.7a3.3 3.3 0 1 0 0 6.6 3.3 3.3 0 0 0 0-6.6Z" /><path d="m19.4 13.5 1.1.8-1.1 1.9-1.3-.5a7.6 7.6 0 0 1-1.5.9l-.2 1.4h-2.2l-.3-1.4a7.6 7.6 0 0 1-1.7 0l-.7 1.2-1.9-1.1.5-1.3a7.6 7.6 0 0 1-.9-1.5l-1.4-.2v-2.2l1.4-.3a7.6 7.6 0 0 1 0-1.7L8 8.8l1.1-1.9 1.3.5a7.6 7.6 0 0 1 1.5-.9l.2-1.4h2.2l.3 1.4a7.6 7.6 0 0 1 1.7 0l.7-1.2 1.9 1.1-.5 1.3a7.6 7.6 0 0 1 .9 1.5l1.4.2v2.2l-1.4.3a7.6 7.6 0 0 1 0 1.6Z" /></svg>
            </button>
          </Flex>
        </Flex>
      </header>

      <dialog ref={infoDialog} className="info-dialog liquid-glass liquid-glass-elevated" aria-labelledby="how-title" onClick={(event) => {
        if (event.target === infoDialog.current) infoDialog.current?.close()
      }}>
        <div className="dialog-head">
          <h2 id="how-title">Как работает EventLens</h2>
          <button type="button" className="dialog-close" aria-label="Закрыть окно" onClick={() => infoDialog.current?.close()}><span aria-hidden="true">×</span></button>
        </div>
        <ol className="how-list">
          <li><span>01</span><div><strong>Проверяем ограничения</strong><p>Город, дата, формат, бюджет, язык и длительность определяют доступных подрядчиков.</p></div></li>
          <li><span>02</span><div><strong>Сопоставляем профили</strong><p>Оставшихся кандидатов ранжируем по совпадению описания и параметров заказа.</p></div></li>
          <li><span>03</span><div><strong>Показываем причины</strong><p>Каждую рекомендацию сопровождают факты из профиля и объяснение результата.</p></div></li>
        </ol>
      </dialog>
      <SettingsDrawer open={settingsOpen} onOpenChange={setSettingsOpen} />
      <ChatSidebar open={chatOpen} onOpenChange={setChatOpen} context={chatContext} />
    </>
  )
}
