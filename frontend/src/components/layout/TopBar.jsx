import React from "react";
import { Menu, ShieldCheck, Sun, Moon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import Sidebar from "./Sidebar";
import NotificationPanel from "./NotificationPanel";

export default function TopBar({ isDarkMode, setIsDarkMode }) {
  return (
    <header className="sticky top-0 z-40 flex h-20 shrink-0 items-center gap-x-4 border-b border-slate-200/60 dark:border-slate-800/60 bg-white/80 dark:bg-[#09090b]/80 backdrop-blur-md px-4 sm:px-6 lg:px-8 transition-colors duration-300">
      
      <div className="flex lg:hidden">
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800">
              <Menu className="h-6 w-6" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="p-0 w-72 border-none z-50">
            <div className="sr-only">
              <SheetTitle>Menu de Navegação</SheetTitle>
              <SheetDescription>Acesse as páginas do sistema SafeWork</SheetDescription>
            </div>
            {/* Ocultamos as props de collapse no mobile para a sidebar sempre abrir inteira */}
            <Sidebar />
          </SheetContent>
        </Sheet>
      </div>

      <div className="flex flex-1 items-center justify-between gap-x-4">
        {/* Mobile Logo */}
        <div className="flex items-center gap-2 lg:hidden">
          <div className="bg-blue-600/10 p-1.5 rounded-lg">
            <ShieldCheck className="h-6 w-6 text-blue-600" />
          </div>
          <span className="font-bold text-slate-900 dark:text-white text-lg">SafeWork</span>
        </div>

        {/* Desktop Breadcrumb / Title */}
        <div className="hidden lg:flex flex-col">
          <span className="text-[10px] font-bold text-blue-600 dark:text-blue-400 uppercase tracking-widest mb-0.5">Módulo de IA</span>
          <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">Painel de Controle Operacional</span>
        </div>

        <div className="flex items-center gap-x-2 sm:gap-x-4 ml-auto">
          
          {/* Toggle Dark Mode */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsDarkMode(!isDarkMode)}
            className="text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-all"
          >
            {isDarkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </Button>

          <NotificationPanel />
          
          <div className="h-8 w-[1px] bg-slate-200 dark:bg-slate-700 hidden sm:block mx-1" />
          
          <div className="flex items-center gap-3 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50 p-1.5 rounded-xl transition-colors">
             <div className="hidden sm:block text-right">
                <p className="text-sm font-bold text-slate-800 dark:text-slate-100 leading-none">Administrador</p>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">Gestão Completa</p>
             </div>
             <div className="h-9 w-9 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white text-xs font-bold shadow-md shadow-blue-500/20 border-2 border-white dark:border-slate-800 shrink-0">
                RA
             </div>
          </div>
        </div>
      </div>
    </header>
  );
}