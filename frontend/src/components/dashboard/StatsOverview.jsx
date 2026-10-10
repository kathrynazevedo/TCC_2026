import React from "react";
import { Activity, AlertOctagon, Cctv, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

const show = (value, format = (v) => v) => (value === undefined || value === null ? "—" : format(value));

const SEGMENTS = 20;

// `metrics` é o objeto de GET /api/metrics (calculado no banco); undefined enquanto carrega.
export default function StatsOverview({ metrics }) {
  const pending = metrics?.nao_conformidades;
  const rate = metrics?.taxa_seguranca;

  const kpis = [
    {
      label: "Eventos totais",
      value: show(metrics?.total_eventos),
      icon: Activity,
      bar: "bg-primary",
      chip: "bg-primary text-primary-foreground",
      note: "registrados no banco de dados",
    },
    {
      label: "Não conformidades",
      value: show(pending),
      icon: AlertOctagon,
      bar: "bg-destructive",
      chip: "bg-destructive text-destructive-foreground",
      note: pending > 0 ? "pendentes · ação necessária" : "nenhuma pendência",
      noteTone: pending > 0 ? "text-destructive" : "text-success",
    },
    {
      label: "Taxa de segurança",
      value: show(rate, (v) => `${v}%`),
      icon: ShieldCheck,
      bar: "bg-success",
      chip: "bg-success text-success-foreground",
      meter: rate === undefined || rate === null ? 0 : Math.round((rate / 100) * SEGMENTS),
    },
    {
      label: "Câmeras",
      value: show(metrics?.total_cameras, (v) => String(v).padStart(2, "0")),
      icon: Cctv,
      bar: "bg-info",
      chip: "bg-info text-info-foreground",
      note: "dispositivos de borda cadastrados",
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {kpis.map((kpi) => (
        <div className="panel relative overflow-hidden" key={kpi.label}>
          <span className={cn("absolute inset-x-0 top-0 h-1", kpi.bar)} aria-hidden />
          <div className="flex items-start justify-between gap-3 p-5 pt-6">
            <div className="min-w-0">
              <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">{kpi.label}</p>
              <p className="display mt-3 text-6xl tabular-nums text-foreground">{kpi.value}</p>
            </div>
            <div className={cn("chamfer-sm flex h-11 w-11 shrink-0 items-center justify-center", kpi.chip)}>
              <kpi.icon className="h-6 w-6" strokeWidth={2.25} />
            </div>
          </div>

          {kpi.meter !== undefined ? (
            <div className="flex gap-0.5 px-5 pb-5" aria-hidden>
              {Array.from({ length: SEGMENTS }, (_, index) => (
                <span key={index} className={cn("h-2 flex-1", index < kpi.meter ? "bg-success" : "bg-border")} />
              ))}
            </div>
          ) : (
            <p className={cn("px-5 pb-5 font-mono text-[11px] uppercase tracking-wider text-muted-foreground", kpi.noteTone)}>{kpi.note}</p>
          )}
        </div>
      ))}
    </div>
  );
}
