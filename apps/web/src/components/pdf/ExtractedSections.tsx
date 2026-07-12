import React, { useState } from 'react';
import { Box, Typography, Chip, Collapse, IconButton } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import SubjectIcon    from '@mui/icons-material/Subject';
import { COLORS } from '../../styles/theme';

interface Section {
  id:    string;
  label: string;
  text:  string;
  tag:   'ok' | 'warn' | 'error';
}

const MOCK_SECTIONS: Section[] = [
  {
    id: 'sec-abstract', label: 'Abstract', tag: 'ok',
    text: 'We propose a novel cross-lingual attention mechanism for scientific abstract parsing. Our approach leverages transformer-based architectures to improve multilingual comprehension across 18 language families...',
  },
  {
    id: 'sec-intro', label: 'Introduction', tag: 'ok',
    text: 'Scientific literature processing at scale demands robust NLP pipelines capable of generalizing across domains and languages. Despite recent advances in pre-trained models...',
  },
  {
    id: 'sec-method', label: 'Methodology', tag: 'ok',
    text: 'Our architecture consists of a multilingual encoder (d_model=768, 12 heads) augmented with a cross-attention pooling module trained on the mC4 corpus subset...',
  },
  {
    id: 'sec-exp', label: 'Experiments', tag: 'warn',
    text: 'We evaluate on MultiNLI and XNLI datasets. Results show 3.2% improvement over baseline. Note: full ablation study deferred to extended version of this paper...',
  },
  {
    id: 'sec-ref', label: 'References', tag: 'ok',
    text: '[1] Vaswani, A. et al. (2017). Attention is All You Need. NeurIPS 2017.\n[2] Conneau, A. et al. (2020). Unsupervised Cross-Lingual Representation Learning...',
  },
];

const TAG_CFG = {
  ok:    { color: COLORS.success, label: 'Validated' },
  warn:  { color: COLORS.warning, label: 'Warning'   },
  error: { color: COLORS.danger,  label: 'Issue'     },
};

function SectionRow({ section }: { section: Section }) {
  const [open, setOpen] = useState(false);
  const cfg = TAG_CFG[section.tag];

  return (
    <Box sx={{
      border: `1px solid ${COLORS.border}`,
      borderRadius: 1.5, overflow: 'hidden',
      '&:hover': { borderColor: '#475569' }, transition: 'border-color 0.15s',
    }}>
      <Box
        onClick={() => setOpen(o => !o)}
        sx={{
          display: 'flex', alignItems: 'center', gap: 1,
          px: 1.2, py: 0.8, cursor: 'pointer',
          bgcolor: 'rgba(255,255,255,0.02)',
        }}
      >
        <SubjectIcon sx={{ fontSize: 13, color: COLORS.muted }} />
        <Typography sx={{ flex: 1, fontSize: '0.68rem', fontWeight: 600, color: COLORS.text }}>
          {section.label}
        </Typography>
        <Chip
          label={cfg.label}
          size="small"
          sx={{ height: 15, fontSize: '0.5rem', color: cfg.color, bgcolor: `${cfg.color}15`, border: 'none' }}
        />
        <IconButton size="small" sx={{ p: 0, color: COLORS.muted }}>
          {open ? <ExpandLessIcon sx={{ fontSize: 14 }} /> : <ExpandMoreIcon sx={{ fontSize: 14 }} />}
        </IconButton>
      </Box>
      <Collapse in={open}>
        <Box sx={{
          px: 1.5, py: 1, borderTop: `1px solid ${COLORS.border}`,
          bgcolor: section.tag === 'warn'  ? 'rgba(245,158,11,0.04)' :
                   section.tag === 'error' ? 'rgba(239,68,68,0.04)'  : 'transparent',
        }}>
          <Typography sx={{ fontSize: '0.65rem', color: COLORS.muted, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
            {section.text}
          </Typography>
        </Box>
      </Collapse>
    </Box>
  );
}

export default function ExtractedSections({ active }: { active: boolean }) {
  if (!active) return null;

  return (
    <Box>
      <Typography variant="overline" sx={{ display: 'block', mb: 1 }}>
        Extracted Sections
      </Typography>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.6 }}>
        {MOCK_SECTIONS.map(s => <SectionRow key={s.id} section={s} />)}
      </Box>
    </Box>
  );
}
