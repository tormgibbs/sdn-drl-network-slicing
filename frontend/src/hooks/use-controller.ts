import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { fetchState } from '@/services/api'
import { MOCK_STATE, startMockWebSocket, USE_MOCK } from '@/services/mock-data'
import type { StateResponse, WsMessage } from '@/types/api'

export const STATE_KEY = ['state'] as const

export function useController() {
  const queryClient = useQueryClient()

  const query = useQuery({
    queryKey: STATE_KEY,
    queryFn: USE_MOCK ? () => Promise.resolve(MOCK_STATE) : fetchState,
    staleTime: Infinity,
    retry: 3,
  })

  useEffect(() => {
    if (!query.isSuccess) return

    if (USE_MOCK) {
      return startMockWebSocket((msg: WsMessage) => {
        queryClient.setQueryData<StateResponse>(STATE_KEY, (old) => {
          if (!old) return old
          return {
            ...old,
            metrics: msg.metrics,
            allocations: msg.allocations,
            traffic: msg.traffic,
          }
        })
      })
    }

    const ws = new WebSocket('ws://localhost:8080/ws')

    ws.onmessage = (event) => {
      try {
        const msg: WsMessage = JSON.parse(event.data)
        queryClient.setQueryData<StateResponse>(STATE_KEY, (old) => {
          if (!old) return old
          return {
            ...old,
            metrics: msg.metrics,
            allocations: msg.allocations,
            traffic: msg.traffic,
          }
        })
      } catch {
        console.error('Invalid WS message', event.data)
      }
    }

    ws.onerror = (e) => console.error('WS error', e)

    return () => ws.close()

  }, [query.isSuccess, queryClient])

  return {
    isLoading: query.isLoading,
    isError: query.isError,
  }
}