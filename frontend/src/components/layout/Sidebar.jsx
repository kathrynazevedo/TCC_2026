import React from "react";
import { Link, useLocation } from "react-router-dom";
import { LayoutDashboard, AlertCircle, Map, Users, Settings, ShieldCheck, FileText, ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/AuthContext";
import { initials, shortName } from "@/lib/format";

const menuItems = [
  { icon: LayoutDashboard, label: "Dashboard", path: "/" },
  { icon: AlertCircle, label: "Violações", path: "/violations" },
  { icon: Map, label: "Zonas", path: "/zones" },
  { icon: Users, label: "Equipe", path: "/workers" },
  { icon: FileText, label: "Relatórios", path: "/docs" },
  { icon: Settings, label: "Sistema", path: "/system" },
];

export default function Sidebar({ isCollapsed, setIsCollapsed }) {
  const location = useLocation();
  const { user } = useAuth();

  return (
    <div className="flex flex-col h-full bg-[#0f172a] text-slate-300 shadow-2xl relative">
      
      {/* Botão Flutuante de Recolher/Expandir (Apenas no Desktop) */}
      {setIsCollapsed && (
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="absolute -right-3 top-8 bg-blue-600 rounded-full p-1 text-white shadow-md hover:bg-blue-700 transition-colors z-50 hidden lg:flex items-center justify-center border-2 border-slate-900"
        >
          {isCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      )}

      {/* Logo Area */}
      <div className={cn("flex items-center h-20 border-b border-slate-800/50 bg-slate-900/50 transition-all duration-300 overflow-hidden", isCollapsed ? "justify-center px-0" : "gap-3 px-6")}>
        <div className="bg-blue-600/20 p-2 rounded-xl shrink-0">
          <ShieldCheck className="w-7 h-7 text-blue-500" />
        </div>
        {!isCollapsed && <span className="text-xl font-bold tracking-wide text-white whitespace-nowrap animate-in fade-in duration-300">SafeWork</span>}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-6 space-y-2 overflow-y-auto overflow-x-hidden custom-scrollbar">
        {menuItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              title={isCollapsed ? item.label : undefined}
              className={cn(
                "flex items-center rounded-xl text-sm font-medium transition-all duration-300 group relative",
                isCollapsed ? "justify-center py-3 px-0 mx-1" : "gap-3 px-4 py-3",
                isActive 
                  ? "bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-md shadow-blue-900/20" 
                  : "text-slate-400 hover:bg-slate-800/80 hover:text-slate-100"
              )}
            >
              <item.icon 
                className={cn(
                  "shrink-0 transition-transform duration-300", 
                  isCollapsed ? "w-6 h-6" : "w-5 h-5",
                  isActive ? "text-white" : "text-slate-500 group-hover:text-blue-400 group-hover:scale-110"
                )} 
              />
              {!isCollapsed && <span className="whitespace-nowrap animate-in fade-in duration-300">{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Footer Info */}
      <div className={cn("border-t border-slate-800/50 bg-slate-900/20 transition-all duration-300 overflow-hidden", isCollapsed ? "p-3" : "p-6")}>
        <div className={cn("flex items-center", isCollapsed ? "justify-center" : "gap-3 mb-4")}>
          <div className="h-9 w-9 shrink-0 rounded-full bg-slate-700 flex items-center justify-center text-white text-xs font-bold border border-slate-600">
            {initials(user.name)}
          </div>
          {!isCollapsed && (
            <div className="animate-in fade-in duration-300 whitespace-nowrap">
              <p className="text-sm font-bold text-white">{shortName(user.name)}</p>
              <p className="text-[10px] text-green-400 font-medium flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
                Admin Online
              </p>
            </div>
          )}
        </div>
        {!isCollapsed && (
          <div className="text-[9px] text-slate-500 uppercase tracking-widest font-semibold text-center whitespace-nowrap animate-in fade-in duration-300">
            TCC CS 2026
          </div>
        )}
      </div>
    </div>
  );
}