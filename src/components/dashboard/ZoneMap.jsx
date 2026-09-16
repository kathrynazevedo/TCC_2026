import React from "react";
import { Badge } from "@/components/ui/badge";
import { Map, AlertTriangle, CheckCircle } from "lucide-react";

export default function ZoneMap({ violations = [] }) {
  const activeByZone = violations.reduce((acc, v) => {
    if (v.status === 'active') {
      acc[v.zone] = (acc[v.zone] || 0) + 1;
    }
    return acc;
  }, {});

  const zones = [
    { name: "Zona Norte", desc: "Fundações e Escavação", status: activeByZone["Norte"] > 0 ? "danger" : "safe" },
    { name: "Canteiro Central", desc: "Área de Vivência e Refeitório", status: activeByZone["Central"] > 0 ? "danger" : "safe" },
    { name: "Almoxarifado", desc: "Estoque de EPIs e Ferramentas", status: activeByZone["Almoxarifado"] > 0 ? "danger" : "safe" },
    { name: "Acesso Principal", desc: "Catracas e Portaria", status: "safe" },
  ];

  return (
    <div className="h-full flex flex-col bg-white">
      <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
        <div>
          <h3 className="font-bold text-slate-800 flex items-center gap-2">
            <Map className="w-5 h-5 text-blue-600" />
            Mapa de Calor Operacional
          </h3>
          <p className="text-xs text-slate-500 mt-1">Monitoramento de risco segmentado por setor</p>
        </div>
      </div>
      <div className="p-4 flex-1">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 h-full">
          {zones.map((zone, idx) => (
            <div 
              key={idx} 
              className={`relative rounded-xl border p-4 transition-all duration-300 flex flex-col justify-between
                ${zone.status === 'danger' 
                  ? 'border-red-200 bg-red-50/50 shadow-[inset_0_0_20px_rgba(239,68,68,0.1)]' 
                  : 'border-slate-200 bg-slate-50 hover:bg-slate-100'}`}
            >
              <div>
                <div className="flex justify-between items-start mb-2">
                  <h4 className="font-bold text-slate-800">{zone.name}</h4>
                  {zone.status === 'danger' ? (
                    <AlertTriangle className="w-5 h-5 text-red-500 animate-pulse" />
                  ) : (
                    <CheckCircle className="w-5 h-5 text-green-500" />
                  )}
                </div>
                <p className="text-xs text-slate-500">{zone.desc}</p>
              </div>
              
              <div className="mt-4">
                <Badge 
                  variant={zone.status === 'danger' ? 'destructive' : 'outline'}
                  className={zone.status === 'safe' ? 'bg-green-100 text-green-700 border-none shadow-sm' : 'shadow-sm'}
                >
                  {zone.status === 'danger' ? `${activeByZone[zone.name]} Alertas Ativos` : 'Área Segura'}
                </Badge>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}