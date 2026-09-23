import { Box, Flex, Text } from '@chakra-ui/react'
import { useRef, useState } from 'react'
import { SettingsDrawer } from '../../features/settings/SettingsDrawer'
import { ThemeToggle } from '../../features/settings/ThemeToggle'

export function AppHeader() {
  const infoDialog = useRef<HTMLDialogElement>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)

  return (
    <>
      <header className="site-header">
        <Flex maxW="1280px" mx="auto" px={{ base: 5, md: 8 }} align="center" justify="space-between" minH="72px" gap={4}>
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

      <dialog ref={infoDialog} className="info-dialog" aria-labelledby="how-title" onClick={(event) => {
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
    </>
  )
}
