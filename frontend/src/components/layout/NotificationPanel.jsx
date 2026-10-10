import React, { useState } from "react";
import { Bell, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Link } from "react-router-dom";
import { useViolations } from "@/api/queries";
import { timeAgo } from "@/lib/format";
import { typeLabel } from "@/lib/violationLabels";

export default function NotificationPanel() {
  const [isOpen, setIsOpen] = useState(false);

  const { data: violations = [] } = useViolations();
  const alerts = violations.filter((v) => v.status === "active").slice(0, 8);

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Alertas de campo" className="relative shrink-0 text-foreground hover:bg-accent">
          <Bell className="h-5 w-5" />
          {alerts.length > 0 && (
            <span className="absolute right-1 top-1 flex min-w-[18px] items-center justify-center bg-destructive px-1 font-mono text-[10px] font-bold leading-[18px] text-destructive-foreground">
              {alerts.length}
            </span>
          )}
        </Button>
      </PopoverTrigger>

      <PopoverContent className="z-50 mt-2 w-[calc(100vw-32px)] border border-border bg-popover p-0 shadow-2xl sm:w-96" align="end" sideOffset={8}>
        <div className="hazard h-1" aria-hidden />
        <div className="flex items-center justify-between border-b border-border bg-surface px-4 py-3">
          <h3 className="display text-lg text-foreground">Alertas de campo</h3>
          <span className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">{alerts.length} pendente(s)</span>
        </div>

        <ScrollArea className="h-[400px]">
          {alerts.length > 0 ? (
            <div className="divide-y divide-border">
              {alerts.map((v) => (
                <div key={v.id} className="flex gap-3 border-l-[3px] border-l-destructive px-4 py-3 transition-colors hover:bg-accent/50">
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-bold uppercase tracking-wide text-foreground">{typeLabel(v.type, "alert")}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{v.zone}</p>
                    <div className="mt-2 flex items-center gap-1 font-mono text-[10px] uppercase text-muted-foreground">
                      <Clock className="h-3 w-3" />
                      {timeAgo(v.detected_at)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center gap-2 py-20 text-muted-foreground">
              <span className="led text-success" />
              <p className="font-mono text-xs uppercase tracking-wider">Nenhum alerta pendente</p>
            </div>
          )}
        </ScrollArea>

        <div className="border-t border-border bg-surface p-3 text-center">
          <Link
            to="/violations"
            onClick={() => setIsOpen(false)}
            className="block w-full font-mono text-[11px] font-bold uppercase tracking-widest text-signal-ink hover:underline"
          >
            Ver todo o histórico →
          </Link>
        </div>
      </PopoverContent>
    </Popover>
  );
}
