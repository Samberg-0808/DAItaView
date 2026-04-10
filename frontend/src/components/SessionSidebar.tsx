import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/api/client'
import type { ChatSession, DataSource } from '@/types'
import NewChatModal from './NewChatModal'
import styles from './SessionSidebar.module.css'

function groupByRecency(sessions: ChatSession[]) {
  const now = Date.now()
  const groups: Record<string, ChatSession[]> = { Pinned: [], Today: [], Yesterday: [], 'Last 7 days': [], Older: [] }
  for (const s of sessions) {
    if (s.is_pinned) { groups['Pinned'].push(s); continue }
    const diff = (now - new Date(s.last_active_at).getTime()) / 86400000
    if (diff < 1) groups['Today'].push(s)
    else if (diff < 2) groups['Yesterday'].push(s)
    else if (diff < 7) groups['Last 7 days'].push(s)
    else groups['Older'].push(s)
  }
  return groups
}

export default function SessionSidebar() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')

  const { data: sessions = [] } = useQuery<ChatSession[]>({
    queryKey: ['sessions'],
    queryFn: () => api.get('/sessions').then(r => r.data),
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`/sessions/${id}`),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: ['sessions'] })
      if (sessionId === id) navigate('/chat')
    },
  })

  const patchMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => api.patch(`/sessions/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sessions'] }),
  })

  const groups = groupByRecency(sessions)

  function startRename(s: ChatSession) {
    setEditingId(s.id)
    setEditTitle(s.title)
  }

  function commitRename(id: string) {
    patchMut.mutate({ id, data: { title: editTitle } })
    setEditingId(null)
  }

  return (
    <aside className={styles.sidebar}>
      <button className={styles.newChat} onClick={() => setShowModal(true)}>+ New Chat</button>

      {Object.entries(groups).map(([group, items]) =>
        items.length === 0 ? null : (
          <div key={group}>
            <p className={styles.groupLabel}>{group}</p>
            {items.map(s => (
              <div
                key={s.id}
                className={`${styles.item} ${sessionId === s.id ? styles.active : ''}`}
                onClick={() => navigate(`/chat/${s.id}`)}
              >
                {editingId === s.id ? (
                  <input
                    className={styles.renameInput}
                    value={editTitle}
                    onChange={e => setEditTitle(e.target.value)}
                    onBlur={() => commitRename(s.id)}
                    onKeyDown={e => e.key === 'Enter' && commitRename(s.id)}
                    autoFocus
                    onClick={e => e.stopPropagation()}
                  />
                ) : (
                  <span className={styles.title} onDoubleClick={() => startRename(s)}>{s.title}</span>
                )}
                <div className={styles.actions} onClick={e => e.stopPropagation()}>
                  <button onClick={() => patchMut.mutate({ id: s.id, data: { is_pinned: !s.is_pinned } })} title={s.is_pinned ? 'Unpin' : 'Pin'}>
                    {s.is_pinned ? '📌' : '📍'}
                  </button>
                  <button onClick={() => { if (confirm('Delete this session?')) deleteMut.mutate(s.id) }}>🗑</button>
                </div>
              </div>
            ))}
          </div>
        )
      )}

      {showModal && <NewChatModal onClose={() => setShowModal(false)} />}
    </aside>
  )
}
