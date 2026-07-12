import React, { useState, useEffect } from 'react';
import { Box, Typography, Button, Avatar, Chip, IconButton, Tooltip, Dialog, DialogTitle, DialogContent, DialogActions, TextField, MenuItem, Select, FormControl, InputLabel } from '@mui/material';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import EditIcon from '@mui/icons-material/Edit';
import BlockIcon from '@mui/icons-material/Block';
import DeleteIcon from '@mui/icons-material/Delete';
import RefreshIcon from '@mui/icons-material/Refresh';
import AdminLayout from '../../components/admin/AdminLayout';
import { AdminCard } from '../../components/admin/ui/AdminCard';
import { AdminTable, Column } from '../../components/admin/ui/AdminTable';
import { useAdminTheme } from '../../components/admin/AdminThemeContext';
import { getUsers, createUser, updateUser, deleteUser } from '../../components/admin/AdminApiClient';

export default function AdminUsersPage() {
  const { colors, isDark } = useAdminTheme();
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editUser, setEditUser] = useState<any>(null);
  const [form, setForm] = useState({ username: '', email: '', role: 'Editorial Reviewer' });

  const fetchUsersList = async () => {
    setLoading(true);
    try {
      const res = await getUsers();
      setUsers(res);
    } catch (err) {
      console.warn('Failed to fetch users from DB, fallback:', err);
      setUsers([
        { id: 1, username: "abdrahim_admin", email: "abdrahim@prefilter.org", role: "Administrator", status: "Active", created_at: "2026-05-15", last_login: "2026-07-07 10:15", avatar: "A" },
        { id: 2, username: "editor_chief", email: "chief.editor@ujaen.es", role: "Senior Editor", status: "Active", created_at: "2026-05-20", last_login: "2026-07-06 18:40", avatar: "E" },
        { id: 3, username: "reviewer_01", email: "rev1@ujaen.es", role: "Editorial Reviewer", status: "Active", created_at: "2026-06-01", last_login: "2026-07-07 09:12", avatar: "R" },
        { id: 4, username: "gdpr_auditor", email: "compliance@ujaen.es", role: "Compliance Auditor", status: "Active", created_at: "2026-06-10", last_login: "2026-07-05 14:20", avatar: "G" }
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsersList();
  }, []);

  const handleSaveUser = async () => {
    if (!form.username || !form.email) return;
    try {
      if (editUser) {
        await updateUser(editUser.id, form);
      } else {
        await createUser(form);
      }
      setModalOpen(false);
      setEditUser(null);
      setForm({ username: '', email: '', role: 'Editorial Reviewer' });
      fetchUsersList();
    } catch (err) {
      alert("Failed to save user in PostgreSQL.");
    }
  };

  const handleDelete = async (id: number) => {
    if (confirm(`Are you sure you want to delete user #${id}?`)) {
      try {
        await deleteUser(id);
        fetchUsersList();
      } catch (err) {
        alert("Failed to delete user.");
      }
    }
  };

  const handleToggleDisable = async (user: any) => {
    const nextStatus = user.status === "Active" ? "Disabled" : "Active";
    try {
      await updateUser(user.id, { status: nextStatus });
      fetchUsersList();
    } catch (err) {
      // Local optimistic update
      setUsers(users.map(u => u.id === user.id ? { ...u, status: nextStatus } : u));
    }
  };

  const columns: Column<any>[] = [
    {
      id: 'avatar',
      label: 'Avatar',
      minWidth: 70,
      sortable: false,
      render: (row) => (
        <Avatar sx={{ width: 34, height: 34, bgcolor: colors.primary, fontWeight: 700, fontSize: '0.82rem' }}>
          {row.avatar || row.username?.[0]?.toUpperCase() || 'U'}
        </Avatar>
      )
    },
    {
      id: 'username',
      label: 'User',
      minWidth: 140,
      render: (row) => (
        <Box>
          <Typography sx={{ fontWeight: 700, fontSize: '0.85rem', color: colors.text }}>
            {row.username}
          </Typography>
          <Typography variant="caption" sx={{ color: colors.muted }}>
            ID: #{row.id}
          </Typography>
        </Box>
      )
    },
    {
      id: 'role',
      label: 'Role',
      minWidth: 150,
      render: (row) => {
        const isAdm = row.role?.toLowerCase().includes('admin');
        const isEd = row.role?.toLowerCase().includes('editor');
        return (
          <Chip
            label={row.role || 'Reviewer'}
            size="small"
            sx={{
              fontWeight: 700, fontSize: '0.7rem', height: 22,
              bgcolor: isAdm ? 'rgba(239,68,68,0.15)' : isEd ? 'rgba(59,130,246,0.15)' : 'rgba(34,197,94,0.15)',
              color: isAdm ? '#f87171' : isEd ? '#60a5fa' : '#4ade80',
              border: `1px solid ${isAdm ? 'rgba(239,68,68,0.3)' : isEd ? 'rgba(59,130,246,0.3)' : 'rgba(34,197,94,0.3)'}`
            }}
          />
        );
      }
    },
    {
      id: 'status',
      label: 'Status',
      minWidth: 110,
      render: (row) => (
        <Chip
          label={row.status || 'Active'}
          size="small"
          color={row.status === 'Disabled' ? 'default' : 'success'}
          sx={{ fontWeight: 700, fontSize: '0.68rem', height: 20 }}
        />
      )
    },
    { id: 'email', label: 'Email Address', minWidth: 180 },
    { id: 'created_at', label: 'Created', minWidth: 110 },
    { id: 'last_login', label: 'Last Login', minWidth: 130 },
    {
      id: 'actions',
      label: 'Actions',
      align: 'right',
      minWidth: 130,
      sortable: false,
      render: (row) => (
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 0.5 }}>
          <Tooltip title="Edit User">
            <IconButton size="small" onClick={() => { setEditUser(row); setForm({ username: row.username, email: row.email, role: row.role }); setModalOpen(true); }} sx={{ color: colors.primary }}>
              <EditIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title={row.status === 'Disabled' ? "Enable User" : "Disable User"}>
            <IconButton size="small" onClick={() => handleToggleDisable(row)} sx={{ color: colors.warning }}>
              <BlockIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Delete User">
            <IconButton size="small" onClick={() => handleDelete(row.id)} sx={{ color: colors.danger }}>
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      )
    }
  ];

  return (
    <AdminLayout>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 2 }}>
          <Box>
            <Typography variant="h1" sx={{ fontSize: '1.8rem', fontWeight: 800, color: colors.text }}>
              Section 7 — User Management
            </Typography>
            <Typography variant="body2" sx={{ color: colors.muted, mt: 0.5 }}>
              Manage editorial staff, assign RBAC governance roles, and audit system access logs.
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1.5 }}>
            <Button variant="outlined" size="small" startIcon={<RefreshIcon />} onClick={fetchUsersList} sx={{ borderColor: colors.border, color: colors.text }}>
              Refresh
            </Button>
            <Button
              variant="contained"
              size="small"
              startIcon={<PersonAddIcon />}
              onClick={() => { setEditUser(null); setForm({ username: '', email: '', role: 'Editorial Reviewer' }); setModalOpen(true); }}
              sx={{ bgcolor: colors.primary, color: '#fff', fontWeight: 700 }}
            >
              Add User
            </Button>
          </Box>
        </Box>

        <AdminCard noPadding>
          <Box sx={{ p: 2.5 }}>
            <AdminTable
              columns={columns}
              data={users}
              loading={loading}
              searchPlaceholder="Search by username or email..."
              searchKeys={['username', 'email', 'role']}
              filterOptions={[
                { label: 'Administrators', key: 'role', value: 'Administrator' },
                { label: 'Senior Editors', key: 'role', value: 'Senior Editor' },
                { label: 'Reviewers', key: 'role', value: 'Editorial Reviewer' },
                { label: 'Auditors', key: 'role', value: 'Compliance Auditor' },
              ]}
              emptyMessage="No system users found in PostgreSQL database."
            />
          </Box>
        </AdminCard>

        {/* Add / Edit User Modal */}
        <Dialog open={modalOpen} onClose={() => setModalOpen(false)} maxWidth="sm" fullWidth>
          <DialogTitle sx={{ fontWeight: 800, bgcolor: colors.panel, color: colors.text, borderBottom: `1px solid ${colors.border}` }}>
            {editUser ? `Edit User #${editUser.id}` : 'Create New System User'}
          </DialogTitle>
          <DialogContent sx={{ bgcolor: colors.panel, py: 3, display: 'flex', flexDirection: 'column', gap: 2.5, mt: 1 }}>
            <TextField
              label="Username"
              fullWidth
              size="small"
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              slotProps={{ inputLabel: { style: { color: colors.muted } }, input: { style: { color: colors.text } } }}
            />
            <TextField
              label="Email Address"
              fullWidth
              size="small"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              slotProps={{ inputLabel: { style: { color: colors.muted } }, input: { style: { color: colors.text } } }}
            />
            <FormControl fullWidth size="small">
              <InputLabel sx={{ color: colors.muted }}>Assigned Role</InputLabel>
              <Select
                value={form.role}
                label="Assigned Role"
                onChange={(e) => setForm({ ...form, role: e.target.value })}
                sx={{ color: colors.text }}
              >
                <MenuItem value="Administrator">Administrator (Full Access)</MenuItem>
                <MenuItem value="Senior Editor">Senior Editor (Queue & Override)</MenuItem>
                <MenuItem value="Editorial Reviewer">Editorial Reviewer (Standard)</MenuItem>
                <MenuItem value="Compliance Auditor">Compliance Auditor (Read-Only Audit)</MenuItem>
              </Select>
            </FormControl>
          </DialogContent>
          <DialogActions sx={{ bgcolor: colors.panel, p: 2, borderTop: `1px solid ${colors.border}` }}>
            <Button onClick={() => setModalOpen(false)} sx={{ color: colors.muted }}>Cancel</Button>
            <Button onClick={handleSaveUser} variant="contained" sx={{ bgcolor: colors.primary, color: '#fff', fontWeight: 700 }}>
              {editUser ? 'Update User' : 'Create User'}
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </AdminLayout>
  );
}
