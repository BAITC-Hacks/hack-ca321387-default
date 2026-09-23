import { createSystem, defaultConfig, defineConfig } from '@chakra-ui/react'

const config = defineConfig({
  theme: {
    semanticTokens: {
      colors: {
        bg: {
          canvas: { value: '#0b0d11' },
          surface: { value: '#14171d' },
          glass: { value: 'rgba(26, 30, 38, 0.88)' },
        },
        text: {
          primary: { value: '#f1f3f6' },
          secondary: { value: '#a5aab4' },
          muted: { value: '#747b87' },
        },
        border: { subtle: { value: 'rgba(255,255,255,0.1)' } },
        accent: { primary: { value: '#8abaff' }, strong: { value: '#bed9ff' } },
        status: {
          success: { value: '#8ed6b6' },
          warning: { value: '#e4be82' },
          error: { value: '#ec9c9f' },
        },
      },
    },
  },
})

export const system = createSystem(defaultConfig, config)
