import { useState } from 'react'
import type { SessionTurn } from '@/types'
import styles from './ClarificationCard.module.css'

interface Props {
  turn: SessionTurn
  sessionId: string
}

export default function ClarificationCard({ turn }: Props) {
  // Clarification Q&A is handled inline in ChatPage via the WebSocket
  // This component displays a clarification request that was saved in turn history
  const qa = turn.clarification_qa || []
  if (qa.length === 0) return null

  return (
    <div className={styles.card}>
      <p className={styles.label}>Clarification</p>
      {qa.map((item, i) => (
        <div key={i} className={styles.item}>
          <p className={styles.q}>{item.question}</p>
          <p className={styles.a}>{item.answer}</p>
        </div>
      ))}
    </div>
  )
}
