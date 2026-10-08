import React, { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { isSameDay } from "date-fns";

const HELMET = "Risco Cabeça";
const VEST = "Risco Corpo";

export default function ViolationChart({ violations = [] }) {
  const chartData = useMemo(() => {
    // Dia inteiro (00h–23h): a placa também registra fora do horário comercial.
    const hours = Array.from({ length: 24 }, (_, hour) => ({
      time: `${String(hour).padStart(2, "0")}:00`,
      [HELMET]: 0,
      [VEST]: 0,
    }));

    const now = new Date();
    for (const v of violations) {
      const date = new Date(v.detected_at);
      if (Number.isNaN(date.getTime()) || !isSameDay(date, now)) continue;
      if (v.type === "no-helmet") hours[date.getHours()][HELMET] += 1;
      if (v.type === "no-vest") hours[date.getHours()][VEST] += 1;
    }
    return hours;
  }, [violations]);

  return (
    <Card className="shadow-md border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
      <CardHeader>
        <CardTitle className="text-lg font-bold text-slate-800 dark:text-slate-100">Gráfico de Densidade de Incidentes</CardTitle>
        <CardDescription>Ocorrências de hoje por hora — apoio ao planejamento do DDS (Diálogo Diário de Segurança)</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[300px] w-full mt-2">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="colorHelmet" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#94a3b8" strokeOpacity={0.25} />
              <XAxis dataKey="time" axisLine={false} tickLine={false} interval={2} tick={{ fill: "#64748b", fontSize: 12 }} />
              <YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: "#64748b", fontSize: 12 }} />
              <Tooltip contentStyle={{ backgroundColor: "#1e293b", border: "none", borderRadius: "8px", color: "#fff" }} itemStyle={{ color: "#fff" }} />
              <Legend verticalAlign="top" align="right" />
              <Area type="monotone" dataKey={HELMET} stroke="#ef4444" fillOpacity={1} fill="url(#colorHelmet)" strokeWidth={3} />
              <Area type="monotone" dataKey={VEST} stroke="#f97316" fillOpacity={0} strokeWidth={3} strokeDasharray="5 5" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
