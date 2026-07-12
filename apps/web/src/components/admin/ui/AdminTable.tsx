import React, { useState, useMemo } from 'react';
import {
  Box, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  TablePagination, TextField, InputAdornment, Skeleton, Typography,
  TableSortLabel, MenuItem, Select, FormControl, InputLabel
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import InboxIcon from '@mui/icons-material/Inbox';
import { useAdminTheme } from '../AdminThemeContext';

export interface Column<T> {
  id: keyof T | string;
  label: string;
  minWidth?: number;
  align?: 'right' | 'left' | 'center';
  sortable?: boolean;
  render?: (row: T) => React.ReactNode;
}

interface AdminTableProps<T> {
  columns: Column<T>[];
  data: T[];
  loading?: boolean;
  searchPlaceholder?: string;
  searchKeys?: (keyof T)[];
  filterOptions?: { label: string; key: keyof T; value: any }[];
  defaultRowsPerPage?: number;
  emptyMessage?: string;
}

export function AdminTable<T extends Record<string, any>>({
  columns, data, loading = false, searchPlaceholder = "Search records...",
  searchKeys = [], filterOptions = [], defaultRowsPerPage = 10,
  emptyMessage = "No records found in PostgreSQL database."
}: AdminTableProps<T>) {
  const { colors, isDark } = useAdminTheme();
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState<string>("ALL");
  const [orderBy, setOrderBy] = useState<string>(columns[0]?.id as string || "");
  const [order, setOrder] = useState<'asc' | 'desc'>('asc');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(defaultRowsPerPage);

  const handleSort = (property: string) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  const filteredData = useMemo(() => {
    let result = [...data];

    // Filter by Dropdown
    if (activeFilter !== "ALL" && filterOptions.length > 0) {
      const option = filterOptions.find(o => `${String(o.key)}:${String(o.value)}` === activeFilter);
      if (option) {
        result = result.filter(item => item[option.key] === option.value);
      }
    }

    // Search Query
    if (searchQuery.trim() !== "" && searchKeys.length > 0) {
      const query = searchQuery.toLowerCase();
      result = result.filter(item =>
        searchKeys.some(key => {
          const val = item[key];
          return val !== null && val !== undefined && String(val).toLowerCase().includes(query);
        })
      );
    }

    // Sort
    if (orderBy) {
      result.sort((a, b) => {
        const valA = a[orderBy];
        const valB = b[orderBy];
        if (valA === valB) return 0;
        if (valA === null || valA === undefined) return 1;
        if (valB === null || valB === undefined) return -1;
        if (typeof valA === 'number' && typeof valB === 'number') {
          return order === 'asc' ? valA - valB : valB - valA;
        }
        return order === 'asc'
          ? String(valA).localeCompare(String(valB))
          : String(valB).localeCompare(String(valA));
      });
    }

    return result;
  }, [data, searchQuery, activeFilter, orderBy, order, searchKeys, filterOptions]);

  const paginatedData = useMemo(() => {
    return filteredData.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);
  }, [filteredData, page, rowsPerPage]);

  return (
    <Box sx={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 2 }}>
      {/* Search & Filter Toolbar */}
      {(searchKeys.length > 0 || filterOptions.length > 0) && (
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
          {searchKeys.length > 0 && (
            <TextField
              size="small"
              placeholder={searchPlaceholder}
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setPage(0); }}
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon fontSize="small" sx={{ color: colors.muted }} />
                    </InputAdornment>
                  ),
                }
              }}
              sx={{
                width: { xs: '100%', sm: 320 },
                '& .MuiOutlinedInput-root': {
                  bgcolor: isDark ? 'rgba(0,0,0,0.2)' : '#f8fafc',
                  borderRadius: 1.5,
                  fontSize: '0.82rem',
                }
              }}
            />
          )}

          {filterOptions.length > 0 && (
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel sx={{ fontSize: '0.8rem', color: colors.muted }}>Filter</InputLabel>
              <Select
                value={activeFilter}
                label="Filter"
                onChange={(e) => { setActiveFilter(e.target.value); setPage(0); }}
                sx={{ fontSize: '0.82rem', borderRadius: 1.5 }}
              >
                <MenuItem value="ALL" sx={{ fontSize: '0.82rem' }}>All Records</MenuItem>
                {filterOptions.map((opt, i) => (
                  <MenuItem key={i} value={`${String(opt.key)}:${String(opt.value)}`} sx={{ fontSize: '0.82rem' }}>
                    {opt.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
        </Box>
      )}

      {/* Table Container */}
      <TableContainer sx={{ border: `1px solid ${colors.border}`, borderRadius: 2, overflowX: 'auto' }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              {columns.map((col) => (
                <TableCell
                  key={String(col.id)}
                  align={col.align || 'left'}
                  style={{ minWidth: col.minWidth }}
                  sx={{
                    bgcolor: isDark ? '#111827' : '#f1f5f9',
                    color: colors.muted,
                    fontWeight: 700,
                    fontSize: '0.7rem',
                    letterSpacing: '0.05em',
                    textTransform: 'uppercase',
                    py: 1.2
                  }}
                >
                  {col.sortable !== false ? (
                    <TableSortLabel
                      active={orderBy === col.id}
                      direction={orderBy === col.id ? order : 'asc'}
                      onClick={() => handleSort(String(col.id))}
                      sx={{ '&.Mui-active': { color: colors.text } }}
                    >
                      {col.label}
                    </TableSortLabel>
                  ) : (
                    col.label
                  )}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              Array.from(new Array(5)).map((_, idx) => (
                <TableRow key={idx}>
                  {columns.map((col, cIdx) => (
                    <TableCell key={cIdx} sx={{ py: 1.5 }}>
                      <Skeleton variant="text" width="80%" height={24} sx={{ bgcolor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }} />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : paginatedData.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length} align="center" sx={{ py: 6 }}>
                  <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
                    <InboxIcon sx={{ fontSize: 48, color: colors.muted, opacity: 0.6 }} />
                    <Typography sx={{ fontSize: '0.9rem', fontWeight: 600, color: colors.text }}>
                      {emptyMessage}
                    </Typography>
                    <Typography variant="caption" sx={{ color: colors.muted }}>
                      Try adjusting your search query or filters.
                    </Typography>
                  </Box>
                </TableCell>
              </TableRow>
            ) : (
              paginatedData.map((row, rIdx) => (
                <TableRow
                  key={rIdx}
                  hover
                  sx={{
                    transition: 'background-color 0.15s ease',
                    '&:hover': { bgcolor: colors.hover }
                  }}
                >
                  {columns.map((col) => (
                    <TableCell key={String(col.id)} align={col.align || 'left'} sx={{ py: 1.4, fontSize: '0.8rem', color: colors.text }}>
                      {col.render ? col.render(row) : (row[col.id as keyof T] !== null && row[col.id as keyof T] !== undefined ? String(row[col.id as keyof T]) : '—')}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Pagination */}
      <TablePagination
        rowsPerPageOptions={[5, 10, 25, 50]}
        component="div"
        count={filteredData.length}
        rowsPerPage={rowsPerPage}
        page={page}
        onPageChange={(_, newPage) => setPage(newPage)}
        onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0); }}
        sx={{
          color: colors.text,
          borderTop: `1px solid ${colors.border}`,
          '& .MuiTablePagination-selectLabel, & .MuiTablePagination-displayedRows': {
            fontSize: '0.78rem',
            color: colors.muted
          }
        }}
      />
    </Box>
  );
}
