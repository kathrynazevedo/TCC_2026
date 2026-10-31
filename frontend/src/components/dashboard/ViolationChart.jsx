import React, { useMemo, useState } from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { differenceInCalendarDays, format, isSameDay, startOfDay, subDays } from "date-fns";
import { ptBR } from "date-fns/locale";
import { BarChart3 } from "lucide-react";
import { VIOLATIONS_LIMIT } from "@/api/apiClient";
import { lacksHelmet, lacksVest } from "@/lib/violationLabels";
import { cn } from "@/lib/utils";

const HELMET = "Risco Cabeça";
const VEST = "Risco Corpo";

// Cores fixas (o SVG do gráfico não herda as variáveis do tema); funcionam nos dois temas.
const RED = "#ff3b3b";
const ORANGE = "#ff9500";
const AXIS = "#8b93a1";

// Cada período: quantos pontos tem o eixo, de quanto em quanto se rotula e o texto do subtítulo.
const RANGES = {
  day: { label: "Dia", buckets: 24, tickInterval: 2, subtitle: "Ocorrências de hoje por hora" },
  week: { label: "Semana", buckets: 7, tickInterval: 0, subtitle: "Ocorrências dos últimos 7 dias" },
  month: { label: "Mês", buckets: 30, tickInterval: 3, subtitle: "Ocorrências dos últimos 30 dias" },
};

const WEEKDAYS = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"]; // abreviação fixa: cabe no eixo em qualquer tela

const emptyBucket = (time, title) => ({ time, title, [HELMET]: 0, [VEST]: 0 });

// Monta os pontos vazios do eixo: 24 horas (hoje) ou N dias terminando hoje.
function buildBuckets(range, now) {
  if (range === "day") {
    return Array.from({ length: 24 }, (_, hour) => {
      const time = `${String(hour).padStart(2, "0")}:00`;
      return emptyBucket(time, `Hoje, ${time}`);
    });
  }
  const { buckets } = RANGES[range];
  return Array.from({ length: buckets }, (_, index) => {
    const day = subDays(startOfDay(now), buckets - 1 - index);
    const time = range === "week" ? `${WEEKDAYS[day.getDay()]} ${format(day, "dd/MM")}` : format(day, "dd/MM");
    return emptyBucket(time, format(day, "EEEE, dd/MM/yyyy", { locale: ptBR }));
  });
}

// Em qual ponto do eixo cai a ocorrência (-1 = fora do período).
function bucketIndex(range, date, now) {
  if (range === "day") return isSameDay(date, now) ? date.getHours() : -1;
  const { buckets } = RANGES[range];
  const daysAgo = differenceInCalendarDays(now, date);
  return daysAgo >= 0 && daysAgo < buckets ? buckets - 1 - daysAgo : -1;
}

export function buildChartData(violations, range, now = new Date()) {
  const points = buildBuckets(range, now);
  for (const v of violations) {
    const date = new Date(v.detected_at);
    if (Number.isNaN(date.getTime())) continue;
    const index = bucketIndex(range, date, now);
    if (index < 0) continue;
    // "Sem capacete e colete" soma nas duas séries: a ocorrência traz os dois riscos.
    if (lacksHelmet(v.type)) points[index][HELMET] += 1;
    if (lacksVest(v.type)) points[index][VEST] += 1;
  }
  return points;
}

export default function ViolationChart({ violations = [] }) {
  const [range, setRange] = useState("day");

  const chartData = useMemo(() => buildChartData(violations, range), [violations, range]);
  const totals = useMemo(
    () => chartData.reduce((sum, point) => ({ helmet: sum.helmet + point[HELMET], vest: sum.vest + point[VEST] }), { helmet: 0, vest: 0 }),
    [chartData]
  );
  const config = RANGES[range];
  const truncated = range !== "day" && violations.length >= VIOLATIONS_LIMIT;

  return (
    <section className="panel overflow-hidden">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-3 border-b border-border bg-surface px-5 py-4">
        <BarChart3 className="h-5 w-5 text-signal-ink" />
        <div className="min-w-0">
          <h2 className="display text-xl text-foreground">Densidade de incidentes</h2>
          <p className="mt-1 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
            {config.subtitle} · apoio ao DDS
          </p>
        </div>

        <div role="group" aria-label="Período do gráfico" className="ml-auto flex border border-border">
          {Object.entries(RANGES).map(([key, { label }]) => (
            <button
              key={key}
              type="button"
              onClick={() => setRange(key)}
              aria-pressed={range === key}
              className={cn(
                "px-3.5 py-1.5 font-mono text-[11px] font-semibold uppercase tracking-wider transition-colors",
                range === key ? "bg-primary text-primary-foreground" : "bg-card text-muted-foreground hover:text-foreground"
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="p-5">
        <p className="mb-3 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
          No período: <span className="font-semibold text-foreground">{totals.helmet}</span> risco cabeça ·{" "}
          <span className="font-semibold text-foreground">{totals.vest}</span> risco corpo
          {truncated && ` · considera as ${VIOLATIONS_LIMIT} ocorrências mais recentes`}
        </p>
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 8, right: 24, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorHelmet" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={RED} stopOpacity={0.45} />
                  <stop offset="95%" stopColor={RED} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 4" vertical={false} stroke={AXIS} strokeOpacity={0.3} />
              <XAxis
                dataKey="time"
                axisLine={false}
                tickLine={false}
                interval={config.tickInterval}
                tick={{ fill: AXIS, fontSize: 11, fontFamily: "JetBrains Mono" }}
              />
              <YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: AXIS, fontSize: 11, fontFamily: "JetBrains Mono" }} />
              <Tooltip
                cursor={{ stroke: AXIS, strokeDasharray: "3 3" }}
                contentStyle={{ backgroundColor: "#0c0e12", border: "1px solid #2a2f38", borderRadius: 0, color: "#fff", fontFamily: "JetBrains Mono", fontSize: 12 }}
                itemStyle={{ color: "#fff" }}
                labelStyle={{ color: "#8b93a1" }}
                labelFormatter={(label, items) => items?.[0]?.payload?.title || label}
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
