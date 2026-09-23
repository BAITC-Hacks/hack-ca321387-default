import { ChakraProvider } from '@chakra-ui/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, type ReactNode } from 'react'
import { SettingsProvider } from '../features/settings/SettingsProvider'
import { system } from './theme'

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: { queries: { gcTime: typeof document === 'undefined' ? Infinity : 5 * 60_000 } },
  }))

  return (
    <ChakraProvider value={system}>
      <QueryClientProvider client={queryClient}>
        <SettingsProvider>{children}</SettingsProvider>
      </QueryClientProvider>
    </ChakraProvider>
  )
}
