import { Box, Flex, Text } from '@chakra-ui/react'
import { useRef } from 'react'

export function AppHeader() {
  const dialog = useRef<HTMLDialogElement>(null)
  return (
    <>
      <header className="site-header">
        <Flex maxW="1280px" mx="auto" px={{ base: 5, md: 8 }} align="center" justify="space-between" minH="72px">
          <Flex align="center" gap="11px">
            <Box className="brand-mark" aria-hidden="true"><span /></Box>
            <Text className="brand-name">EventLens</Text>
            <span className="brand-divider" aria-hidden="true" />
            <Text className="brand-caption">Подбор с объяснением</Text>
          </Flex>
          <button className="text-button" type="button" onClick={() => dialog.current?.showModal()}>
            Как это работает
          </button>
        </Flex>
      </header>
      <dialog ref={dialog} className="info-dialog" aria-labelledby="how-title" onClick={(event) => {
        if (event.target === dialog.current) dialog.current?.close()
      }}>
        <div className="dialog-head">
          <h2 id="how-title">Как работает EventLens</h2>
          <button type="button" className="dialog-close" aria-label="Закрыть окно" onClick={() => dialog.current?.close()}>×</button>
        </div>
        <ol className="how-list">
          <li><span>01</span><div><strong>Проверяем ограничения</strong><p>Город, дата, формат, бюджет, язык и длительность определяют доступных подрядчиков.</p></div></li>
          <li><span>02</span><div><strong>Сопоставляем профили</strong><p>Оставшихся кандидатов ранжируем по совпадению описания и параметрам заказа.</p></div></li>
          <li><span>03</span><div><strong>Показываем причины</strong><p>Каждая рекомендация сопровождается фактами из профиля и объяснением результата.</p></div></li>
        </ol>
      </dialog>
    </>
  )
}
