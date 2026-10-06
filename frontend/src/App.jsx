import { Toaster } from "@/components/ui/toaster"
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClientInstance } from '@/lib/query-client'
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import PageNotFound from './lib/PageNotFound';
import { AuthProvider, useAuth } from '@/lib/AuthContext';
import AppLayout from './components/layout/AppLayout';
import Dashboard from './pages/Dashboard';
import Zones from './pages/Zones';
import Violations from './pages/Violations';
import Workers from './pages/Workers';
import System from './pages/System';
import Docs from './pages/Docs';

const AuthenticatedApp = () => {
  const { isLoading } = useAuth();

  // Mostra um spinner simples se o sistema estiver carregando localmente
  if (isLoading) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-slate-50">
        <div className="w-8 h-8 border-4 border-slate-200 border-t-blue-600 rounded-full animate-spin"></div>
      </div>
    );
  }

  // Renderiza as rotas do sistema independente
  return (
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
  );
};

function App() {
  return (
    <AuthProvider>
      <QueryClientProvider client={queryClientInstance}>
        {/* Aqui está a correção do aviso do console (future flags) */}
        <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <AuthenticatedApp />
        </Router>
        <Toaster />
      </QueryClientProvider>
    </AuthProvider>
  )
}

export default App;