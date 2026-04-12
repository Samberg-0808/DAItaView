import { useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import AdminLayout from './AdminLayout'
import api from '@/api/client'
import type { DataSource } from '@/types'
import styles from './DataSourceAdminPage.module.css'

type DbType = 'postgres' | 'mysql' | 'sqlite'
type FileType = 'csv' | 'json' | 'parquet'

const DB_TYPES: DbType[] = ['postgres', 'mysql', 'sqlite']

export default function DataSourceAdminPage() {
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [showDbForm, setShowDbForm] = useState(false)
  const [dbForm, setDbForm] = useState({ name: '', type: 'postgres' as DbType, host: '', port: '5432', database: '', username: '', password: '' })
  const [uploadName, setUploadName] = useState('')
  const [uploadType, setUploadType] = useState<FileType>('csv')
  const [uploadFile, setUploadFile] = useState<File | null>(null)

  const { data: sources = [], isLoading } = useQuery<DataSource[]>({
    queryKey: ['sources'],
    queryFn: () => api.get('/sources').then(r => r.data),
  })

  const addDbMut = useMutation({
    mutationFn: () => api.post('/sources', {
      name: dbForm.name,
      type: dbForm.type,
      connection_config: { host: dbForm.host, port: Number(dbForm.port), database: dbForm.database, username: dbForm.username, password: dbForm.password },
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['sources'] }); setShowDbForm(false) },
  })

  const uploadMut = useMutation({
    mutationFn: () => {
      if (!uploadFile) throw new Error('No file selected')
      const fd = new FormData()
      fd.append('file', uploadFile)
      fd.append('name', uploadName || uploadFile.name)
      fd.append('type', uploadType)
      return api.post('/sources/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['sources'] }); setUploadFile(null); setUploadName('') },
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`/sources/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sources'] }),
  })

  const refreshMut = useMutation({
    mutationFn: (id: string) => api.post(`/sources/${id}/refresh-schema`),
  })

  return (
    <AdminLayout>
      <div className={styles.content}>
        <h1 className={styles.title}>Data Sources</h1>

        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle}>Connected sources</h2>
            <button className={styles.addBtn} onClick={() => setShowDbForm(v => !v)}>+ Add Database</button>
          </div>

          {showDbForm && (
            <div className={styles.form}>
              <input className={styles.input} placeholder="Source name" value={dbForm.name} onChange={e => setDbForm(p => ({ ...p, name: e.target.value }))} />
              <select className={styles.select} value={dbForm.type} onChange={e => setDbForm(p => ({ ...p, type: e.target.value as DbType }))}>
                {DB_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
              <input className={styles.input} placeholder="Host" value={dbForm.host} onChange={e => setDbForm(p => ({ ...p, host: e.target.value }))} />
              <input className={styles.input} placeholder="Port" value={dbForm.port} onChange={e => setDbForm(p => ({ ...p, port: e.target.value }))} style={{ maxWidth: 80 }} />
              <input className={styles.input} placeholder="Database" value={dbForm.database} onChange={e => setDbForm(p => ({ ...p, database: e.target.value }))} />
              <input className={styles.input} placeholder="Username" value={dbForm.username} onChange={e => setDbForm(p => ({ ...p, username: e.target.value }))} />
              <input className={styles.input} placeholder="Password" type="password" value={dbForm.password} onChange={e => setDbForm(p => ({ ...p, password: e.target.value }))} />
              <button className={styles.saveBtn} onClick={() => addDbMut.mutate()} disabled={addDbMut.isPending}>
                {addDbMut.isPending ? 'Connecting…' : 'Connect'}
              </button>
              {addDbMut.isError && <p className={styles.error}>{String((addDbMut.error as any)?.response?.data?.detail ?? 'Connection failed')}</p>}
            </div>
          )}

          {isLoading ? <p className={styles.empty}>Loading…</p> : (
            <div className={styles.sourceList}>
              {sources.map(s => (
                <div key={s.id} className={styles.sourceCard}>
                  <div className={styles.sourceInfo}>
                    <span className={styles.sourceName}>{s.name}</span>
                    <span className={styles.sourceType}>{s.type}</span>
                  </div>
                  <div className={styles.sourceActions}>
                    <button className={styles.refreshBtn} onClick={() => refreshMut.mutate(s.id)} disabled={refreshMut.isPending}>↻ Refresh Schema</button>
                    <button className={styles.deleteBtn} onClick={() => { if (confirm(`Delete source "${s.name}"?`)) deleteMut.mutate(s.id) }}>Delete</button>
                  </div>
                </div>
              ))}
              {sources.length === 0 && <p className={styles.empty}>No sources connected.</p>}
            </div>
          )}
        </div>

        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Upload file source</h2>
          <div className={styles.uploadZone} onClick={() => fileRef.current?.click()} onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); setUploadFile(e.dataTransfer.files[0]) }}>
            {uploadFile ? <span>{uploadFile.name}</span> : <span>Drop a CSV / JSON / Parquet file here, or click to browse</span>}
          </div>
          <input ref={fileRef} type="file" accept=".csv,.json,.parquet" style={{ display: 'none' }} onChange={e => e.target.files && setUploadFile(e.target.files[0])} />
          {uploadFile && (
            <div className={styles.uploadForm}>
              <input className={styles.input} placeholder="Source name (optional)" value={uploadName} onChange={e => setUploadName(e.target.value)} />
              <select className={styles.select} value={uploadType} onChange={e => setUploadType(e.target.value as FileType)}>
                {(['csv', 'json', 'parquet'] as FileType[]).map(t => <option key={t} value={t}>{t}</option>)}
              </select>
              <button className={styles.saveBtn} onClick={() => uploadMut.mutate()} disabled={uploadMut.isPending}>
                {uploadMut.isPending ? 'Uploading…' : 'Upload'}
              </button>
            </div>
          )}
        </div>
      </div>
    </AdminLayout>
  )
}
