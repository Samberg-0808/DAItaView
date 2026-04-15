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

          <p style={{ fontSize: 13, color: '#64748b', lineHeight: 1.6, margin: '0 0 12px' }}>
            The knowledge editor lets you provide business context that the AI uses when answering
            questions about your data. For each data source you can describe tables, columns,
            metrics, and common queries in plain language. Select a data source below and click
            <strong> Edit Knowledge</strong> to open its editor.
          </p>

          <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: '14px 16px', marginBottom: 20, fontSize: 13, color: '#475569', lineHeight: 1.7 }}>
            <p style={{ margin: '0 0 8px', fontWeight: 600, color: '#1a1a2e' }}>Knowledge file types</p>
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              <li><strong>global.md</strong> — General rules and context shared across all data sources, such as company terminology, date conventions, or formatting preferences.</li>
              <li><strong>overview.md</strong> — A high-level summary of this specific data source: what it contains, how it is organized, and key relationships between tables.</li>
              <li><strong>domain</strong> — One file per business domain (e.g. "sales", "inventory"). Describes domain-specific metrics, KPIs, and business logic the AI should know.</li>
              <li><strong>table</strong> — One file per database table. Documents column meanings, accepted values, join keys, and any nuances not obvious from the schema alone.</li>
              <li><strong>example</strong> — Sample question-and-answer pairs that show the AI how to translate common business questions into correct queries.</li>
            </ul>
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
