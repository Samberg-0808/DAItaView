import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import styles from './NavBar.module.css'

export default function NavBar() {
  const { user, logout, isAdmin } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <nav className={styles.nav}>
      <span className={styles.logo}>DAItaView</span>
      <div className={styles.right}>
        {isAdmin && <Link className={styles.adminLink} to={user?.role === 'super_admin' ? '/admin/users' : '/admin/sources'}>Admin</Link>}
        <span className={styles.username}>{user?.username}</span>
        <button className={styles.logout} onClick={handleLogout}>Sign out</button>
      </div>
    </nav>
  )
}
