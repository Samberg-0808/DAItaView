import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import AdminLayout from './AdminLayout'
import GroupPermissionEditor from './GroupPermissionEditor'
import api from '@/api/client'
import type { Group, User } from '@/types'
import styles from './GroupManagementPage.module.css'

export default function GroupManagementPage() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', description: '' })
  const [membersGroupId, setMembersGroupId] = useState<string | null>(null)
  const [permGroupId, setPermGroupId] = useState<string | null>(null)

  const { data: groups = [], isLoading } = useQuery<Group[]>({
    queryKey: ['groups'],
    queryFn: () => api.get('/groups').then(r => r.data),
  })

  const { data: users = [] } = useQuery<User[]>({
    queryKey: ['users'],
    queryFn: () => api.get('/users').then(r => r.data),
  })

  const createMut = useMutation({
    mutationFn: () => api.post('/groups', form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['groups'] }); setShowForm(false); setForm({ name: '', description: '' }) },
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`/groups/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['groups'] }),
  })

  const addMemberMut = useMutation({
    mutationFn: ({ groupId, userId }: { groupId: string; userId: string }) =>
      api.post(`/groups/${groupId}/members`, { user_id: userId }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['groups'] }),
  })

  const removeMemberMut = useMutation({
    mutationFn: ({ groupId, userId }: { groupId: string; userId: string }) =>
      api.delete(`/groups/${groupId}/members/${userId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['groups'] }),
  })

  const membersGroup = groups.find(g => g.id === membersGroupId) ?? null
  const permGroup = groups.find(g => g.id === permGroupId) ?? null

  const userMap = Object.fromEntries(users.map(u => [u.id, u]))

  function getUserName(userId: string) {
    return userMap[userId]?.username ?? userId.slice(0, 8)
  }

  const nonMembers = (group: Group) =>
    users.filter(u => u.is_active && !group.members.some(m => m.user_id === u.id))

  return (
    <AdminLayout>
      <div className={styles.content}>
        <div className={styles.header}>
          <h1 className={styles.title}>Group Management</h1>
          <button className={styles.newBtn} onClick={() => setShowForm(v => !v)}>+ New Group</button>
        </div>

        {showForm && (
          <div className={styles.form}>
            <input className={styles.input} placeholder="Group name" value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} />
            <input className={styles.input} placeholder="Description (optional)" value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))} />
            <button className={styles.saveBtn} onClick={() => createMut.mutate()} disabled={createMut.isPending || !form.name.trim()}>
              {createMut.isPending ? 'Creating…' : 'Create'}
            </button>
          </div>
        )}

        {isLoading ? <p className={styles.empty}>Loading…</p> : (
          <table className={styles.table}>
            <thead>
              <tr><th>Name</th><th>Description</th><th>Members</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {groups.map(g => (
                <tr key={g.id}>
                  <td>{g.name}</td>
                  <td className={styles.desc}>{g.description || '—'}</td>
                  <td><span className={styles.badge}>{g.member_count}</span></td>
                  <td className={styles.actions}>
                    <button className={styles.actionBtn} onClick={() => setMembersGroupId(g.id)}>Members</button>
                    <button className={styles.actionBtn} onClick={() => setPermGroupId(g.id)}>Permissions</button>
                    <button className={styles.deleteBtn} onClick={() => { if (confirm(`Delete group "${g.name}"?`)) deleteMut.mutate(g.id) }}>Delete</button>
                  </td>
                </tr>
              ))}
              {groups.length === 0 && (
                <tr><td colSpan={4} className={styles.empty}>No groups yet</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {membersGroup && (
        <MemberModal
          group={membersGroup}
          nonMembers={nonMembers(membersGroup)}
          getUserName={getUserName}
          onAdd={(userId) => addMemberMut.mutate({ groupId: membersGroup.id, userId })}
          onRemove={(userId) => removeMemberMut.mutate({ groupId: membersGroup.id, userId })}
          addPending={addMemberMut.isPending}
          onClose={() => setMembersGroupId(null)}
        />
      )}

      {permGroup && (
        <GroupPermissionEditor group={permGroup} onClose={() => setPermGroupId(null)} />
      )}
    </AdminLayout>
  )
}

function MemberModal({
  group, nonMembers, getUserName, onAdd, onRemove, addPending, onClose,
}: {
  group: Group
  nonMembers: User[]
  getUserName: (id: string) => string
  onAdd: (userId: string) => void
  onRemove: (userId: string) => void
  addPending: boolean
  onClose: () => void
}) {
  const [selectedUser, setSelectedUser] = useState('')

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        <h2 className={styles.modalTitle}>Members — {group.name}</h2>
        <div className={styles.modalBody}>
          <span className={styles.sectionLabel}>Add member</span>
          <div className={styles.addRow}>
            <select className={styles.addSelect} value={selectedUser} onChange={e => setSelectedUser(e.target.value)}>
              <option value="">Select a user…</option>
              {nonMembers.map(u => <option key={u.id} value={u.id}>{u.username} ({u.email})</option>)}
            </select>
            <button
              className={styles.addBtn}
              disabled={!selectedUser || addPending}
              onClick={() => { onAdd(selectedUser); setSelectedUser('') }}
            >
              Add
            </button>
          </div>

          <span className={styles.sectionLabel}>Current members ({group.member_count})</span>
          {group.members.map(m => (
            <div key={m.user_id} className={styles.memberRow}>
              <span className={styles.memberName}>{getUserName(m.user_id)}</span>
              <button className={styles.removeBtn} onClick={() => onRemove(m.user_id)}>Remove</button>
            </div>
          ))}
          {group.members.length === 0 && <p className={styles.empty}>No members yet</p>}
        </div>
        <div className={styles.modalFooter}>
          <button className={styles.cancelBtn} onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  )
}
