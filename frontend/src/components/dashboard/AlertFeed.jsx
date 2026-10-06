import React from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, MapPin } from "lucide-react";
import moment from "moment";

export default function AlertFeed({ violations = [] }) {
  const sorted = [...violations].sort((a, b) => new Date(b.detected_at) - new Date(a.detected_at));

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col h-[600px]">
      <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/50 rounded-t-xl">
        <h2 className="font-bold text-slate-800 flex items-center gap-2">
          <AlertCircle className="text-red-500 w-5 h-5" />
          Log de Eventos Críticos
        </h2>
        <Badge variant="outline" className="bg-white">{violations.length} total</Badge>
      </div>
      <ScrollArea className="flex-1">
        <div className="divide-y divide-slate-100">
          {sorted.map((v) => (
            <div key={v.id} className={`p-4 transition-colors hover:bg-slate-50 ${v.status === 'active' ? 'border-l-4 border-l-red-500' : ''}`}>
              <div className="flex justify-between items-start">
                <span className="text-sm font-bold text-slate-700">
                  {v.type === 'no-helmet' ? '⚠️ FALTA DE CAPACETE' : '⚠️ FALTA DE COLETE'}
                </span>
                <span className="text-[10px] font-mono text-slate-400">
                  {moment(v.detected_at).format("HH:mm:ss")}
                </span>
              </div>
              <div className="flex items-center gap-2 mt-2">
                <MapPin size={12} className="text-slate-400" />
                <span className="text-xs text-slate-600 font-medium">{v.zone}</span>
                <Badge className="ml-auto text-[10px] h-5 bg-slate-100 text-slate-600 border-none">
                  {v.status === 'active' ? 'PENDENTE' : 'RESOLVIDO'}
                </Badge>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}