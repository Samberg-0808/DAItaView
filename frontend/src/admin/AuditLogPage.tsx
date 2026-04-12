import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import AdminLayout from './AdminLayout'
import api from '@/api/client'
import styles from './AuditLogPage.module.css'

interface AuditEntry {
  id: string
  event_type: string
  user_id: string | null
  source_id: string | null
  details: any
  created_at: string
}

interface Filters {
  user_id: string
  event_type: string
  source_id: string
  date_from: string
  date_to: string
}

const EVENT_TYPES = ['', 'query_submitted', 'code_generated', 'code_blocked', 'query_completed', 'query_failed', 'login_success', 'login_failed', 'logout', 'sso_login', 'user_created', 'user_role_changed', 'source_connected', 'source_deleted', 'permission_granted', 'permission_revoked', 'knowledge_updated']

function downloadCSV(entries: AuditEntry[]) {
  const cols = ['id', 'event_type', 'user_id', 'source_id', 'created_at', 'details']
  const escape = (v: any) => `"${String(v ?? '').replace(/"/g, '""')}"`
  const rows = [cols.map(escape).join(','), ...entries.map(e => [e.id, e.event_type, e.user_id, e.source_id, e.created_at, JSON.stringify(e.details)].map(escape).join(','))]
  const blob = new Blob([rows.join('\n')], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'audit_log.csv'
  a.click()
  URL.revokeObjectURL(url)
}

export default function AuditLogPage() {
  const [filters, setFilters] = useState<Filters>({ user_id: '', event_type: '', source_id: '', date_from: '', date_to: '' })

  function setFilter(k: keyof Filters, v: string) { setFilters(p => ({ ...p, [k]: v })) }

  const params: Record<string, string> = {}
  if (filters.user_id) params.user_id = filters.user_id
  if (filters.event_type) params.event_type = filters.event_type
  if (filters.source_id) params.source_id = filters.source_id
  if (filters.date_from) params.date_from = filters.date_from
  if (filters.date_to) params.date_to = filters.date_to

  const { data: entries = [], isLoading } = useQuery<AuditEntry[]>({
    queryKey: ['audit', params],
    queryFn: () => api.get('/audit', { params }).then(r => r.data),
  })

  return (
    <AdminLayout>
      <div className={styles.content}>
        <div className={styles.header}>
          <h1 className={styles.title}>Audit Log</h1>
          <button className={styles.exportBtn} onClick={() => downloadCSV(entries)}>Export CSV</button>
        </div>

        <div className={styles.filters}>
          <input className={styles.filterInput} placeholder="User ID" value={filters.user_id} onChange={e => setFilter('user_id', e.target.value)} />
          <select className={styles.filterSelect} value={filters.event_type} onChange={e => setFilter('event_type', e.target.value)}>
            <option value="">All events</option>
            {EVENT_TYPES.filter(Boolean).map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <input className={styles.filterInput} placeholder="Source ID" value={filters.source_id} onChange={e => setFilter('source_id', e.target.value)} />
          <input className={styles.filterInput} type="date" value={filters.date_from} onChange={e => setFilter('date_from', e.target.value)} title="From" />
          <input className={styles.filterInput} type="date" value={filters.date_to} onChange={e => setFilter('date_to', e.target.value)} title="To" />
        </div>

        {isLoading ? <p className={styles.empty}>Loading…</p> : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Event</th>
                  <th>User ID</th>
                  <th>Source ID</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {entries.map(e => (
                  <tr key={e.id}>
                    <td className={styles.ts}>{new Date(e.created_at).toLocaleString()}</td>
                    <td><span className={styles.event}>{e.event_type}</span></td>
                    <td className={styles.mono}>{e.user_id ?? '—'}</td>
                    <td className={styles.mono}>{e.source_id ?? '—'}</td>
                    <td className={styles.details}>{JSON.stringify(e.details)}</td>
                  </tr>
                ))}
                {entries.length === 0 && <tr><td colSpan={5} className={styles.empty}>No entries match the current filters.</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AdminLayout>
  )
}
