import { Box, type BoxProps } from '@chakra-ui/react'

export function GlassPanel({ className, ...props }: BoxProps) {
  return <Box className={`glass-panel ${className || ''}`} {...props} />
}
