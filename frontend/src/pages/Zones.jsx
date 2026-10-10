import React from "react";
import { Camera, MapPin, MapPinned } from "lucide-react";
import { useAreas } from "@/api/queries";
import ApiErrorNotice from "@/components/common/ApiErrorNotice";
import PageHeader from "@/components/common/PageHeader";
import { cn } from "@/lib/utils";
import { timeAgo } from "@/lib/format";

// Resume o estado das câmeras da área para a etiqueta do cartão.
function areaStatus(dispositivos) {
  if (dispositivos.length === 0) {
    return { label: "Sem câmera", className: "border-border bg-muted text-muted-foreground" };
  }
  if (dispositivos.some((d) => d.online)) {
    return { label: "Monitorada", className: "border-success/50 bg-success/10 text-success" };
  }
  return { label: "Câmera offline", className: "border-warning/50 bg-warning/10 text-warning" };
}

export default function Zones() {
  const { data: areas = [], isLoading, error } = useAreas();

  const totalCameras = areas.reduce((sum, area) => sum + area.dispositivos.length, 0);
  const onlineCameras = areas.reduce((sum, area) => sum + area.dispositivos.filter((d) => d.online).length, 0);

  return (
    <div className="animate-in fade-in space-y-8 duration-500">
      <PageHeader
        code="03"
        icon={MapPinned}
        title="Zonas de risco"
        description="Monitoramento das áreas do canteiro e dos dispositivos de borda ativos em cada uma."
      >
        <div className="flex items-stretch border border-border bg-card font-mono">
          <div className="px-4 py-2 text-right">
            <div className="display text-3xl tabular-nums text-foreground">{areas.length}</div>
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground">zonas</div>
          </div>
          <div className="border-l border-border px-4 py-2 text-right">
            <div className="display text-3xl tabular-nums text-success">
              {onlineCameras}
              <span className="text-xl text-muted-foreground">/{totalCameras}</span>
            </div>
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground">câmeras online</div>
          </div>
        </div>
      </PageHeader>

      <ApiErrorNotice error={error} />

      {isLoading ? (
        <p className="font-mono text-sm uppercase tracking-wider text-muted-foreground">Carregando zonas...</p>
      ) : areas.length === 0 && !error ? (
        <p className="font-mono text-sm uppercase tracking-wider text-muted-foreground">Nenhuma zona cadastrada no banco de dados.</p>
      ) : (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
          {areas.map((area, index) => {
            const status = areaStatus(area.dispositivos);
            return (
              <article key={area.id_area} className="panel group relative overflow-hidden transition-colors hover:border-signal">
                <span className="absolute inset-x-0 top-0 h-1 bg-signal" aria-hidden />

                <div className="flex items-start justify-between gap-4 p-5 pt-7">
                  <div className="min-w-0">
                    <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.22em] text-signal-ink">
                      Zona {String(index + 1).padStart(2, "0")}
                    </p>
                    <h2 className="display mt-2 break-words text-3xl text-foreground">{area.nome_area}</h2>
                  </div>
                  <div className="chamfer-sm flex h-11 w-11 shrink-0 items-center justify-center bg-signal text-signal-foreground">
                    <MapPin className="h-6 w-6" strokeWidth={2.25} />
                  </div>
                </div>

                <div className="space-y-3 px-5 pb-5">
                  <span className={cn("inline-flex items-center gap-1.5 border px-2 py-1 font-mono text-[10px] font-semibold uppercase tracking-wider", status.className)}>
                    <span className="h-1.5 w-1.5 bg-current" aria-hidden />
                    {status.label}
                  </span>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {area.descricao || "Área monitorada por visão computacional para conformidade de EPIs."}
                  </p>
                </div>

                <div className="border-t border-border bg-surface">
                  {area.dispositivos.length === 0 ? (
                    <div className="flex items-center gap-2 px-5 py-3 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                      <Camera className="h-4 w-4" /> Nenhum dispositivo atribuído
                    </div>
                  ) : (
                    <ul className="divide-y divide-border">
                      {area.dispositivos.map((d) => (
                        <li key={d.id_dispositivo} className="flex items-center justify-between gap-3 px-5 py-3 font-mono text-xs">
                          <span className="flex min-w-0 items-center gap-2.5">
                            <span className={cn("led shrink-0", d.online ? "led-pulse text-success" : "text-muted-foreground")} />
                            <Camera className="h-4 w-4 shrink-0 text-muted-foreground" />
                            <span className="truncate font-bold uppercase tracking-wide text-foreground">{d.numero_serie}</span>
                          </span>
                          <span className="shrink-0 uppercase tracking-wider text-muted-foreground">
                            {d.ultima_atividade ? timeAgo(d.ultima_atividade) : "sem sinal"}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
