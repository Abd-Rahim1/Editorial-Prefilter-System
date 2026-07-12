import React, { useState } from 'react';
import { 
  Box, Typography, TextField, Button, Stack, 
  IconButton, ThemeProvider, createTheme, CssBaseline, InputAdornment, Alert, Link 
} from '@mui/material';
import GoogleIcon from '@mui/icons-material/Google';
import GitHubIcon from '@mui/icons-material/GitHub';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';

const theme = createTheme({
  palette: { background: { default: '#f4f7f9' }, primary: { main: '#314fc6' } },
  typography: { fontFamily: '"Inter", "Roboto", sans-serif', button: { textTransform: 'none', fontWeight: 600 } }
});

export default function SlidingLoginPage() {
  const [isSignUp, setIsSignUp] = useState(false);
  
  // Form States
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // Visibility State
  const [showPassword, setShowPassword] = useState(false);

  const handleToggleVisibility = () => {
    setShowPassword((prev) => !prev);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    const endpoint = isSignUp ? '/api/auth/register' : '/api/auth/login';

    try {
      let response;

      if (isSignUp) {
        response = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: name.trim() || email.split('@')[0], email: email.trim(), password, role: 'editor' }),
        });
      } else {
        const form = new URLSearchParams();
        form.append('username', email.trim());
        form.append('password', password);

        response = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: form.toString(),
        });
      }

      const data = await response.json();

      if (response.ok) {
        if (isSignUp) {
          setSuccess('Editor account created successfully! Switching to login...');
          setIsSignUp(false);
        } else {
          setSuccess('Login successful! Redirecting...');

          const userData = data.user || {};
          const role = data.role || userData.role || 'editor';
          const token = data.access_token || data.token;

          if (token) {
            localStorage.setItem('token', token);
          }
          localStorage.setItem('user', JSON.stringify(userData));
          localStorage.setItem('userRole', role);
          document.cookie = `user_role=${role}; path=/; max-age=86400; SameSite=Lax`;

          setTimeout(() => {
            if (role === 'admin') {
              window.location.href = '/admin/thresholds';
            } else {
              window.location.href = '/editor/queue';
            }
          }, 1000);
        }
      } else {
        setError(data.detail || data.message || 'Authentication failed');
      }
    } catch (err) {
      setError('Failed to connect to backend server');
    }
  };

  const socialIconStyle = { border: '1px solid #e5e7eb', borderRadius: '12px', p: 1, color: '#4b5563', '&:hover': { bgcolor: '#f3f4f6' } };
  const rapidTransition = 'all 0.5s cubic-bezier(0.25, 1, 0.25, 1)';

  const textInputStyle = {
    '& .MuiOutlinedInput-root': {
      borderRadius: '12px',
      backgroundColor: '#eff4fc',
      '& fieldset': { borderColor: 'transparent' },
      '&:hover fieldset': { borderColor: 'transparent' },
      '&.Mui-focused fieldset': { borderColor: '#314fc6' },
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', p: 3, bgcolor: '#f4f7f9' }}>
        <Box sx={{ position: 'relative', width: 950, maxWidth: '100%', minHeight: 580, backgroundColor: '#fff', borderRadius: 6, boxShadow: '0 20px 40px rgba(0,0,0,0.06)', overflow: 'hidden', display: 'flex' }}>
          
          {/* SIGN IN FORM VIEW */}
          <Box sx={{ width: '50%', p: 6, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
            <Typography variant="h3" sx={{ fontWeight: 800, mb: 1 }}>Sign In</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>Workspace access for Admins & Editors</Typography>
            
            <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
              <IconButton sx={socialIconStyle}><GoogleIcon fontSize="small" /></IconButton>
              <IconButton sx={socialIconStyle}><GitHubIcon fontSize="small" /></IconButton>
            </Stack>
            
            <Typography variant="caption" color="text.secondary" sx={{ mb: 3 }}>use your credentials</Typography>
            
            <Stack spacing={2.5} sx={{ width: '100%', maxWidth: 340 }}>
              {!isSignUp && error && <Alert severity="error" sx={{ borderRadius: 3 }}>{error}</Alert>}
              {!isSignUp && success && <Alert severity="success" sx={{ borderRadius: 3 }}>{success}</Alert>}
              
              <TextField 
                fullWidth 
                placeholder="Email Address" 
                value={email} 
                onChange={(e) => setEmail(e.target.value)} 
                sx={textInputStyle}
              />
              
              <TextField 
                fullWidth 
                placeholder="Password" 
                type={showPassword ? 'text' : 'password'} 
                value={password} 
                onChange={(e) => setPassword(e.target.value)} 
                sx={textInputStyle}
                slotProps={{
                  input: {
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton onClick={handleToggleVisibility} edge="end">
                          {showPassword ? <VisibilityOff /> : <Visibility />}
                        </IconButton>
                      </InputAdornment>
                    )
                  }
                }}
              />
              
              <Typography variant="caption" sx={{ alignSelf: 'flex-start', cursor: 'pointer', fontWeight: 600, color: '#314fc6' }}>
                Forgot your password?
              </Typography>

              <Button variant="contained" size="large" onClick={handleSubmit} sx={{ py: 1.5, borderRadius: 3, bgcolor: '#314fc6', boxShadow: 'none' }}>
                Sign In
              </Button>
            </Stack>
          </Box>

          {/* SIGN UP FORM VIEW */}
          <Box sx={{ width: '50%', p: 6, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
            <Typography variant="h3" sx={{ fontWeight: 800, mb: 1 }}>Register</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>Create a new platform workspace account</Typography>
            
            <Stack spacing={2.5} sx={{ width: '100%', maxWidth: 340 }}>
              {isSignUp && error && <Alert severity="error" sx={{ borderRadius: 3 }}>{error}</Alert>}
              {isSignUp && success && <Alert severity="success" sx={{ borderRadius: 3 }}>{success}</Alert>}

              <TextField fullWidth placeholder="Username" value={name} onChange={(e) => setName(e.target.value)} sx={textInputStyle} />
              <TextField fullWidth placeholder="Email Address" value={email} onChange={(e) => setEmail(e.target.value)} sx={textInputStyle} />
              
              <TextField 
                fullWidth 
                placeholder="Password" 
                type={showPassword ? 'text' : 'password'} 
                value={password} 
                onChange={(e) => setPassword(e.target.value)} 
                sx={textInputStyle}
                slotProps={{
                  input: {
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton onClick={handleToggleVisibility} edge="end">
                          {showPassword ? <VisibilityOff /> : <Visibility />}
                        </IconButton>
                      </InputAdornment>
                    )
                  }
                }}
              />
              
              <Button variant="contained" size="large" onClick={handleSubmit} sx={{ mt: 2, py: 1.5, borderRadius: 3, bgcolor: '#314fc6', boxShadow: 'none' }}>
                Create Account
              </Button>
            </Stack>
          </Box>

          {/* SLIDING INTERACTION CONTAINER OVERLAY */}
          <Box sx={{ position: 'absolute', top: 0, left: 0, width: '50%', height: '100%', background: 'linear-gradient(135deg, #4c409d 0%, #6b43b6 100%)', color: 'white', transition: rapidTransition, transform: isSignUp ? 'translateX(0%)' : 'translateX(100%)', zIndex: 10, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', p: 5, borderRadius: isSignUp ? '0 100px 100px 0' : '100px 0 0 100px' }}>
            <Box sx={{ position: 'absolute', transition: rapidTransition, transform: isSignUp ? 'translateX(-30%)' : 'translateX(0)', opacity: isSignUp ? 0 : 1, pointerEvents: isSignUp ? 'none' : 'auto', textAlign: 'center' }}>
              <Typography variant="h3" sx={{ fontWeight: 800, mb: 2 }}>New Editor?</Typography>
              <Typography variant="body1" sx={{ mb: 4, px: 3, opacity: 0.8 }}>If you are an Editor looking for workspace access, click below to set up your profile.</Typography>
              <Button variant="outlined" size="large" onClick={() => { setIsSignUp(true); setError(''); setSuccess(''); }} sx={{ color: 'white', borderColor: 'white', borderRadius: 3, px: 5 }}>Register here</Button>
            </Box>
            <Box sx={{ position: 'absolute', transition: rapidTransition, transform: isSignUp ? 'translateX(0)' : 'translateX(30%)', opacity: isSignUp ? 1 : 0, pointerEvents: isSignUp ? 'auto' : 'none', textAlign: 'center' }}>
              <Typography variant="h3" sx={{ fontWeight: 800, mb: 2 }}>Welcome Back!</Typography>
              <Typography variant="body1" sx={{ mb: 4, px: 3, opacity: 0.8 }}>Admins logging in directly or pre-verified editors can switch straight back here.</Typography>
              <Button variant="outlined" size="large" onClick={() => { setIsSignUp(false); setError(''); setSuccess(''); }} sx={{ color: 'white', borderColor: 'white', borderRadius: 3, px: 5 }}>Sign In</Button>
            </Box>
          </Box>

        </Box>
      </Box>
    </ThemeProvider>
  );
}