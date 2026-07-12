import React from 'react';
import { Box, Typography, Button, Container, Grid, Card, CardContent } from '@mui/material';
import RuleIcon from '@mui/icons-material/Rule';
import ScienceIcon from '@mui/icons-material/Science';
import GavelIcon from '@mui/icons-material/Gavel';
import Link from 'next/link';

export default function LandingPage() {
  return (
    <Box 
      sx={{ 
        minHeight: '100vh', 
        bgcolor: '#f8fafc', // bg-slate-50
        color: '#0f172a',
        display: 'flex',
        flexDirection: 'column',
        fontFamily: '"Inter", "Roboto", sans-serif'
      }}
    >
      <Container maxWidth="lg" sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', py: 10 }}>
        
        {/* Hero Section */}
        <Box sx={{ textAlign: 'center', mb: 10, maxWidth: '800px', mx: 'auto' }}>
          <Typography 
            variant="h1" 
            component="h1" 
            sx={{ 
              fontWeight: 800, 
              fontSize: { xs: '2.5rem', md: '3.75rem' },
              color: '#0f172a', // slate-900
              mb: 3,
              letterSpacing: '-0.02em',
              lineHeight: 1.1
            }}
          >
            AI-Assisted Scientific Paper Pre-filtering
          </Typography>
          <Typography 
            variant="h6" 
            sx={{ 
              color: '#475569', // slate-600
              mb: 5,
              fontWeight: 400,
              fontSize: { xs: '1rem', md: '1.25rem' },
              lineHeight: 1.6
            }}
          >
            An advanced, human-in-the-loop editorial decision support system. Combine rule-based checks, Large Language Models (Qwen), and machine learning to streamline manuscript triage.
          </Typography>
          <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, flexWrap: 'wrap' }}>
            <Button 
              variant="outlined" 
              size="large"
              sx={{ 
                borderColor: '#cbd5e1', 
                color: '#334155', 
                bgcolor: 'transparent',
                fontWeight: 600,
                px: 4,
                py: 1.5,
                borderRadius: '8px',
                textTransform: 'none',
                '&:hover': {
                  borderColor: '#94a3b8',
                  bgcolor: 'rgba(241, 245, 249, 0.5)' // slate-100
                }
              }}
            >
              View Live Demo
            </Button>
            <Link href="/login" passHref legacyBehavior>
              <Button 
                variant="contained" 
                size="large"
                sx={{ 
                  bgcolor: '#2563eb', // blue-600
                  color: '#ffffff',
                  fontWeight: 600,
                  px: 4,
                  py: 1.5,
                  borderRadius: '8px',
                  textTransform: 'none',
                  boxShadow: '0 4px 6px -1px rgba(37, 99, 235, 0.2), 0 2px 4px -1px rgba(37, 99, 235, 0.1)',
                  '&:hover': {
                    bgcolor: '#1d4ed8', // blue-700
                    boxShadow: '0 10px 15px -3px rgba(37, 99, 235, 0.3), 0 4px 6px -2px rgba(37, 99, 235, 0.15)',
                    transform: 'translateY(-1px)'
                  },
                  transition: 'all 0.2s ease-in-out'
                }}
              >
                Editor Login
              </Button>
            </Link>
          </Box>
        </Box>

        {/* Feature Cards Section */}
        <Grid container spacing={4}>
          {/* Card 1 */}
          <Grid size={{ xs: 12, md: 4 }}>
            <FeatureCard 
              icon={<RuleIcon sx={{ fontSize: 32, color: '#3b82f6' }} />}
              title="Layer 1: Hard Rules"
              text="Instant structural validation (pages, word counts, missing sections)."
            />
          </Grid>
          {/* Card 2 */}
          <Grid size={{ xs: 12, md: 4 }}>
            <FeatureCard 
              icon={<ScienceIcon sx={{ fontSize: 32, color: '#8b5cf6' }} />}
              title="Layer 2: Qwen LLM Scoring"
              text="Holistic evaluation of methodology, clarity, and experimental strength."
            />
          </Grid>
          {/* Card 3 */}
          <Grid size={{ xs: 12, md: 4 }}>
            <FeatureCard 
              icon={<GavelIcon sx={{ fontSize: 32, color: '#10b981' }} />}
              title="Layer 3 & 4: Calibration & Trace"
              text="ML-driven probability scoring with controlled, transparent explanations."
            />
          </Grid>
        </Grid>
      </Container>
    </Box>
  );
}

function FeatureCard({ icon, title, text }: { icon: React.ReactNode, title: string, text: string }) {
  return (
    <Card 
      sx={{ 
        height: '100%',
        bgcolor: '#ffffff',
        borderRadius: '16px', // rounded-xl
        border: '1px solid #e2e8f0', // slate-200
        backgroundImage: 'none',
        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05), 0 2px 4px -2px rgb(0 0 0 / 0.05)',
        transition: 'all 0.3s ease',
        '&:hover': {
          transform: 'translateY(-6px)',
          boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
          borderColor: '#cbd5e1'
        }
      }}
    >
      <CardContent sx={{ p: { xs: 3, md: 4 } }}>
        <Box sx={{ 
          display: 'inline-flex',
          p: 1.5, 
          borderRadius: '12px', 
          bgcolor: '#f1f5f9', // slate-100
          mb: 3
        }}>
          {icon}
        </Box>
        <Typography 
          variant="h6" 
          component="h3" 
          sx={{ 
            fontWeight: 700, 
            color: '#0f172a', 
            mb: 1.5,
            fontSize: '1.125rem'
          }}
        >
          {title}
        </Typography>
        <Typography 
          variant="body1" 
          sx={{ 
            color: '#475569',
            lineHeight: 1.6
          }}
        >
          {text}
        </Typography>
      </CardContent>
    </Card>
  );
}
