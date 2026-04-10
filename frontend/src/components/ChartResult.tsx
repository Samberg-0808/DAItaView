import Plot from 'react-plotly.js'
import ResultErrorBoundary from './ResultErrorBoundary'
import styles from './ChartResult.module.css'

interface Props {
  data: any
}

function downloadCSV(figure: any) {
  const traces = figure?.data ?? []
  if (traces.length === 0) return
  const rows: string[][] = []
  for (const trace of traces) {
    const x: any[] = trace.x ?? []
    const y: any[] = trace.y ?? []
    const name = trace.name ?? 'series'
    if (rows.length === 0) rows.push(['x', name])
    x.forEach((xv: any, i: number) => rows.push([String(xv), String(y[i] ?? '')]))
  }
  const csv = rows.map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'chart_data.csv'
  a.click()
  URL.revokeObjectURL(url)
}

function ChartInner({ data }: Props) {
  const figure = data?.figure ?? data
  return (
    <div className={styles.wrap}>
      <div className={styles.actions}>
        <button className={styles.csvBtn} onClick={() => downloadCSV(figure)}>Export CSV</button>
      </div>
      <Plot
        data={figure?.data ?? []}
        layout={{ ...(figure?.layout ?? {}), autosize: true, paper_bgcolor: 'transparent', plot_bgcolor: '#1a1a1a', font: { color: '#ececec' } }}
        config={{ responsive: true, displayModeBar: true, modeBarButtonsToAdd: ['toImage'] }}
        style={{ width: '100%', minHeight: 320 }}
      />
    </div>
  )
}

export default function ChartResult({ data }: Props) {
  return (
    <ResultErrorBoundary>
      <ChartInner data={data} />
    </ResultErrorBoundary>
  )
}
