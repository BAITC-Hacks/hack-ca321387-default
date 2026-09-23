import { Box, Container } from '@chakra-ui/react'
import type { ReactNode } from 'react'
import { AppHeader } from './AppHeader'
import { AppFooter } from './AppFooter'
import type { ChatContext } from '../../features/chat/chat.types'

export function AppShell({ children, chatContext }: { children: ReactNode; chatContext: ChatContext }) {
  return (
    <Box className="app-shell" minH="100dvh" display="flex" flexDirection="column" bg="bg.canvas" color="text.primary">
      <AppHeader chatContext={chatContext} />
      <Box as="main" flex="1" width="100%">
        <Container maxW="1280px" px={{ base: 5, md: 8 }}>
          {children}
        </Container>
      </Box>
      <Container maxW="1280px" width="100%" px={{ base: 5, md: 8 }}>
        <AppFooter />
      </Container>
    </Box>
  )
}