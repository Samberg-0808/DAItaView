import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Editor from '@monaco-editor/react'
import NavBar from '@/components/NavBar'
import api from '@/api/client'
import styles from './KnowledgeEditorPage.module.css'

interface KnowledgeFile {
  path: string
  name: string
}

interface GapSignal {
  id: string
  question_text: string
  frequency: number
  last_seen_at: string
  resolved: boolean
}

function MarkdownPreview({ content }: { content: string }) {
  // Minimal preview: convert headings, bold, newlines
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

export default function KnowledgeEditorPage() {
  const { sourceId } = useParams<{ sourceId: string }>()
  const qc = useQueryClient()
  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const [editorContent, setEditorContent] = useState('')
  const [activeTab, setActiveTab] = useState<'editor' | 'gaps'>('editor')

  const { data: files = [] } = useQuery<KnowledgeFile[]>({
    queryKey: ['knowledge', sourceId],
    queryFn: () => api.get(`/knowledge/${sourceId}`).then(r => r.data),
    enabled: !!sourceId,
  })

  const { data: gaps = [] } = useQuery<GapSignal[]>({
    queryKey: ['knowledge-gaps', sourceId],
    queryFn: () => api.get(`/knowledge/${sourceId}/gaps`).then(r => r.data),
    enabled: !!sourceId,
  })

  function selectFile(path: string) {
    setSelectedPath(path)
    api.get(`/knowledge/${sourceId}/file`, { params: { path } }).then(r => setEditorContent(r.data?.content ?? r.data ?? ''))
  }

  const saveMut = useMutation({
    mutationFn: () => api.put(`/knowledge/${sourceId}/file`, { path: selectedPath, content: editorContent }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['knowledge', sourceId] }),
  })

  const resolveMut = useMutation({
    mutationFn: (id: string) => api.post(`/knowledge/${sourceId}/gaps/${id}/resolve`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['knowledge-gaps', sourceId] }),
  })

  function openGapInEditor(gap: GapSignal) {
    const examplesFile = files.find(f => f.path.includes('examples/'))
    if (examplesFile) selectFile(examplesFile.path)
    else if (files.length > 0) selectFile(files[0].path)
    setActiveTab('editor')
  }

  return (
    <div className={styles.page}>
      <NavBar />
      <div className={styles.body}>
        {/* File tree */}
        <aside className={styles.tree}>
          <p className={styles.treeTitle}>Knowledge Files</p>
          {files.map(f => (
            <div
              key={f.path}
              className={`${styles.treeItem} ${selectedPath === f.path ? styles.treeActive : ''}`}
              onClick={() => selectFile(f.path)}
            >
              {f.name}
            </div>
          ))}
          {files.length === 0 && <p className={styles.treeEmpty}>No files yet</p>}
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
              {selectedPath ? (
                <>
                  <div className={styles.editorHeader}>
                    <span className={styles.filePath}>{selectedPath}</span>
                    <button className={styles.saveBtn} onClick={() => saveMut.mutate()} disabled={saveMut.isPending}>
                      {saveMut.isPending ? 'Saving…' : 'Save'}
                    </button>
                  </div>
                  <div className={styles.editorPreviewSplit}>
                    <div className={styles.editorPane}>
                      <Editor
                        height="100%"
                        language="markdown"
                        theme="vs-dark"
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
                <div className={styles.noFile}>Select a file from the tree to edit.</div>
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
                    <button className={styles.addToKbBtn} onClick={() => openGapInEditor(g)}>Add to KB</button>
                    <button className={styles.dismissBtn} onClick={() => resolveMut.mutate(g.id)}>Dismiss</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
