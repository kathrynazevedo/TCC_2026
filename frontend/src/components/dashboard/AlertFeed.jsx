import React, { useMemo } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, MapPin } from "lucide-react";
import { formatDateTime } from "@/lib/format";
import { typeLabel } from "@/lib/violationLabels";

export default function AlertFeed({ violations = [], total }) {
  // A API já devolve do mais recente para o mais antigo; só garantimos a ordem.
  const sorted = useMemo(
    () => [...violations].sort((a, b) => new Date(b.detected_at) - new Date(a.detected_at)),
    [violations]
  );

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col h-[600px] transition-colors">
      <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center bg-slate-50/50 dark:bg-slate-800/50 rounded-t-xl">
        <h2 className="font-bold text-slate-800 dark:text-slate-200 flex items-center gap-2">
          <AlertCircle className="text-red-500 dark:text-red-400 w-5 h-5" />
          Log de Eventos Críticos
        </h2>
        <Badge className="bg-white dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700" variant="outline">
          {total ?? violations.length} total
        </Badge>
      </div>

      <ScrollArea className="flex-1">
        {sorted.length === 0 ? (
          <p className="p-8 text-center text-sm text-slate-400">Nenhum evento registrado.</p>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {sorted.map((v) => (
              <div key={v.id} className={`p-4 transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/30 ${v.status === "active" ? "border-l-4 border-l-red-500" : ""}`}>
                <div className="flex justify-between items-start">
                  <span className="text-sm font-bold text-slate-700 dark:text-slate-200 uppercase">
                    ⚠️ {typeLabel(v.type, "alert")}
                  </span>
                  <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500">{formatDateTime(v.detected_at, "HH:mm:ss")}</span>
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <MapPin className="text-slate-400 dark:text-slate-500" size={12} />
                  <span className="text-xs text-slate-600 dark:text-slate-400 font-medium">{v.zone}</span>
                  <Badge className="ml-auto text-[10px] h-5 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border-none">
                    {v.status === "active" ? "PENDENTE" : v.status === "acknowledged" ? "EM ANÁLISE" : "RESOLVIDO"}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
