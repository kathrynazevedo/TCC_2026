import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { ShieldCheck, AlertOctagon, Cctv, BarChart3 } from "lucide-react";

export default function StatsOverview({ violations = [] }) {
  const total = violations.length;
  const actives = violations.filter(v => v.status === 'active').length;
  const complianceRate = total > 0 ? Math.round(((total - actives) / total) * 100) : 100;

  const kpis = [
    { label: "Eventos Totais", value: total, icon: BarChart3, color: "text-blue-600", bg: "bg-blue-50" },
    { label: "Não Conformidades", value: actives, icon: AlertOctagon, color: "text-red-600", bg: "bg-red-50" },
    { label: "Taxa de Segurança", value: `${complianceRate}%`, icon: ShieldCheck, color: "text-green-600", bg: "bg-green-50" },
    { label: "Quantidade de Câmeras", value: "02", icon: Cctv, color: "text-purple-600", bg: "bg-purple-50" },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {kpis.map((kpi, i) => (
        <Card key={i} className="border-none shadow-sm overflow-hidden">
          <CardContent className="p-0">
            <div className="flex items-center p-4">
              <div className={`p-3 rounded-xl ${kpi.bg} ${kpi.color} mr-4`}>
                <kpi.icon size={24} />
              </div>
              <div>
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">{kpi.label}</p>
                <h3 className="text-2xl font-bold text-slate-800">{kpi.value}</h3>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
