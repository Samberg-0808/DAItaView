import { useMutation } from '@tanstack/react-query'
import api from '@/api/client'
import type { SessionTurn } from '@/types'
import styles from './StalenessBar.module.css'

function relativeTime(iso: string) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return new Date(iso).toLocaleDateString()
}

interface Props {
  snapshotAt: string | null
  sessionId: string
  turnId: string
  onRefreshed: (t: any) => void
  onReask: () => void
}

export default function StalenessBar({ snapshotAt, sessionId, turnId, onRefreshed, onReask }: Props) {
  const refreshMut = useMutation({
    mutationFn: () => api.post(`/sessions/${sessionId}/turns/${turnId}/refresh`).then(r => r.data),
    onSuccess: onRefreshed,
  })

  const hasError = refreshMut.data?.type === 'error' && refreshMut.data?.error_type === 'schema_change'

  if (hasError) {
    return (
      <div className={styles.bar}>
        <span className={styles.error}>⚠ Refresh failed — schema may have changed: {refreshMut.data.error}</span>
        <button className={styles.action} onClick={onReask}>Re-ask</button>
      </div>
    )
  }

  return (
    <div className={styles.bar}>
      {snapshotAt && <span className={styles.time}>Last updated: {relativeTime(snapshotAt)}</span>}
      <button className={styles.action} onClick={() => refreshMut.mutate()} disabled={refreshMut.isPending}>
        {refreshMut.isPending ? 'Refreshing…' : '↻ Refresh'}
      </button>
    </div>
  )
}
