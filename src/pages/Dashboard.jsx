import React from "react";
import { useQuery } from "@tanstack/react-query";
import { getViolations } from "@/api/apiClient";
import StatsOverview from "../components/dashboard/StatsOverview";
import ViolationChart from "../components/dashboard/ViolationChart";
import AlertFeed from "../components/dashboard/AlertFeed";
import RecentViolations from "../components/dashboard/ZoneMap";

export default function Dashboard() {
  // A requisição a cada 5 segundos garante que a tela atualize em tempo real 
  // assim que o Raspberry Pi enviar a foto para a porta 3000
  const { data: violations = [] } = useQuery({
    queryKey: ["violations"],
    queryFn: getViolations,
    refetchInterval: 5000, 
  });

  return (
    <div className="space-y-6">
      {/* Cabeçalho */}
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Painel de Segurança</h1>
        <p className="text-sm text-slate-500">Monitoramento automatizado de EPIs via Visão Computacional</p>
      </div>

      {/* Grid de KPIs Superiores (Com as "02 Câmeras Monitoradas") */}
      <StatsOverview violations={violations} />

      {/* Grid Principal: Dividido em 2 colunas para as fotos e 1 coluna para os logs */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Coluna Esquerda (Ocupa 2/3 da tela no Desktop) */}
        <div className="lg:col-span-2 space-y-6 flex flex-col">
          
          {/* Feed de Imagens (Substituiu o antigo Mapa de Calor) */}
          <div className="flex-1">
            <RecentViolations violations={violations} />
          </div>
          
          {/* Gráfico de Evolução (Mantido abaixo das fotos para contexto histórico) */}
          <ViolationChart violations={violations} />
        </div>
        
        {/* Coluna Direita (Ocupa 1/3 da tela no Desktop) */}
        <div className="lg:col-span-1">
          {/* Log de Eventos Críticos em tempo real */}
          <AlertFeed violations={violations} />
        </div>
        
      </div>
    </div>
  );
}