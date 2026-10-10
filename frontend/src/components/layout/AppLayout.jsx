import React, { Suspense, useState, useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import ErrorBoundary from "@/components/common/ErrorBoundary";
import { screenFor } from "@/lib/screens";

const THEME_KEY = "safework-theme";

export default function AppLayout() {
  // Em telas médias (notebook pequeno) o menu já abre recolhido, para a tabela caber sem rolagem.
  const [isCollapsed, setIsCollapsed] = useState(() => typeof window !== "undefined" && window.innerWidth < 1280);
  const { pathname } = useLocation();

  // Escuro por padrão (visual de sala de controle); a escolha da pessoa fica salva no navegador.
  const [isDarkMode, setIsDarkMode] = useState(() => {
    try {
      const stored = localStorage.getItem(THEME_KEY);
      return stored ? stored === "dark" : true;
    } catch {
      return true;
    }
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", isDarkMode);
    try {
      localStorage.setItem(THEME_KEY, isDarkMode ? "dark" : "light");
    } catch {
      // armazenamento indisponível (modo privado): o tema só não será lembrado
    }
  }, [isDarkMode]);

  return (
    // data-screen define a cor de sinal (--signal) que menu, topo e página compartilham.
    <div data-screen={screenFor(pathname).key} className="flex h-screen overflow-hidden bg-background text-foreground">
      <aside
        className={`z-50 hidden border-r border-sidebar-border transition-all duration-300 lg:fixed lg:inset-y-0 lg:flex lg:flex-col ${isCollapsed ? "w-20" : "w-72"}`}
      >
        <Sidebar isCollapsed={isCollapsed} setIsCollapsed={setIsCollapsed} />
      </aside>

      <div className={`flex w-full flex-1 flex-col overflow-hidden transition-all duration-300 ${isCollapsed ? "lg:pl-20" : "lg:pl-72"}`}>
        <TopBar isDarkMode={isDarkMode} setIsDarkMode={setIsDarkMode} />

        <main className="grid-bg relative flex-1 overflow-y-auto focus:outline-none">
          <div className="mx-auto max-w-[1600px] px-4 py-8 sm:px-6 lg:px-8">
            <ErrorBoundary>
              <Suspense
                fallback={
                  <div className="flex justify-center py-24">
                    <div className="h-8 w-8 animate-spin border-4 border-border border-t-signal" />
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
