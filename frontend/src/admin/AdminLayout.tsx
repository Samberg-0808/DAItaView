import { type ReactNode } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import styles from './AdminLayout.module.css'

interface NavItem {
  to: string
  label: string
  adminOnly?: boolean  // super_admin only
}

const NAV_ITEMS: NavItem[] = [
  { to: '/admin/users',    label: 'Users',         adminOnly: true },
  { to: '/admin/groups',   label: 'Groups',        adminOnly: true },
  { to: '/admin/sources',  label: 'Data Sources' },
  { to: '/admin/knowledge', label: 'Knowledge' },
  { to: '/admin/audit',    label: 'Audit Log',     adminOnly: true },
]

export default function AdminLayout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const isSuperAdmin = user?.role === 'super_admin'

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  const visibleItems = NAV_ITEMS.filter(item => !item.adminOnly || isSuperAdmin)

  return (
    <div className={styles.shell}>
      {/* Top bar */}
      <header className={styles.topbar}>
        <div className={styles.topLeft}>
          <span className={styles.logo}>DAItaView</span>
          <span className={styles.section}>Admin</span>
        </div>
        <div className={styles.topRight}>
          <NavLink className={styles.chatLink} to="/chat">← Back to Chat</NavLink>
          <span className={styles.username}>{user?.username}</span>
          <button className={styles.logout} onClick={handleLogout}>Sign out</button>
        </div>
      </header>

      <div className={styles.body}>
        {/* Sidebar */}
        <aside className={styles.sidebar}>
          {visibleItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
            >
              {item.label}
            </NavLink>
          ))}
        </aside>

        {/* Page content */}
        <main className={styles.content}>
          {children}
        </main>
      </div>
    </div>
  )
}
