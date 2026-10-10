import { AlertOctagon, Cpu, FileText, LayoutDashboard, MapPinned, Users } from "lucide-react";

// Fonte única das telas: menu, topo e cor de sinal (data-screen) usam esta lista.
export const SCREENS = [
  { path: "/", key: "dashboard", code: "01", label: "Dashboard", icon: LayoutDashboard },
  { path: "/violations", key: "violations", code: "02", label: "Violações", icon: AlertOctagon },
  { path: "/zones", key: "zones", code: "03", label: "Zonas", icon: MapPinned },
  { path: "/workers", key: "workers", code: "04", label: "Equipe", icon: Users },
  { path: "/docs", key: "docs", code: "05", label: "Relatórios", icon: FileText },
  { path: "/system", key: "system", code: "06", label: "Sistema", icon: Cpu },
];

export const screenFor = (pathname) => SCREENS.find((screen) => screen.path === pathname) || SCREENS[0];
