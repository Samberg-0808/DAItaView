import { Component, type ReactNode } from 'react'
import styles from './ResultErrorBoundary.module.css'

interface Props { children: ReactNode }
interface State { caught: boolean; message: string }

export default class ResultErrorBoundary extends Component<Props, State> {
  state: State = { caught: false, message: '' }

  static getDerivedStateFromError(err: Error): State {
    return { caught: true, message: err.message }
  }

  render() {
    if (this.state.caught) {
      return (
        <div className={styles.card}>
          <p className={styles.title}>Unable to render result</p>
          <p className={styles.detail}>{this.state.message}</p>
        </div>
      )
    }
    return this.props.children
  }
}
