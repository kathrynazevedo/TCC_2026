import React, { useState } from "react";
import { Bell, AlertTriangle, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useQuery } from "@tanstack/react-query";
import { getViolations } from "@/api/apiClient";
import moment from "moment";
import { Link } from "react-router-dom";

export default function NotificationPanel() {
  // Controle de estado para podermos fechar o menu ao clicar no link
  const [isOpen, setIsOpen] = useState(false);

  const { data: violations = [] } = useQuery({
    queryKey: ["violations"],
    queryFn: getViolations,
  });

  const alerts = violations.filter(v => v.status === 'active').slice(0, 8);

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative hover:bg-slate-100 shrink-0">
          <Bell className="h-5 w-5 text-slate-600" />
          {alerts.length > 0 && (
            <span className="absolute top-2 right-2 flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
            </span>
          )}
        </Button>
      </PopoverTrigger>
      
      <PopoverContent 
        className="w-[calc(100vw-32px)] sm:w-96 p-0 mt-2 bg-white shadow-2xl border border-slate-200 z-50" 
        align="end"
        sideOffset={8}
      >
        <div className="p-4 border-b border-slate-100 bg-slate-50">
          <h3 className="font-bold text-sm text-slate-800">Alertas de Campo</h3>
        </div>
        
        <ScrollArea className="h-[400px] bg-white">
          {alerts.length > 0 ? (
            <div className="divide-y divide-slate-100">
              {alerts.map((v) => (
                <div key={v.id} className="p-4 hover:bg-slate-50 transition-colors">
                  <div className="flex gap-3">
                    <div className="mt-1 shrink-0">
                      <AlertTriangle className="h-4 w-4 text-red-500" />
                    </div>
                    <div className="flex-1">
                      <p className="text-xs font-bold text-slate-900 uppercase">
                        {v.type === 'no-helmet' ? 'Falta de Capacete' : 'Falta de Colete'}
                      </p>
                      <p className="text-xs text-slate-600 mt-1">{v.zone}</p>
                      <div className="flex items-center gap-1 mt-2 text-[10px] text-slate-400">
                        <Clock className="h-3 w-3" />
                        {moment(v.detected_at).fromNow()}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-20 text-slate-400 bg-white">
              <p className="text-xs font-medium">Nenhum alerta pendente</p>
            </div>
          )}
        </ScrollArea>
        
        <div className="p-3 border-t border-slate-100 bg-slate-50 text-center">
          {/* Substituímos o <button> por um <Link> do React Router */}
          <Link 
            to="/violations" 
            onClick={() => setIsOpen(false)}
            className="text-[10px] font-bold text-blue-600 uppercase hover:underline block w-full"
          >
            Ver todo o histórico
          </Link>
        </div>
      </PopoverContent>
    </Popover>
  );
}