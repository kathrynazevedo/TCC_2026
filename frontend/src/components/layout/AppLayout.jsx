import React, { Suspense, useState, useEffect } from "react";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import { Outlet } from "react-router-dom";
import ErrorBoundary from "@/components/common/ErrorBoundary";

export default function AppLayout() {
  // Estado para a Sidebar recolhível
  const [isCollapsed, setIsCollapsed] = useState(false);
  
  // Estado para o Dark Mode (Puxa do cache do navegador se existir)
  const [isDarkMode, setIsDarkMode] = useState(() => {
    try {
      return localStorage.getItem("theme") === "dark";
    } catch {
      return false;
    }
  });

  // Efeito que injeta a classe 'dark' no HTML quando o botão é ativado
  useEffect(() => {
    document.documentElement.classList.toggle("dark", isDarkMode);
    try {
      localStorage.setItem("theme", isDarkMode ? "dark" : "light");
    } catch {
      // armazenamento indisponível (modo privado): o tema só não será lembrado
    }
  }, [isDarkMode]);

  return (
    <div className="flex h-screen bg-slate-50 dark:bg-[#09090b] overflow-hidden transition-colors duration-300">
      
      {/* Sidebar Desktop com tamanho dinâmico (w-20 ou w-72) */}
      <aside 
        className={`hidden lg:flex lg:flex-col lg:fixed lg:inset-y-0 border-r border-slate-200 dark:border-slate-800 bg-[#0f172a] transition-all duration-300 z-50 ${isCollapsed ? 'w-20' : 'w-72'}`}
      >
        <Sidebar isCollapsed={isCollapsed} setIsCollapsed={setIsCollapsed} />
      </aside>

      {/* Área Principal (Ajusta o padding lateral dependendo da Sidebar) */}
      <div className={`flex flex-col flex-1 w-full overflow-hidden transition-all duration-300 ${isCollapsed ? 'lg:pl-20' : 'lg:pl-72'}`}>
        
        <TopBar 
          isDarkMode={isDarkMode} 
          setIsDarkMode={setIsDarkMode} 
        />
        
        <main className="flex-1 relative overflow-y-auto focus:outline-none dark:text-slate-200">
          <div className="py-6 px-4 sm:px-6 lg:px-8 max-w-[1600px] mx-auto">
            <ErrorBoundary>
              <Suspense
                fallback={
                  <div className="flex justify-center py-24">
                    <div className="w-8 h-8 border-4 border-slate-200 border-t-blue-600 rounded-full animate-spin" />
                  </div>
                }
              >
                <Outlet />
              </Suspense>
            </ErrorBoundary>
          </div>
        </main>
      </div>
    </div>
  );
}