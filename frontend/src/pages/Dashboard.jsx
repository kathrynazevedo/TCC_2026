import React from "react";
import { LayoutDashboard } from "lucide-react";
import { useViolations, useMetrics } from "@/api/queries";
import StatsOverview from "../components/dashboard/StatsOverview";
import ViolationChart from "../components/dashboard/ViolationChart";
import AlertFeed from "../components/dashboard/AlertFeed";
import RecentViolations from "../components/dashboard/RecentViolations";
import ApiErrorNotice from "@/components/common/ApiErrorNotice";
import PageHeader from "@/components/common/PageHeader";

export default function Dashboard() {
  // Atualiza sozinho a cada poucos segundos: assim que a Raspberry Pi envia a foto, ela aparece aqui.
  const { data: violations = [], error: violationsError } = useViolations();
  const { data: metrics, error: metricsError } = useMetrics();

  return (
    <div className="animate-in fade-in space-y-8 duration-500">
      <PageHeader
        code="01"
        icon={LayoutDashboard}
        title="Painel de Segurança"
        description="Monitoramento automatizado de EPIs via Visão Computacional, atualizado em tempo real."
      >
        <span className="flex items-center gap-2 border border-border bg-card px-3 py-2 font-mono text-[11px] font-semibold uppercase tracking-wider text-foreground">
          <span className="led led-pulse text-destructive" /> Ao vivo · 5s
        </span>
      </PageHeader>

      <ApiErrorNotice error={violationsError || metricsError} />

      <StatsOverview metrics={metrics} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="flex flex-col space-y-6 lg:col-span-2">
          <RecentViolations violations={violations} />
          <ViolationChart violations={violations} />
        </div>

        <div className="lg:col-span-1">
          <AlertFeed violations={violations} total={metrics?.total_eventos} />
        </div>
      </div>
    </div>
  );
}
