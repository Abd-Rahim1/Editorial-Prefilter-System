import React from 'react';
import { Box, Typography, Stepper, Step, StepLabel } from '@mui/material';
import { COLORS } from '../../styles/theme';
import type { PipelineStep } from '../../types/dashboard';

const LAYERS = [
  'Layer 1: Parsing & Rules',
  'Layer 2: Qwen LLM Scoring',
  'Layer 3: ML Calibration',
  'Layer 4: Trace Generation'
];

interface PipelineTimelineProps {
  activeStep?: number;
  steps?: PipelineStep[]; // Keep for compatibility with existing usage in cockpit.tsx
}

export default function PipelineTimeline({ activeStep, steps }: PipelineTimelineProps) {
  // Derive activeStep from steps if not provided explicitly
  let currentStep = activeStep ?? 0;
  
  if (activeStep === undefined && steps) {
    const runningIndex = steps.findIndex(s => s.status === 'running');
    if (runningIndex !== -1) {
      currentStep = runningIndex;
    } else if (steps.every(s => s.status === 'done')) {
      currentStep = steps.length;
    } else if (steps.every(s => s.status === 'pending')) {
      currentStep = 0;
    }
  }

  return (
    <Box>
      <Typography variant="overline" sx={{ display: 'block', mb: 2, px: 0.5 }}>
        Pipeline Status
      </Typography>
      <Stepper 
        activeStep={currentStep} 
        orientation="vertical" 
        sx={{ 
          pl: 1,
          '& .MuiStepConnector-line': {
            borderColor: COLORS.border,
            minHeight: 24,
          },
          '& .MuiStepIcon-root': {
            color: COLORS.border,
            '&.Mui-active': { color: COLORS.warning },
            '&.Mui-completed': { color: COLORS.success },
          },
          '& .MuiStepLabel-label': {
            color: COLORS.muted,
            '&.Mui-active': { color: COLORS.text, fontWeight: 700 },
            '&.Mui-completed': { color: COLORS.text, fontWeight: 500 },
          }
        }}
      >
        {LAYERS.map((label, index) => (
          <Step key={label}>
            <StepLabel>
              <Typography sx={{ 
                fontSize: '0.75rem', 
                fontWeight: currentStep === index ? 700 : 500 
              }}>
                {label}
              </Typography>
            </StepLabel>
          </Step>
        ))}
      </Stepper>
    </Box>
  );
}