import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from '@/context/AuthContext'
import ProtectedRoute from '@/components/ProtectedRoute'
import LoginPage from '@/pages/LoginPage'
import ChatPage from '@/pages/ChatPage'
import UserManagementPage from '@/admin/UserManagementPage'
import DataSourceAdminPage from '@/admin/DataSourceAdminPage'
import KnowledgeEditorPage from '@/admin/KnowledgeEditorPage'
import AuditLogPage from '@/admin/AuditLogPage'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/chat" element={<ProtectedRoute><ChatPage /></ProtectedRoute>} />
          <Route path="/chat/:sessionId" element={<ProtectedRoute><ChatPage /></ProtectedRoute>} />
          <Route path="/admin/users" element={<ProtectedRoute><UserManagementPage /></ProtectedRoute>} />
          <Route path="/admin/sources" element={<ProtectedRoute><DataSourceAdminPage /></ProtectedRoute>} />
          <Route path="/admin/knowledge/:sourceId" element={<ProtectedRoute><KnowledgeEditorPage /></ProtectedRoute>} />
          <Route path="/admin/audit" element={<ProtectedRoute><AuditLogPage /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/chat" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
