import { lazy } from 'react';
import { Toaster } from "@/components/ui/toaster"
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClientInstance } from '@/lib/query-client'
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import PageNotFound from './lib/PageNotFound';
import { AuthProvider } from '@/lib/AuthContext';
import AppLayout from './components/layout/AppLayout';

// Cada página vira um arquivo próprio, carregado só quando acessada (primeiro carregamento bem menor).
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Zones = lazy(() => import('./pages/Zones'));
const Violations = lazy(() => import('./pages/Violations'));
const Workers = lazy(() => import('./pages/Workers'));
const System = lazy(() => import('./pages/System'));
const Docs = lazy(() => import('./pages/Docs'));

function App() {
  return (
    <AuthProvider>
      <QueryClientProvider client={queryClientInstance}>
        <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/zones" element={<Zones />} />
              <Route path="/violations" element={<Violations />} />
              <Route path="/workers" element={<Workers />} />
              <Route path="/system" element={<System />} />
              <Route path="/docs" element={<Docs />} />
            </Route>
            <Route path="*" element={<PageNotFound />} />
          </Routes>
        </Router>
        <Toaster />
      </QueryClientProvider>
    </AuthProvider>
  )
}

export default App;
