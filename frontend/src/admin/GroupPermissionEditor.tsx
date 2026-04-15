import { useEffect, useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import api from '@/api/client'
import type { DataSource, Group } from '@/types'
import styles from './PermissionEditor.module.css'

interface TablePermission {
  source_id: string
  permitted_tables: string[] | null
}

interface Props {
  group: Group
  onClose: () => void
}

type AccessLevel = 'none' | 'full' | 'table'

const FILE_TYPES = ['csv', 'json', 'parquet']

function accessLevelsForSource(src: DataSource): AccessLevel[] {
  return FILE_TYPES.includes(src.type) ? ['none', 'full'] : ['none', 'full', 'table']
}

export default function GroupPermissionEditor({ group, onClose }: Props) {
  const { data: sources = [] } = useQuery<DataSource[]>({
    queryKey: ['sources'],
    queryFn: () => api.get('/sources').then(r => r.data),
  })

  const { data: existingPerms = [] } = useQuery<TablePermission[]>({
    queryKey: ['group-permissions', group.id],
    queryFn: () => api.get(`/groups/${group.id}/permissions`).then(r => r.data),
  })

  const [config, setConfig] = useState<Record<string, { access: AccessLevel; tables: string[] }>>({})
  const [schemaTables, setSchemaTables] = useState<Record<string, string[]>>({})

  useEffect(() => {
    const init: typeof config = {}
    for (const src of sources) {
      const perm = existingPerms.find(p => p.source_id === src.id)
      if (!perm) { init[src.id] = { access: 'none', tables: [] }; continue }
      if (perm.permitted_tables === null) init[src.id] = { access: 'full', tables: [] }
      else init[src.id] = { access: 'table', tables: perm.permitted_tables }
    }
    setConfig(init)
  }, [sources, existingPerms])

  async function loadTables(sourceId: string) {
    if (schemaTables[sourceId]) return
    try {
      const r = await api.get(`/sources/${sourceId}/schema`)
      const tables: string[] = Object.keys(r.data ?? {})
      setSchemaTables(prev => ({ ...prev, [sourceId]: tables }))
    } catch {
      setSchemaTables(prev => ({ ...prev, [sourceId]: [] }))
    }
  }

  const saveMut = useMutation({
    mutationFn: async () => {
      for (const [sourceId, { access, tables }] of Object.entries(config)) {
        if (access === 'none') {
          await api.delete(`/groups/${group.id}/permissions/${sourceId}`).catch(() => {})
        } else {
          await api.post(`/groups/${group.id}/permissions`, {
            source_id: sourceId,
            permitted_tables: access === 'full' ? null : tables,
          })
        }
      }
    },
    onSuccess: onClose,
  })

  function setAccess(sourceId: string, access: AccessLevel) {
    setConfig(prev => ({ ...prev, [sourceId]: { ...prev[sourceId], access, tables: [] } }))
    if (access === 'table') loadTables(sourceId)
  }

  function toggleTable(sourceId: string, table: string) {
    setConfig(prev => {
      const cur = prev[sourceId].tables
      const next = cur.includes(table) ? cur.filter(t => t !== table) : [...cur, table]
      return { ...prev, [sourceId]: { ...prev[sourceId], tables: next } }
    })
  }

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        <h2 className={styles.title}>Permissions — {group.name}</h2>
        <div className={styles.list}>
          {sources.map(src => {
            const cfg = config[src.id] ?? { access: 'none', tables: [] }
            const levels = accessLevelsForSource(src)
            return (
              <div key={src.id} className={styles.sourceRow}>
                <div className={styles.sourceHeader}>
                  <span className={styles.sourceName}>{src.name}</span>
                  <div className={styles.accessBtns}>
                    {levels.map(a => (
                      <button
                        key={a}
                        className={`${styles.accessBtn} ${cfg.access === a ? styles.active : ''}`}
                        onClick={() => setAccess(src.id, a)}
                      >{a}</button>
                    ))}
                  </div>
                </div>
                {cfg.access === 'table' && (
                  <div className={styles.tableList}>
                    {(schemaTables[src.id] ?? []).map(t => (
                      <label key={t} className={styles.tableCheck}>
                        <input type="checkbox" checked={cfg.tables.includes(t)} onChange={() => toggleTable(src.id, t)} />
                        {t}
                      </label>
                    ))}
                    {!schemaTables[src.id] && <span className={styles.loading}>Loading tables…</span>}
                  </div>
                )}
              </div>
            )
          })}
        </div>
        <div className={styles.footer}>
          <button className={styles.cancel} onClick={onClose}>Cancel</button>
          <button className={styles.save} onClick={() => saveMut.mutate()} disabled={saveMut.isPending}>
            {saveMut.isPending ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  )
}
