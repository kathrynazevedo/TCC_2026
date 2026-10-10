import React from "react";
import { Link, useLocation } from "react-router-dom";
import { ChevronLeft, ChevronRight, HardHat } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/AuthContext";
import { initials, shortName } from "@/lib/format";
import { SCREENS } from "@/lib/screens";

export default function Sidebar({ isCollapsed, setIsCollapsed }) {
  const location = useLocation();
  const { user } = useAuth();

  return (
    <div className="relative flex h-full flex-col bg-sidebar text-sidebar-foreground">
      {/* Recolher/expandir (somente desktop) */}
      {setIsCollapsed && (
        <button
          type="button"
          onClick={() => setIsCollapsed(!isCollapsed)}
          aria-label={isCollapsed ? "Expandir menu" : "Recolher menu"}
          className="absolute -right-3 top-[22px] z-50 hidden h-6 w-6 items-center justify-center border border-sidebar-border bg-signal text-signal-foreground transition-transform hover:scale-110 lg:flex"
        >
          {isCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      )}

      {/* Marca */}
      <div className={cn("flex h-16 shrink-0 items-center overflow-hidden border-b border-sidebar-border", isCollapsed ? "justify-center" : "gap-3 px-5")}>
        <div className="chamfer-sm flex h-10 w-10 shrink-0 items-center justify-center bg-primary text-primary-foreground">
          <HardHat className="h-6 w-6" strokeWidth={2.25} />
        </div>
        {!isCollapsed && (
          <div className="min-w-0 whitespace-nowrap">
            <span className="display block text-[26px] text-white">SafeWork</span>
            <span className="mt-0.5 block font-mono text-[9px] uppercase tracking-[0.28em] text-sidebar-foreground/50">Central de segurança</span>
          </div>
        )}
      </div>
      <div className="hazard h-1.5 shrink-0" aria-hidden />

      {/* Navegação */}
      <nav className="flex-1 space-y-1 overflow-y-auto overflow-x-hidden py-5">
        {!isCollapsed && (
          <p className="px-5 pb-2 font-mono text-[10px] uppercase tracking-[0.25em] text-sidebar-foreground/40">// módulos</p>
        )}
        {SCREENS.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              title={isCollapsed ? item.label : undefined}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "group relative flex items-center border-l-[3px] text-sm font-medium transition-colors",
                isCollapsed ? "justify-center px-0 py-3.5" : "gap-3 px-5 py-3",
                isActive
                  ? "border-signal bg-signal/10 text-white"
                  : "border-transparent text-sidebar-foreground/65 hover:bg-white/5 hover:text-white"
              )}
            >
              {!isCollapsed && (
                <span className={cn("font-mono text-[11px] tabular-nums", isActive ? "text-signal" : "text-sidebar-foreground/35")}>
                  {item.code}
                </span>
              )}
              <item.icon
                className={cn("shrink-0", isCollapsed ? "h-6 w-6" : "h-[18px] w-[18px]", isActive ? "text-signal" : "text-sidebar-foreground/50 group-hover:text-white")}
                strokeWidth={2}
              />
              {!isCollapsed && <span className="whitespace-nowrap uppercase tracking-wide">{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Operador */}
      <div className={cn("shrink-0 overflow-hidden border-t border-sidebar-border", isCollapsed ? "p-3" : "p-5")}>
        <div className={cn("flex items-center", isCollapsed ? "justify-center" : "gap-3")}>
          <div className="flex h-10 w-10 shrink-0 items-center justify-center border border-sidebar-border bg-sidebar-accent font-mono text-xs font-bold text-white">
            {initials(user.name)}
          </div>
          {!isCollapsed && (
            <div className="min-w-0 whitespace-nowrap">
              <p className="truncate text-sm font-semibold text-white">{shortName(user.name)}</p>
              <p className="mt-0.5 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider text-success">
                <span className="led led-pulse !h-1.5 !w-1.5" /> Admin online
              </p>
            </div>
          )}
        </div>
        {!isCollapsed && (
          <p className="mt-4 border-t border-sidebar-border pt-3 font-mono text-[9px] uppercase tracking-[0.25em] text-sidebar-foreground/35">
            TCC CS · 2026
          </p>
        )}
      </div>
    </div>
  );
}
