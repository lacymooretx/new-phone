import { useEffect, useRef, useCallback } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { useAuthStore } from "@/stores/auth-store"
import { queryKeys } from "@/api/query-keys"
import { getWsBaseUrl } from "@/lib/desktop-bridge"

type ConnectionStatus = "connecting" | "connected" | "disconnected"

const MAX_BACKOFF = 30_000
const INITIAL_BACKOFF = 1_000

interface EventEnvelope {
  event: string
  tenant_id: string
  payload: Record<string, unknown>
  timestamp: string
}

export function useEventStream(): ConnectionStatus {
  const queryClient = useQueryClient()
  const accessToken = useAuthStore((s) => s.accessToken)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const activeTenantId = useAuthStore((s) => s.activeTenantId)

  const wsRef = useRef<WebSocket | null>(null)
  const backoffRef = useRef(INITIAL_BACKOFF)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const statusRef = useRef<ConnectionStatus>("disconnected")
  const intentionalCloseRef = useRef(false)

  const cleanup = useCallback(() => {
    intentionalCloseRef.current = true
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    statusRef.current = "disconnected"
  }, [])

  const handleEvent = useCallback(
    (envelope: EventEnvelope) => {
      const tenantId = activeTenantId
      if (!tenantId) return

      const conversationId = envelope.payload.conversation_id as string | undefined

      switch (envelope.event) {
        case "sms.received":
          queryClient.invalidateQueries({ queryKey: queryKeys.sms.conversations(tenantId) })
          if (conversationId) {
            queryClient.invalidateQueries({
              queryKey: queryKeys.sms.messages(tenantId, conversationId),
            })
            queryClient.invalidateQueries({
              queryKey: queryKeys.sms.conversationDetail(tenantId, conversationId),
            })
          }
          break

        case "sms.sent":
          if (conversationId) {
            queryClient.invalidateQueries({
              queryKey: queryKeys.sms.messages(tenantId, conversationId),
            })
          }
          break

        case "sms.status_updated":
          if (conversationId) {
            queryClient.invalidateQueries({
              queryKey: queryKeys.sms.messages(tenantId, conversationId),
            })
          }
          break

        case "conversation.created":
          queryClient.invalidateQueries({ queryKey: queryKeys.sms.conversations(tenantId) })
          break

        case "conversation.updated":
          queryClient.invalidateQueries({ queryKey: queryKeys.sms.conversations(tenantId) })
          if (conversationId) {
            queryClient.invalidateQueries({
              queryKey: queryKeys.sms.conversationDetail(tenantId, conversationId),
            })
          }
          break

        case "conversation.assigned":
          queryClient.invalidateQueries({ queryKey: queryKeys.sms.conversations(tenantId) })
          if (conversationId) {
            queryClient.invalidateQueries({
              queryKey: queryKeys.sms.conversationDetail(tenantId, conversationId),
            })
          }
          break

        case "parking.slot_occupied":
        case "parking.slot_cleared":
          queryClient.invalidateQueries({ queryKey: queryKeys.parkingLots.slots(tenantId) })
          queryClient.invalidateQueries({ queryKey: queryKeys.parkingLots.all(tenantId) })
          break
      }
    },
    [queryClient, activeTenantId],
  )

  useEffect(() => {
    if (!isAuthenticated || !accessToken) {
      cleanup()
      return
    }

    async function connect() {
      intentionalCloseRef.current = false
      statusRef.current = "connecting"

      const wsBase = await getWsBaseUrl()
      const url = `${wsBase}/api/v1/ws/events?token=${encodeURIComponent(accessToken!)}`
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        statusRef.current = "connected"
        backoffRef.current = INITIAL_BACKOFF
      }

      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data) as EventEnvelope
          if (data.event === "ping") return
          handleEvent(data)
        } catch {
          // ignore malformed messages
        }
      }

      ws.onclose = () => {
        wsRef.current = null
        statusRef.current = "disconnected"

        if (intentionalCloseRef.current) return

        // Exponential backoff reconnect
        const delay = backoffRef.current
        backoffRef.current = Math.min(backoffRef.current * 2, MAX_BACKOFF)
        reconnectTimerRef.current = setTimeout(connect, delay)
      }

      ws.onerror = () => {
        // onclose will fire after onerror — reconnect handled there
      }
    }

    connect()

    return cleanup
  }, [isAuthenticated, accessToken, handleEvent, cleanup])

  return statusRef.current
}
