import React from 'react';
import type { AppProps } from 'next/app';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import '../styles/globals.css';
import { AdminThemeProvider } from '../components/admin/AdminThemeContext';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
});

export default function App({ Component, pageProps }: AppProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <AdminThemeProvider>
        <Component {...pageProps} />
      </AdminThemeProvider>
    </QueryClientProvider>
  );
}