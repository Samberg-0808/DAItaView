export type UserRole = 'super_admin' | 'data_admin' | 'user'

export interface User {
  id: string
  email: string
  username: string
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface DataSource {
  id: string
  name: string
  type: 'postgres' | 'mysql' | 'sqlite' | 'csv' | 'json' | 'parquet'
  created_at: string
}

export interface ChatSession {
  id: string
  source_id: string
  title: string
  is_pinned: boolean
  created_at: string
  last_active_at: string
}

export type TurnResultType = 'chart' | 'table' | 'clarification' | 'error' | 'empty'

export interface SessionTurn {
  id: string
  session_id: string
  sequence: number
  question: string
  clarification_qa: Array<{ question: string; answer: string }> | null
  thinking: string | null
  generated_code: string | null
  result_cache: any | null
  result_type: TurnResultType | null
  data_snapshot_at: string | null
  executed_at: string | null
}

export interface ClarificationQuestion {
  text: string
  options: string[]
}

export interface Group {
  id: string
  name: string
  description: string | null
  created_at: string | null
  member_count: number
  members: { user_id: string }[]
}
