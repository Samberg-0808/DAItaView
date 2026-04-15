import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import AdminLayout from './AdminLayout'
import api from '@/api/client'
import type { User, UserRole } from '@/types'
import styles from './UserManagementPage.module.css'

const ROLES: UserRole[] = ['super_admin', 'data_admin', 'user']
const ROLE_LABELS: Record<UserRole, string> = { super_admin: 'Super Admin', data_admin: 'Data Admin', user: 'User' }

export default function UserManagementPage() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ email: '', username: '', password: '', role: 'user' as UserRole })

  const { data: users = [], isLoading } = useQuery<User[]>({
    queryKey: ['users'],
    queryFn: () => api.get('/users').then(r => r.data),
  })

  const createMut = useMutation({
    mutationFn: () => api.post('/users', form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); setShowForm(false); setForm({ email: '', username: '', password: '', role: 'user' }) },
  })

  const patchMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => api.patch(`/users/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })

  const deactivateMut = useMutation({
    mutationFn: (id: string) => api.delete(`/users/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })

  return (
    <AdminLayout>
      <div className={styles.content}>
        <div className={styles.header}>
          <h1 className={styles.title}>User Management</h1>
          <button className={styles.newBtn} onClick={() => setShowForm(v => !v)}>+ New User</button>
        </div>

        {showForm && (
          <div className={styles.form}>
            <input className={styles.input} placeholder="Email" value={form.email} onChange={e => setForm(p => ({ ...p, email: e.target.value }))} />
            <input className={styles.input} placeholder="Username" value={form.username} onChange={e => setForm(p => ({ ...p, username: e.target.value }))} />
            <input className={styles.input} placeholder="Password" type="password" value={form.password} onChange={e => setForm(p => ({ ...p, password: e.target.value }))} />
            <select className={styles.select} value={form.role} onChange={e => setForm(p => ({ ...p, role: e.target.value as UserRole }))}>
              {ROLES.map(r => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
            </select>
            <button className={styles.saveBtn} onClick={() => createMut.mutate()} disabled={createMut.isPending}>
              {createMut.isPending ? 'Creating…' : 'Create'}
            </button>
          </div>
        )}

        {isLoading ? <p className={styles.empty}>Loading…</p> : (
          <table className={styles.table}>
            <thead>
              <tr><th>Username</th><th>Email</th><th>Role</th><th>Status</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id}>
                  <td>{u.username}</td>
                  <td>{u.email}</td>
                  <td>
                    <select
                      className={styles.roleSelect}
                      value={u.role}
                      onChange={e => patchMut.mutate({ id: u.id, data: { role: e.target.value } })}
                    >
                      {ROLES.map(r => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
                    </select>
                  </td>
                  <td><span className={u.is_active ? styles.active : styles.inactive}>{u.is_active ? 'Active' : 'Inactive'}</span></td>
                  <td className={styles.actions}>
                    {u.is_active && (
                      <button className={styles.deactivateBtn} onClick={() => { if (confirm(`Deactivate ${u.username}?`)) deactivateMut.mutate(u.id) }}>Deactivate</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </AdminLayout>
  )
}
