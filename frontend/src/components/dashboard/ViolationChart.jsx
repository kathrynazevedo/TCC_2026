import React, { useMemo } from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { isSameDay } from "date-fns";
import { BarChart3 } from "lucide-react";
import { lacksHelmet, lacksVest } from "@/lib/violationLabels";

const HELMET = "Risco Cabeça";
const VEST = "Risco Corpo";

// Cores fixas (o SVG do gráfico não herda as variáveis do tema); funcionam nos dois temas.
const RED = "#ff3b3b";
const ORANGE = "#ff9500";
const AXIS = "#8b93a1";

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
      // "Sem capacete e colete" soma nas duas séries: a ocorrência traz os dois riscos.
      if (lacksHelmet(v.type)) hours[date.getHours()][HELMET] += 1;
      if (lacksVest(v.type)) hours[date.getHours()][VEST] += 1;
    }
    return hours;
  }, [violations]);

  return (
    <section className="panel overflow-hidden">
      <div className="flex items-center gap-3 border-b border-border bg-surface px-5 py-4">
        <BarChart3 className="h-5 w-5 text-signal-ink" />
        <div>
          <h2 className="display text-xl text-foreground">Densidade de incidentes</h2>
          <p className="mt-1 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
            Ocorrências de hoje por hora · apoio ao DDS
          </p>
        </div>
      </div>
      <div className="p-5">
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorHelmet" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={RED} stopOpacity={0.45} />
                  <stop offset="95%" stopColor={RED} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 4" vertical={false} stroke={AXIS} strokeOpacity={0.3} />
              <XAxis dataKey="time" axisLine={false} tickLine={false} interval={2} tick={{ fill: AXIS, fontSize: 11, fontFamily: "JetBrains Mono" }} />
              <YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: AXIS, fontSize: 11, fontFamily: "JetBrains Mono" }} />
              <Tooltip
                cursor={{ stroke: AXIS, strokeDasharray: "3 3" }}
                contentStyle={{ backgroundColor: "#0c0e12", border: "1px solid #2a2f38", borderRadius: 0, color: "#fff", fontFamily: "JetBrains Mono", fontSize: 12 }}
                itemStyle={{ color: "#fff" }}
                labelStyle={{ color: "#8b93a1" }}
              />
              <Legend verticalAlign="top" align="right" iconType="square" wrapperStyle={{ fontFamily: "JetBrains Mono", fontSize: 11 }} />
              <Area type="monotone" dataKey={HELMET} stroke={RED} fillOpacity={1} fill="url(#colorHelmet)" strokeWidth={2.5} />
              <Area type="monotone" dataKey={VEST} stroke={ORANGE} fillOpacity={0} strokeWidth={2.5} strokeDasharray="6 4" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}
