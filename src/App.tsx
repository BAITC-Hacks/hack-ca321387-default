import {
  Badge,
  Box,
  Button,
  Container,
  Heading,
  HStack,
  SimpleGrid,
  Stack,
  Text,
} from '@chakra-ui/react'
import { useQuery } from '@tanstack/react-query'
import './App.css'

type HealthResponse = {
  status: string
  service: string
}

const apiUrl = import.meta.env.VITE_API_URL ?? '/api'

async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${apiUrl}/health`)

  if (!response.ok) {
    throw new Error('Backend health check failed')
  }

  return response.json()
}

function App() {
  const healthQuery = useQuery({
    queryKey: ['backend-health'],
    queryFn: fetchHealth,
    retry: 1,
  })

  return (
    <Box minH="100vh" bg="gray.950" color="white">
      <Container maxW="1100px" py={{ base: 8, md: 12 }}>
        <Stack gap={8}>
          <HStack align="center" justify="space-between">
            <Stack gap={1}>
              <Badge colorPalette="green" w="fit-content">
                Full stack ready
              </Badge>
              <Heading size={{ base: '2xl', md: '4xl' }}>HackAlemAI architecture</Heading>
            </Stack>
            <Button colorPalette="blue" onClick={() => healthQuery.refetch()}>
              Check API
            </Button>
          </HStack>

          <SimpleGrid columns={{ base: 1, md: 3 }} gap={4}>
            <Box className="app-card">
              <Text className="card-label">Frontend</Text>
              <Heading size="md">React + Vite</Heading>
              <Text color="gray.300">Fast interface with Chakra UI components.</Text>
            </Box>
            <Box className="app-card">
              <Text className="card-label">Data</Text>
              <Heading size="md">TanStack Query</Heading>
              <Text color="gray.300">API state, caching, and loading statuses.</Text>
            </Box>
            <Box className="app-card">
              <Text className="card-label">Backend</Text>
              <Heading size="md">FastAPI</Heading>
              <Text color="gray.300">Dockerized backend service in the backend folder.</Text>
            </Box>
          </SimpleGrid>

          <Box className="status-panel">
            <Text className="card-label">API status</Text>
            <Heading size="lg">
              {healthQuery.isLoading && 'Checking backend...'}
              {healthQuery.isError && 'Backend is not reachable'}
              {healthQuery.isSuccess && `${healthQuery.data.service}: ${healthQuery.data.status}`}
            </Heading>
            <Text color="gray.300">
              Docker Compose starts frontend on port 3000 and backend on port 8000.
            </Text>
          </Box>
        </Stack>
      </Container>
    </Box>
  )
}

export default App
