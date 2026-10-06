import React from "react";
import { Link, useLocation } from "react-router-dom";
import { LayoutDashboard, AlertCircle, Map, Users, Settings, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

const menuItems = [
  { icon: LayoutDashboard, label: "Dashboard", path: "/" },
  { icon: AlertCircle, label: "Violações", path: "/violations" },
  { icon: Map, label: "Zonas", path: "/zones" },
  { icon: Users, label: "Equipe", path: "/workers" },
  { icon: Settings, label: "Sistema", path: "/system" },
];

export default function Sidebar() {
  const location = useLocation();

  return (
    <div className="flex flex-col h-full bg-slate-900 text-white">
      {/* Logo Area */}
      <div className="flex items-center gap-3 px-6 h-16 border-b border-slate-800">
        <ShieldCheck className="w-8 h-8 text-blue-500" />
        <span className="text-lg font-bold tracking-wider">SafeWork</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-6 space-y-1">
        {menuItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                "flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200",
                isActive 
                  ? "bg-blue-600 text-white shadow-lg shadow-blue-900/20" 
                  : "text-slate-400 hover:bg-slate-800 hover:text-white"
              )}
            >
              <item.icon className={cn("w-5 h-5", isActive ? "text-white" : "text-slate-400")} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer info */}
      <div className="p-6 border-t border-slate-800 text-[10px] text-slate-500 uppercase tracking-widest font-semibold">
        TCC Computer Science 2026
      </div>
    </div>
  );
}