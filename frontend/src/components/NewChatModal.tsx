import { useQuery, useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import api from '@/api/client'
import type { DataSource } from '@/types'
import styles from './NewChatModal.module.css'

export default function NewChatModal({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate()
  const [selected, setSelected] = useState<string | null>(null)

  const { data: sources = [], isLoading } = useQuery<DataSource[]>({
    queryKey: ['sources'],
    queryFn: () => api.get('/sources').then(r => r.data),
  })

  const createMut = useMutation({
    mutationFn: (sourceId: string) => api.post('/sessions', { source_id: sourceId }).then(r => r.data),
    onSuccess: (session) => {
      onClose()
      navigate(`/chat/${session.id}`)
    },
  })

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        <h2 className={styles.title}>Select a data source</h2>
        {isLoading && <p className={styles.empty}>Loading…</p>}
        {!isLoading && sources.length === 0 && (
          <p className={styles.empty}>You don't have access to any data sources. Contact your admin.</p>
        )}
        <div className={styles.list}>
          {sources.map(s => (
            <div
              key={s.id}
              className={`${styles.item} ${selected === s.id ? styles.selected : ''}`}
              onClick={() => setSelected(s.id)}
            >
              <span className={styles.type}>{s.type}</span>
              <span className={styles.name}>{s.name}</span>
            </div>
          ))}
        </div>
        <div className={styles.footer}>
          <button className={styles.cancel} onClick={onClose}>Cancel</button>
          <button
            className={styles.start}
            disabled={!selected || createMut.isPending}
            onClick={() => selected && createMut.mutate(selected)}
          >
            Start Chat
          </button>
        </div>
      </div>
    </div>
  )
}
