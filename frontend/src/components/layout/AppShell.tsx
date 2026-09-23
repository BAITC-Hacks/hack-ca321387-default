import { Box, Container } from '@chakra-ui/react'
import type { ReactNode } from 'react'
import { AppHeader } from './AppHeader'

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <Box className="app-shell" minH="100vh" bg="bg.canvas" color="text.primary">
      <AppHeader />
      <Container maxW="1280px" px={{ base: 5, md: 8 }}>
        {children}
        <footer className="site-footer"><span>EventLens</span><span>HackAlem AI · 2026</span></footer>
      </Container>
    </Box>
  )
}
