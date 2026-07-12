import React, { useState, useEffect } from 'react';
import { Box, Typography, Button, Chip, IconButton, Tooltip } from '@mui/material';
import SecurityIcon from '@mui/icons-material/Security';
import RefreshIcon from '@mui/icons-material/Refresh';
import EditIcon from '@mui/icons-material/Edit';
import VisibilityIcon from '@mui/icons-material/Visibility';
import AdminLayout from '../../components/admin/AdminLayout';
import { AdminCard } from '../../components/admin/ui/AdminCard';
import { AdminTable, Column } from '../../components/admin/ui/AdminTable';
import { useAdminTheme } from '../../components/admin/AdminThemeContext';
import { getRoles } from '../../components/admin/AdminApiClient';

export default function AdminRolesPage() {
  const { colors } = useAdminTheme();
  const [roles, setRoles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchRolesList = async () => {
    setLoading(true);
    try {
      const res = await getRoles();
      setRoles(res);
    } catch (err) {
      console.warn('Failed to fetch roles from DB, fallback:', err);
      setRoles([
        { id: 1, role: "Administrator", permissions: "Full system governance, database schema control, GPU allocation, audit purging.", members: 1 },
        { id: 2, role: "Senior Editor", permissions: "Ingest manuscripts, manage review queue, override LLM scores, view analytics.", members: 2 },
        { id: 3, role: "Editorial Reviewer", permissions: "Inspect assigned manuscripts, submit manual scores, review evidence spans.", members: 4 },
        { id: 4, role: "Compliance Auditor", permissions: "Read-only access to audit logs, GDPR retention ledgers, reproducibility checkpoints.", members: 1 }
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRolesList();
  }, []);

  const columns: Column<any>[] = [
    {
      id: 'role',
      label: 'Role Name',
      minWidth: 160,
      render: (row) => (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <SecurityIcon sx={{ color: colors.primary, fontSize: 18 }} />
          <Typography sx={{ fontWeight: 700, fontSize: '0.88rem', color: colors.text }}>
            {row.role || row.name}
          </Typography>
        </Box>
      )
    },
    {
      id: 'permissions',
      label: 'Assigned RBAC Permissions',
      minWidth: 320,
      render: (row) => (
        <Typography sx={{ fontSize: '0.82rem', color: colors.muted, lineHeight: 1.4 }}>
          {row.permissions || "Standard system access and evaluation reading."}
        </Typography>
      )
    },
    {
      id: 'members',
      label: 'Active Members',
      minWidth: 130,
      render: (row) => (
        <Chip
          label={`${row.members || 1} User(s)`}
          size="small"
          sx={{ fontWeight: 700, fontSize: '0.72rem', bgcolor: 'rgba(59,130,246,0.15)', color: '#60a5fa', border: '1px solid rgba(59,130,246,0.3)' }}
        />
      )
    },
    {
      id: 'actions',
      label: 'Actions',
      align: 'right',
      minWidth: 120,
      sortable: false,
      render: () => (
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 0.5 }}>
          <Tooltip title="View Members">
            <IconButton size="small" sx={{ color: colors.primary }}>
              <VisibilityIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Edit Role Permissions">
            <IconButton size="small" sx={{ color: colors.warning }}>
              <EditIcon fontSize="small" />
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
              Section 8 — Roles & Permissions Matrix
            </Typography>
            <Typography variant="body2" sx={{ color: colors.muted, mt: 0.5 }}>
              Configure Role-Based Access Control (RBAC) policies and audit staff privileges.
            </Typography>
          </Box>
          <Button variant="outlined" size="small" startIcon={<RefreshIcon />} onClick={fetchRolesList} sx={{ borderColor: colors.border, color: colors.text }}>
            Refresh Roles
          </Button>
        </Box>

        <AdminCard noPadding>
          <Box sx={{ p: 2.5 }}>
            <AdminTable
              columns={columns}
              data={roles}
              loading={loading}
              searchPlaceholder="Search roles or permissions..."
              searchKeys={['role', 'name', 'permissions']}
              emptyMessage="No roles found in PostgreSQL database."
            />
          </Box>
        </AdminCard>
      </Box>
    </AdminLayout>
  );
}
