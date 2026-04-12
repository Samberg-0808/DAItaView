import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Editor from '@monaco-editor/react'
import AdminLayout from './AdminLayout'
import api from '@/api/client'
import styles from './KnowledgeEditorPage.module.css'

type KnowledgeLayer = 'global' | 'overview' | 'domain' | 'table' | 'example'

interface FileRef {
  layer: KnowledgeLayer
  name: string       // "" for global/overview
  label: string      // display label in tree
}

interface ListFilesResponse {
  global_exists: boolean
  overview_exists: boolean
  domains: string[]
  tables: string[]
  examples: string[]
}

interface GapSignal {
  id: string
  question_text: string
  frequency: number
  last_seen_at: string
  resolved: boolean
}

function MarkdownPreview({ content }: { content: string }) {
  const html = content
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br/>')
  return <div className={styles.preview} dangerouslySetInnerHTML={{ __html: html }} />
}

function buildFileList(data: ListFilesResponse): FileRef[] {
  const files: FileRef[] = []
  if (data.global_exists)  files.push({ layer: 'global',   name: '', label: 'global.md' })
  if (data.overview_exists) files.push({ layer: 'overview', name: '', label: 'overview.md' })
  data.domains.forEach(n  => files.push({ layer: 'domain',  name: n, label: `domains/${n}.md` }))
  data.tables.forEach(n   => files.push({ layer: 'table',   name: n, label: `tables/${n}.md` }))
  data.examples.forEach(n => files.push({ layer: 'example', name: n, label: `examples/${n}.md` }))
  return files
}

function fileKey(f: FileRef) { return `${f.layer}::${f.name}` }

export default function KnowledgeEditorPage() {
  const { sourceId } = useParams<{ sourceId: string }>()
  const qc = useQueryClient()
  const [selected, setSelected] = useState<FileRef | null>(null)
  const [editorContent, setEditorContent] = useState('')
  const [activeTab, setActiveTab] = useState<'editor' | 'gaps'>('editor')
  const [newFileLayer, setNewFileLayer] = useState<KnowledgeLayer>('domain')
  const [newFileName, setNewFileName] = useState('')
  const [showNewFile, setShowNewFile] = useState(false)

  const { data: listData, isLoading } = useQuery<ListFilesResponse>({
    queryKey: ['knowledge', sourceId],
    queryFn: () => api.get(`/knowledge/${sourceId}`).then(r => r.data),
    enabled: !!sourceId,
  })

  const files: FileRef[] = listData ? buildFileList(listData) : []

  const { data: gaps = [] } = useQuery<GapSignal[]>({
    queryKey: ['knowledge-gaps', sourceId],
    queryFn: () => api.get(`/knowledge/${sourceId}/gaps`).then(r => r.data),
    enabled: !!sourceId,
  })

  function selectFile(f: FileRef) {
    setSelected(f)
    api.get(`/knowledge/${sourceId}/file`, { params: { layer: f.layer, name: f.name } })
      .then(r => setEditorContent(r.data?.content ?? ''))
  }

  const saveMut = useMutation({
    mutationFn: () => api.put(`/knowledge/${sourceId}/file`, {
      layer: selected!.layer,
      name: selected!.name,
      content: editorContent,
    }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['knowledge', sourceId] }),
  })

  const createMut = useMutation({
    mutationFn: ({ layer, name }: { layer: KnowledgeLayer; name: string }) =>
      api.put(`/knowledge/${sourceId}/file`, { layer, name, content: `# ${name || layer}\n` }),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ['knowledge', sourceId] })
      setShowNewFile(false)
      setNewFileName('')
      // Auto-select the new file after refetch
      const newRef: FileRef = { layer: vars.layer, name: vars.name, label: '' }
      setTimeout(() => selectFile(newRef), 300)
    },
  })

  const resolveMut = useMutation({
    mutationFn: (id: string) => api.post(`/knowledge/${sourceId}/gaps/${id}/resolve`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['knowledge-gaps', sourceId] }),
  })

  const SINGLETON_LAYERS: KnowledgeLayer[] = ['global', 'overview']
  const needsName = !SINGLETON_LAYERS.includes(newFileLayer)

  return (
    <AdminLayout>
      <div className={styles.body}>
        {/* File tree */}
        <aside className={styles.tree}>
          <p className={styles.treeTitle}>Knowledge Files</p>

          {isLoading && <p className={styles.treeEmpty}>Loading…</p>}

          {files.map(f => (
            <div
              key={fileKey(f)}
              className={`${styles.treeItem} ${selected && fileKey(selected) === fileKey(f) ? styles.treeActive : ''}`}
              onClick={() => selectFile(f)}
            >
              {f.label}
            </div>
          ))}

          {!isLoading && files.length === 0 && (
            <p className={styles.treeEmpty}>No files yet. Create one below.</p>
          )}

          {/* New file form */}
          <div style={{ marginTop: 12, padding: '0 4px' }}>
            {!showNewFile ? (
              <button
                onClick={() => setShowNewFile(true)}
                style={{ background: 'none', border: '1px dashed #94a3b8', borderRadius: 5, color: '#64748b', cursor: 'pointer', fontSize: 12, padding: '5px 8px', width: '100%' }}
              >
                + New file
              </button>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <select
                  value={newFileLayer}
                  onChange={e => setNewFileLayer(e.target.value as KnowledgeLayer)}
                  style={{ fontSize: 12, padding: '4px 6px', borderRadius: 4, border: '1px solid #e2e8f0' }}
                >
                  <option value="global">global</option>
                  <option value="overview">overview</option>
                  <option value="domain">domain</option>
                  <option value="table">table</option>
                  <option value="example">example</option>
                </select>
                {needsName && (
                  <input
                    placeholder="file name (no .md)"
                    value={newFileName}
                    onChange={e => setNewFileName(e.target.value)}
                    style={{ fontSize: 12, padding: '4px 6px', borderRadius: 4, border: '1px solid #e2e8f0', outline: 'none' }}
                  />
                )}
                <div style={{ display: 'flex', gap: 4 }}>
                  <button
                    disabled={createMut.isPending || (needsName && !newFileName.trim())}
                    onClick={() => createMut.mutate({ layer: newFileLayer, name: needsName ? newFileName.trim() : '' })}
                    style={{ background: '#eff6ff', border: '1px solid #3b82f6', borderRadius: 4, color: '#1d4ed8', cursor: 'pointer', flex: 1, fontSize: 12, padding: '4px 0' }}
                  >
                    {createMut.isPending ? '…' : 'Create'}
                  </button>
                  <button
                    onClick={() => { setShowNewFile(false); setNewFileName('') }}
                    style={{ background: 'none', border: '1px solid #e2e8f0', borderRadius: 4, color: '#64748b', cursor: 'pointer', fontSize: 12, padding: '4px 8px' }}
                  >
                    ✕
                  </button>
                </div>
              </div>
            )}
          </div>
        </aside>

        {/* Main area */}
        <main className={styles.main}>
          <div className={styles.tabs}>
            <button className={`${styles.tab} ${activeTab === 'editor' ? styles.tabActive : ''}`} onClick={() => setActiveTab('editor')}>Editor</button>
            <button className={`${styles.tab} ${activeTab === 'gaps' ? styles.tabActive : ''}`} onClick={() => setActiveTab('gaps')}>
              Knowledge Gaps {gaps.length > 0 && <span className={styles.badge}>{gaps.length}</span>}
            </button>
          </div>

          {activeTab === 'editor' && (
            <div className={styles.editorArea}>
              {selected ? (
                <>
                  <div className={styles.editorHeader}>
                    <span className={styles.filePath}>{selected.label || `${selected.layer}/${selected.name}`}</span>
                    <button className={styles.saveBtn} onClick={() => saveMut.mutate()} disabled={saveMut.isPending}>
                      {saveMut.isPending ? 'Saving…' : 'Save'}
                    </button>
                  </div>
                  <div className={styles.editorPreviewSplit}>
                    <div className={styles.editorPane}>
                      <Editor
                        height="100%"
                        language="markdown"
                        theme="vs-light"
                        value={editorContent}
                        onChange={v => setEditorContent(v ?? '')}
                        options={{ minimap: { enabled: false }, wordWrap: 'on', fontSize: 13 }}
                      />
                    </div>
                    <div className={styles.previewPane}>
                      <MarkdownPreview content={editorContent} />
                    </div>
                  </div>
                </>
              ) : (
                <div className={styles.noFile}>
                  {files.length === 0
                    ? 'No knowledge files yet. Use "+ New file" in the sidebar to create one.'
                    : 'Select a file from the tree to edit.'}
                </div>
              )}
            </div>
          )}

          {activeTab === 'gaps' && (
            <div className={styles.gapsArea}>
              <p className={styles.gapsHint}>Unresolved knowledge gaps — questions the system couldn't answer without admin input.</p>
              {gaps.length === 0 && <p className={styles.noGaps}>No open gaps.</p>}
              {gaps.map(g => (
                <div key={g.id} className={styles.gapCard}>
                  <div className={styles.gapInfo}>
                    <p className={styles.gapQuestion}>{g.question_text}</p>
                    <p className={styles.gapMeta}>Asked {g.frequency}x · Last seen {new Date(g.last_seen_at).toLocaleDateString()}</p>
                  </div>
                  <div className={styles.gapActions}>
                    <button className={styles.addToKbBtn} onClick={() => { setActiveTab('editor') }}>Add to KB</button>
                    <button className={styles.dismissBtn} onClick={() => resolveMut.mutate(g.id)}>Dismiss</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </main>
      </div>
    </AdminLayout>
  )
}
