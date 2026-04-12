import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import NavBar from '@/components/NavBar'
import SessionSidebar from '@/components/SessionSidebar'
import TurnMessage from '@/components/TurnMessage'
import { useSessionWebSocket } from '@/hooks/useSessionWebSocket'
import { useAuth } from '@/context/AuthContext'
import api from '@/api/client'
import type { ChatSession, ClarificationQuestion, SessionTurn } from '@/types'
import styles from './ChatPage.module.css'

export default function ChatPage() {
  const { sessionId } = useParams()
  const { token } = useAuth()
  const qc = useQueryClient()
  const bottomRef = useRef<HTMLDivElement>(null)
  const [input, setInput] = useState('')
  const [turns, setTurns] = useState<SessionTurn[]>([])
  const [pendingClarify, setPendingClarify] = useState<ClarificationQuestion[] | null>(null)
  const [clarifyAnswers, setClarifyAnswers] = useState<Record<string, string>>({})
  const [showStaleBanner, setShowStaleBanner] = useState(false)

  const { data: session } = useQuery<ChatSession>({
    queryKey: ['session', sessionId],
    queryFn: () => api.get(`/sessions/${sessionId}`).then(r => r.data),
    enabled: !!sessionId,
  })

  // Load existing turns on session open
  useEffect(() => {
    if (!sessionId) return
    api.get(`/sessions/${sessionId}/turns`).then(r => {
      const fetchedTurns: SessionTurn[] = r.data
      setTurns(fetchedTurns)
      // Check staleness: if last result is older than 1 hour
      const last = fetchedTurns[fetchedTurns.length - 1]
      if (last?.data_snapshot_at) {
        const age = (Date.now() - new Date(last.data_snapshot_at).getTime()) / 3600000
        if (age > 1) setShowStaleBanner(true)
      }
    })
  }, [sessionId])

  const ws = useSessionWebSocket(sessionId || '', token || '')

  // When WS completes a turn, reload turns from API
  useEffect(() => {
    if (ws.status === 'done' && ws.lastResult) {
      api.get(`/sessions/${sessionId}/turns`).then(r => setTurns(r.data))
      qc.invalidateQueries({ queryKey: ['sessions'] })
    }
    if (ws.status === 'clarifying' && ws.clarifyQuestions.length > 0) {
      setPendingClarify(ws.clarifyQuestions)
    }
  }, [ws.status, ws.lastResult])

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [turns, ws.status])

  function handleSend() {
    const q = input.trim()
    if (!q || !sessionId) return
    setInput('')
    setPendingClarify(null)
    setClarifyAnswers({})
    ws.sendQuestion(q)
  }

  function handleClarifySend() {
    const q = input.trim() || Object.keys(clarifyAnswers)[0] || ''
    ws.sendQuestion(q, clarifyAnswers)
    setPendingClarify(null)
  }

  async function handleRefreshAll() {
    await api.post(`/sessions/${sessionId}/refresh`)
    const r = await api.get(`/sessions/${sessionId}/turns`)
    setTurns(r.data)
    setShowStaleBanner(false)
  }

  const isLoading = ['thinking', 'generating', 'executing'].includes(ws.status)

  if (!sessionId) {
    return (
      <div className={styles.shell}>
        <NavBar />
        <div className={styles.body}>
          <SessionSidebar />
          <main className={styles.empty}>
            <p>Select a session or start a new chat.</p>
          </main>
        </div>
      </div>
    )
  }

  return (
    <div className={styles.shell}>
      <NavBar />
      <div className={styles.body}>
        <SessionSidebar />
        <main className={styles.main}>
          {/* Session header */}
          <div className={styles.header}>
            <span className={styles.sessionTitle}>{session?.title || 'Chat'}</span>
          </div>

          {/* Staleness banner */}
          {showStaleBanner && (
            <div className={styles.staleBanner}>
              ⚠ Results in this session may be outdated.
              <button onClick={handleRefreshAll}>Refresh all</button>
              <button onClick={() => setShowStaleBanner(false)}>Dismiss</button>
            </div>
          )}

          {/* Messages */}
          <div className={styles.messages}>
            {turns.length === 0 && !isLoading && (
              <p className={styles.emptyMsg}>Ask your first question below.</p>
            )}
            {turns.map((t, i) => (
              <TurnMessage
                key={t.id}
                turn={t}
                isFirst={i === 0}
                sessionId={sessionId}
                onRefreshed={(updated) => setTurns(prev => prev.map(x => x.id === t.id ? { ...x, result_cache: updated } : x))}
                onReask={(q) => { setInput(q); ws.sendQuestion(q) }}
              />
            ))}
            {isLoading && (
              <div className={styles.statusBadge}>
                <span className={styles.spinner} /> {ws.status}…
              </div>
            )}
            {pendingClarify && (
              <div className={styles.clarifyBlock}>
                <p className={styles.clarifyLabel}>A few quick questions before I proceed:</p>
                {pendingClarify.map((q, i) => (
                  <div key={i} className={styles.clarifyItem}>
                    <p className={styles.clarifyQ}>{q.text}</p>
                    {q.options.length > 0 ? (
                      <div className={styles.options}>
                        {q.options.map(opt => (
                          <button
                            key={opt}
                            className={`${styles.opt} ${clarifyAnswers[q.text] === opt ? styles.selected : ''}`}
                            onClick={() => setClarifyAnswers(prev => ({ ...prev, [q.text]: opt }))}
                          >{opt}</button>
                        ))}
                      </div>
                    ) : (
                      <input
                        className={styles.clarifyInput}
                        placeholder="Your answer…"
                        value={clarifyAnswers[q.text] || ''}
                        onChange={e => setClarifyAnswers(prev => ({ ...prev, [q.text]: e.target.value }))}
                      />
                    )}
                  </div>
                ))}
                <button className={styles.submitClarify} onClick={handleClarifySend}>Submit answers</button>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input bar */}
          <div className={styles.inputBar}>
            <input
              className={styles.input}
              placeholder="Ask a question about your data…"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
              disabled={isLoading || !!pendingClarify}
            />
            <button className={styles.send} onClick={handleSend} disabled={isLoading || !input.trim()}>Send</button>
          </div>
        </main>
      </div>
    </div>
  )
}
