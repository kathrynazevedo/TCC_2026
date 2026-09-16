import React from "react";
import { useQuery } from "@tanstack/react-query";
import { getViolations } from "@/api/apiClient";
import StatsOverview from "../components/dashboard/StatsOverview";
import ViolationChart from "../components/dashboard/ViolationChart";
import AlertFeed from "../components/dashboard/AlertFeed";
import ZoneMap from "../components/dashboard/ZoneMap";

export default function Dashboard() {
  const { data: violations = [] } = useQuery({
    queryKey: ["violations"],
    queryFn: getViolations,
    refetchInterval: 5000,
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Painel de Segurança</h1>
        <p className="text-sm text-slate-500">Monitoramento automatizado de EPIs e Zonas de Risco</p>
      </div>

      {/* Grid de Stats: 1 col no mobile, 2 no tablet, 4 no desktop */}
      <StatsOverview violations={violations} />

      {/* Grid Principal: 1 col no mobile, 3 no desktop (Gráficos ocupam 2/3) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
            <ZoneMap violations={violations} />
          </div>
          <ViolationChart violations={violations} />
        </div>
        
        <div className="lg:col-span-1">
          <AlertFeed violations={violations} />
        </div>
      </div>
    </div>
  );
}