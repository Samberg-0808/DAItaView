import { useCallback, useEffect, useRef, useState } from 'react'
import type { ClarificationQuestion } from '@/types'

type WSEvent =
  | { event: 'thinking' }
  | { event: 'clarifying'; data: { questions: ClarificationQuestion[]; turn_id: string } }
  | { event: 'generating' }
  | { event: 'executing'; data: { attempt: number } }
  | { event: 'done'; data: { turn_id: string; result: any } }
  | { event: 'error'; data: { message: string; error_type?: string } }

type Status = 'idle' | 'thinking' | 'clarifying' | 'generating' | 'executing' | 'done' | 'error'

interface UseSessionWebSocketReturn {
  status: Status
  clarifyQuestions: ClarificationQuestion[]
  pendingTurnId: string | null
  sendQuestion: (question: string, clarificationAnswers?: Record<string, string>) => void
  lastResult: any
  lastError: string | null
  reset: () => void
}

export function useSessionWebSocket(sessionId: string, token: string): UseSessionWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null)
  const [status, setStatus] = useState<Status>('idle')
  const [clarifyQuestions, setClarifyQuestions] = useState<ClarificationQuestion[]>([])
  const [pendingTurnId, setPendingTurnId] = useState<string | null>(null)
  const [lastResult, setLastResult] = useState<any>(null)
  const [lastError, setLastError] = useState<string | null>(null)

  const wsUrl = (import.meta.env.VITE_WS_URL || 'ws://localhost:8000')
  const url = `${wsUrl}/sessions/${sessionId}/query`

  useEffect(() => {
    if (!sessionId) return

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onmessage = (e) => {
      const msg: WSEvent = JSON.parse(e.data)
      switch (msg.event) {
        case 'thinking': setStatus('thinking'); break
        case 'generating': setStatus('generating'); break
        case 'executing': setStatus('executing'); break
        case 'clarifying':
          setStatus('clarifying')
          setClarifyQuestions(msg.data.questions)
          setPendingTurnId(msg.data.turn_id)
          break
        case 'done':
          setStatus('done')
          setLastResult(msg.data.result)
          break
        case 'error':
          setStatus('error')
          setLastError(msg.data.message)
          break
      }
    }

    return () => ws.close()
  }, [url, sessionId])

  const sendQuestion = useCallback((question: string, clarificationAnswers?: Record<string, string>) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    setStatus('thinking')
    setLastError(null)
    const payload: any = { question, token }
    if (clarificationAnswers) {
      payload.clarification_answers = Object.entries(clarificationAnswers).map(([q, a]) => ({ question: q, answer: a }))
    }
    wsRef.current.send(JSON.stringify(payload))
  }, [token])

  const reset = useCallback(() => {
    setStatus('idle')
    setClarifyQuestions([])
    setPendingTurnId(null)
    setLastResult(null)
    setLastError(null)
  }, [])

  return { status, clarifyQuestions, pendingTurnId, sendQuestion, lastResult, lastError, reset }
}
