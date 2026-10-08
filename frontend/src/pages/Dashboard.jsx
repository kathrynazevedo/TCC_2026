import React from "react";
import { useViolations, useMetrics } from "@/api/queries";
import StatsOverview from "../components/dashboard/StatsOverview";
import ViolationChart from "../components/dashboard/ViolationChart";
import AlertFeed from "../components/dashboard/AlertFeed";
import RecentViolations from "../components/dashboard/RecentViolations";
import ApiErrorNotice from "@/components/common/ApiErrorNotice";

export default function Dashboard() {
  // Atualiza sozinho a cada poucos segundos: assim que a Raspberry Pi envia a foto, ela aparece aqui.
  const { data: violations = [], error: violationsError } = useViolations();
  const { data: metrics, error: metricsError } = useMetrics();

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Painel de Segurança</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">Monitoramento automatizado de EPIs via Visão Computacional</p>
      </div>

      <ApiErrorNotice error={violationsError || metricsError} />

      <StatsOverview metrics={metrics} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6 flex flex-col">
          <div className="flex-1">
            <RecentViolations violations={violations} />
          </div>
          <ViolationChart violations={violations} />
        </div>

        <div className="lg:col-span-1">
          <AlertFeed violations={violations} total={metrics?.total_eventos} />
        </div>
      </div>
    </div>
  );
}
