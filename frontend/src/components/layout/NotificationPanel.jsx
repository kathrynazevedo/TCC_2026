import React, { useState } from "react";
import { Bell, AlertTriangle, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Link } from "react-router-dom";
import { useViolations } from "@/api/queries";
import { timeAgo } from "@/lib/format";
import { typeLabel } from "@/lib/violationLabels";

export default function NotificationPanel() {
  // Controle de estado para fechar o menu ao clicar no link
  const [isOpen, setIsOpen] = useState(false);

  const { data: violations = [] } = useViolations();
  const alerts = violations.filter((v) => v.status === "active").slice(0, 8);

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Alertas de campo" className="relative hover:bg-slate-100 dark:hover:bg-slate-800 shrink-0">
          <Bell className="h-5 w-5 text-slate-600 dark:text-slate-300" />
          {alerts.length > 0 && (
            <span className="absolute top-2 right-2 flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
            </span>
          )}
        </Button>
      </PopoverTrigger>

      <PopoverContent
        className="w-[calc(100vw-32px)] sm:w-96 p-0 mt-2 bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 z-50"
        align="end"
        sideOffset={8}
      >
        <div className="p-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
          <h3 className="font-bold text-sm text-slate-800 dark:text-slate-100">Alertas de Campo</h3>
        </div>

        <ScrollArea className="h-[400px] bg-white dark:bg-slate-900">
          {alerts.length > 0 ? (
            <div className="divide-y divide-slate-100 dark:divide-slate-800">
              {alerts.map((v) => (
                <div key={v.id} className="p-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                  <div className="flex gap-3">
                    <div className="mt-1 shrink-0">
                      <AlertTriangle className="h-4 w-4 text-red-500" />
                    </div>
                    <div className="flex-1">
                      <p className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase">{typeLabel(v.type, "alert")}</p>
                      <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">{v.zone}</p>
                      <div className="flex items-center gap-1 mt-2 text-[10px] text-slate-400">
                        <Clock className="h-3 w-3" />
                        {timeAgo(v.detected_at)}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-20 text-slate-400">
              <p className="text-xs font-medium">Nenhum alerta pendente</p>
            </div>
          )}
        </ScrollArea>

        <div className="p-3 border-t border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 text-center">
          <Link
            to="/violations"
            onClick={() => setIsOpen(false)}
            className="text-[10px] font-bold text-blue-600 dark:text-blue-400 uppercase hover:underline block w-full"
          >
            Ver todo o histórico
          </Link>
        </div>
      </PopoverContent>
    </Popover>
  );
}
