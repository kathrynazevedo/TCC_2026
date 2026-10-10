import React, { useMemo } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MapPin, Radio } from "lucide-react";
import StatusTag from "@/components/common/StatusTag";
import { cn } from "@/lib/utils";
import { formatDateTime } from "@/lib/format";
import { typeLabel, personLabel } from "@/lib/violationLabels";

const BAR = {
  active: "border-l-destructive",
  acknowledged: "border-l-warning",
  resolved: "border-l-success/60",
};

export default function AlertFeed({ violations = [], total }) {
  // A API já devolve do mais recente para o mais antigo; só garantimos a ordem.
  const sorted = useMemo(
    () => [...violations].sort((a, b) => new Date(b.detected_at) - new Date(a.detected_at)),
    [violations]
  );

  return (
    <section className="panel flex h-[640px] flex-col overflow-hidden">
      <div className="flex items-center justify-between gap-3 border-b border-border bg-surface px-5 py-4">
        <h2 className="display flex items-center gap-2.5 text-xl text-foreground">
          <Radio className="h-5 w-5 text-destructive" />
          Log de eventos
        </h2>
        <span className="border border-border bg-background px-2 py-1 font-mono text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          {total ?? violations.length} total
        </span>
      </div>

      <ScrollArea className="flex-1">
        {sorted.length === 0 ? (
          <p className="p-8 text-center font-mono text-xs uppercase tracking-wider text-muted-foreground">Nenhum evento registrado.</p>
        ) : (
          <ul className="divide-y divide-border">
            {sorted.map((v) => (
              <li
                key={v.id}
                className={cn("border-l-[3px] px-4 py-3 transition-colors hover:bg-accent/50", BAR[v.status] || BAR.active)}
              >
                <div className="flex items-start justify-between gap-3">
                  <span className="text-sm font-bold uppercase leading-tight tracking-wide text-foreground">{typeLabel(v.type, "alert")}</span>
                  <span className="shrink-0 font-mono text-[11px] tabular-nums text-muted-foreground">
                    {formatDateTime(v.detected_at, "HH:mm:ss")}
                  </span>
                </div>
                <div className="mt-2 flex items-center justify-between gap-2">
                  <span className="flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
                    <MapPin className="h-3 w-3 shrink-0" />
                    <span className="truncate">{v.zone}</span>
                    {personLabel(v) && <span className="shrink-0 font-mono">· {personLabel(v)}</span>}
                  </span>
                  <StatusTag status={v.status} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </ScrollArea>
    </section>
  );
}
