import { Box, Container } from '@chakra-ui/react'
import type { ReactNode } from 'react'
import { AppHeader } from './AppHeader'
import { AppFooter } from './AppFooter'

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <Box className="app-shell" minH="100dvh" display="flex" flexDirection="column" bg="bg.canvas" color="text.primary">
      <AppHeader />
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