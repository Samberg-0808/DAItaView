import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import AdminLayout from './AdminLayout'
import api from '@/api/client'
import type { DataSource } from '@/types'
import styles from './DataSourceAdminPage.module.css'

export default function KnowledgeIndexPage() {
  const navigate = useNavigate()
  const { data: sources = [], isLoading } = useQuery<DataSource[]>({
    queryKey: ['sources'],
    queryFn: () => api.get('/sources').then(r => r.data),
  })

  const dbSources = sources.filter(s => ['postgres', 'mysql', 'sqlite'].includes(s.type))

  return (
    <AdminLayout>
      <div className={styles.content}>
        <h1 className={styles.title}>Knowledge Editor</h1>

        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle}>Select a data source to edit its knowledge base</h2>
          </div>

          {isLoading && <p className={styles.empty}>Loading…</p>}

          {!isLoading && dbSources.length === 0 && (
            <p className={styles.empty}>
              No database sources connected yet. Go to <strong>Data Sources</strong> to add one.
            </p>
          )}

          <div className={styles.sourceList}>
            {dbSources.map(s => (
              <div key={s.id} className={styles.sourceCard} style={{ cursor: 'pointer' }} onClick={() => navigate(`/admin/knowledge/${s.id}`)}>
                <div className={styles.sourceInfo}>
                  <span className={styles.sourceName}>{s.name}</span>
                  <span className={styles.sourceType}>{s.type}</span>
                </div>
                <div className={styles.sourceActions}>
                  <button className={styles.refreshBtn}>Edit Knowledge →</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AdminLayout>
  )
}
