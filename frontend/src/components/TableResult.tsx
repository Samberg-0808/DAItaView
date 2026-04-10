import { useState } from 'react'
import ResultErrorBoundary from './ResultErrorBoundary'
import styles from './TableResult.module.css'

interface TableData {
  columns: string[]
  rows: any[][]
}

interface Props {
  data: TableData
}

const PAGE_SIZE = 50

type SortDir = 'asc' | 'desc' | null

function downloadCSV(columns: string[], rows: any[][]) {
  const escape = (v: any) => `"${String(v ?? '').replace(/"/g, '""')}"`
  const lines = [columns.map(escape).join(','), ...rows.map(r => r.map(escape).join(','))]
  const blob = new Blob([lines.join('\n')], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'table_data.csv'
  a.click()
  URL.revokeObjectURL(url)
}

function TableInner({ data }: Props) {
  const { columns, rows } = data
  const [sortCol, setSortCol] = useState<number | null>(null)
  const [sortDir, setSortDir] = useState<SortDir>(null)
  const [page, setPage] = useState(0)

  function handleSort(idx: number) {
    if (sortCol === idx) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortCol(idx)
      setSortDir('asc')
    }
    setPage(0)
  }

  const sorted = sortCol !== null && sortDir ? [...rows].sort((a, b) => {
    const av = a[sortCol], bv = b[sortCol]
    const cmp = av < bv ? -1 : av > bv ? 1 : 0
    return sortDir === 'asc' ? cmp : -cmp
  }) : rows

  const totalPages = Math.ceil(sorted.length / PAGE_SIZE)
  const paged = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  return (
    <div className={styles.wrap}>
      <div className={styles.toolbar}>
        <span className={styles.count}>{rows.length} rows</span>
        <button className={styles.csvBtn} onClick={() => downloadCSV(columns, rows)}>Export CSV</button>
      </div>
      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              {columns.map((col, i) => (
                <th key={i} className={styles.th} onClick={() => handleSort(i)}>
                  {col}
                  {sortCol === i ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ''}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paged.map((row, ri) => (
              <tr key={ri} className={styles.tr}>
                {row.map((cell, ci) => <td key={ci} className={styles.td}>{String(cell ?? '')}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {totalPages > 1 && (
        <div className={styles.pagination}>
          <button disabled={page === 0} onClick={() => setPage(p => p - 1)}>‹ Prev</button>
          <span>Page {page + 1} of {totalPages}</span>
          <button disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}>Next ›</button>
        </div>
      )}
    </div>
  )
}

export default function TableResult({ data }: Props) {
  return (
    <ResultErrorBoundary>
      <TableInner data={data} />
    </ResultErrorBoundary>
  )
}
