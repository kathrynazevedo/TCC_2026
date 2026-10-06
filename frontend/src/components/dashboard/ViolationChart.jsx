import React, { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import moment from "moment";

export default function ViolationChart({ violations = [] }) {
  const chartData = useMemo(() => {
    const hoursCount = {};
    for(let i=8; i<=18; i++) {
        const h = `${i.toString().padStart(2, '0')}:00`;
        hoursCount[h] = { time: h, "Risco Cabeça": 0, "Risco Corpo": 0 };
    }

    violations.forEach(v => {
      const hour = moment(v.detected_at).format("HH:00");
      if (hoursCount[hour]) {
        if (v.type === 'no-helmet') hoursCount[hour]["Risco Cabeça"] += 1;
        if (v.type === 'no-vest') hoursCount[hour]["Risco Corpo"] += 1;
      }
    });
    return Object.values(hoursCount);
  }, [violations]);

  return (
    <Card className="shadow-md border-slate-200">
      <CardHeader>
        <CardTitle className="text-lg font-bold text-slate-800">Gráfico de Densidade de Incidentes</CardTitle>
        <CardDescription>Análise estatística para planejamento de DDS (Diálogo Diário de Segurança)</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[300px] w-full mt-2">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="colorHelmet" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{fill: '#64748b', fontSize: 12}} />
              <YAxis axisLine={false} tickLine={false} tick={{fill: '#64748b', fontSize: 12}} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff' }}
                itemStyle={{ color: '#fff' }}
              />
              <Legend verticalAlign="top" align="right" />
              <Area type="monotone" dataKey="Risco Cabeça" stroke="#ef4444" fillOpacity={1} fill="url(#colorHelmet)" strokeWidth={3} />
              <Area type="monotone" dataKey="Risco Corpo" stroke="#f97316" fillOpacity={0} strokeWidth={3} strokeDasharray="5 5" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}