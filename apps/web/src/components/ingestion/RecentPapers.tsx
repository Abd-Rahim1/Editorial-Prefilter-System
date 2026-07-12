import React from 'react';
import { useRouter } from 'next/router';
import { 
  Box, Typography, Paper, Table, TableBody, TableCell, 
  TableContainer, TableHead, TableRow, Chip, Button 
} from '@mui/material';
import VisibilityIcon from '@mui/icons-material/Visibility';
import { COLORS } from '../../styles/theme';
import type { RecentPaper } from '../../types/dashboard';

const STATUS_MAP: Record<string, { label: string; color: string; bg: string; }> = {
  passed:     { label: 'Passed',     color: COLORS.success, bg: 'rgba(34,197,94,0.12)'   },
  rejected:   { label: 'Rejected',   color: COLORS.danger,  bg: 'rgba(239,68,68,0.12)'   },
  escalated:  { label: 'Escalated',  color: COLORS.warning, bg: 'rgba(245,158,11,0.12)'  },
  in_review:  { label: 'In Review',  color: '#60a5fa',      bg: 'rgba(96,165,250,0.12)'  },
  pending:    { label: 'Pending',    color: COLORS.muted,   bg: 'rgba(148,163,184,0.12)' },
  processing: { label: 'Processing', color: COLORS.warning, bg: 'rgba(245,158,11,0.12)'  },
  review:     { label: 'Review',     color: '#60a5fa',      bg: 'rgba(96,165,250,0.12)'  },
  accepted:   { label: 'Accepted',   color: COLORS.success, bg: 'rgba(34,197,94,0.12)'   },
};

interface RecentPapersProps {
  papers: RecentPaper[];
  onSelectPaper?: (paperId: string) => void;
}

export default function RecentPapers({ papers, onSelectPaper }: RecentPapersProps) {
  const router = useRouter();

  const handleRowClick = (paperId: string) => {
    if (onSelectPaper) {
      onSelectPaper(paperId);
    }
    router.push(`/editor/evaluation/${paperId}`);
  };

  return (
    <Box>
      <Typography variant="overline" sx={{ display: 'block', mb: 1.5, px: 0.5, fontWeight: 700, color: COLORS.text }}>
        Recent Submissions Log
      </Typography>

      <TableContainer component={Paper} sx={{ bgcolor: 'transparent', boxShadow: 'none', border: `1px solid ${COLORS.border}`, borderRadius: 2 }}>
        <Table size="small">
          <TableHead>
            <TableRow sx={{ '& th': { bgcolor: 'rgba(255,255,255,0.02)', color: COLORS.muted, fontWeight: 600, fontSize: '0.65rem', borderBottom: `1px solid ${COLORS.border}` } }}>
              <TableCell>ID</TableCell>
              <TableCell>Title</TableCell>
              <TableCell align="center">Status</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {papers.map((paper) => {
              const badge = STATUS_MAP[paper.status as string] || { label: paper.status, color: COLORS.muted, bg: 'rgba(0,0,0,0.05)' };
              return (
                <TableRow 
                  key={paper.id} 
                  onClick={() => handleRowClick(paper.id)}
                  sx={{ 
                    cursor: 'pointer',
                    transition: 'background-color 0.15s ease',
                    '& td': { borderBottom: `1px solid ${COLORS.border}`, color: COLORS.text, py: 1 }, 
                    '&:last-child td': { borderBottom: 0 },
                    '&:hover': {
                      bgcolor: 'rgba(255, 255, 255, 0.03)'
                    }
                  }}
                >
                  <TableCell sx={{ fontWeight: 'bold', fontSize: '0.68rem', color: COLORS.primary }}>{paper.id}</TableCell>
                  <TableCell sx={{ fontSize: '0.68rem', maxWidth: '220px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{paper.title}</TableCell>
                  <TableCell align="center">
                    <Chip 
                      label={badge.label} 
                      size="small" 
                      sx={{ height: 18, fontSize: '0.58rem', fontWeight: 700, color: badge.color, bgcolor: badge.bg, borderRadius: 1 }} 
                    />
                  </TableCell>
                  <TableCell align="right">
                    <Button 
                      size="small" 
                      onClick={(e) => {
                        e.stopPropagation(); // Prevent duplicate TableRow click triggering
                        handleRowClick(paper.id);
                      }}
                      startIcon={<VisibilityIcon sx={{ fontSize: '10px !important' }} />}
                      sx={{ textTransform: 'none', fontSize: '0.6rem', py: 0.2, px: 1, color: COLORS.primary }}
                    >
                      Inspect
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}