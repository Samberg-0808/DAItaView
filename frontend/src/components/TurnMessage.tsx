import { useState } from 'react'
import type { SessionTurn } from '@/types'
import ChartResult from './ChartResult'
import TableResult from './TableResult'
import ClarificationCard from './ClarificationCard'
import StalenessBar from './StalenessBar'
import styles from './TurnMessage.module.css'

interface Props {
  turn: SessionTurn
  isFirst: boolean
  sessionId: string
  onRefreshed: (updated: SessionTurn) => void
  onReask: (question: string) => void
}

export default function TurnMessage({ turn, isFirst, sessionId, onRefreshed, onReask }: Props) {
  const [showThinking, setShowThinking] = useState(isFirst)
  const [showCode, setShowCode] = useState(isFirst)

  return (
    <div className={styles.turn}>
      {/* User question */}
      <div className={styles.question}>{turn.question}</div>

      {/* AI response */}
      <div className={styles.response}>
        {/* Thinking block */}
        {turn.thinking && (
          <div className={styles.thinkingWrap}>
            <button className={styles.toggle} onClick={() => setShowThinking(v => !v)}>
              {showThinking ? '▾' : '▸'} Thinking
            </button>
            {showThinking && <pre className={styles.thinking}>{turn.thinking}</pre>}
          </div>
        )}

        {/* Clarification */}
        {turn.result_type === 'clarification' && (
          <ClarificationCard turn={turn} sessionId={sessionId} />
        )}

        {/* Result */}
        {turn.result_cache && turn.result_type !== 'clarification' && (
          <div className={styles.resultWrap}>
            <StalenessBar
              snapshotAt={turn.data_snapshot_at}
              sessionId={sessionId}
              turnId={turn.id}
              onRefreshed={onRefreshed}
              onReask={() => onReask(turn.question)}
            />
            {turn.result_type === 'chart' && <ChartResult data={turn.result_cache} />}
            {turn.result_type === 'table' && <TableResult data={turn.result_cache} />}
            {turn.result_type === 'error' && (
              <p className={styles.error}>{turn.result_cache?.error || 'Execution failed'}</p>
            )}
          </div>
        )}

        {/* Generated code */}
        {turn.generated_code && (
          <div className={styles.codeWrap}>
            <button className={styles.toggle} onClick={() => setShowCode(v => !v)}>
              {showCode ? '▾' : '▸'} Generated code
            </button>
            {showCode && (
              <div className={styles.codeBlock}>
                <button className={styles.copy} onClick={() => navigator.clipboard.writeText(turn.generated_code!)}>
                  Copy
                </button>
                <pre className={styles.code}>{turn.generated_code}</pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
