import React, { useState } from "react";
import { Camera, Maximize2, ShieldCheck } from "lucide-react";
import EvidenceModal from "@/components/common/EvidenceModal";
import Brackets from "@/components/common/Brackets";
import { formatDateTime } from "@/lib/format";
import { typeLabel } from "@/lib/violationLabels";

const camLabel = (id) => `CAM ${String(id ?? 0).padStart(2, "0")}`;

export default function RecentViolations({ violations = [] }) {
  const [selectedImage, setSelectedImage] = useState(null);
  const recent = violations.slice(0, 6);

  return (
    <section className="panel overflow-hidden">
      <div className="flex items-center justify-between gap-3 border-b border-border bg-surface px-5 py-4">
        <div className="flex items-center gap-3">
          <Camera className="h-5 w-5 text-signal-ink" />
          <div>
            <h2 className="display text-xl text-foreground">Últimas evidências</h2>
            <p className="mt-1 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">Capturas do modelo YOLO em tempo real</p>
          </div>
        </div>
        <span className="flex items-center gap-2 font-mono text-[11px] font-semibold uppercase tracking-wider text-destructive">
          <span className="led led-pulse" /> Rec
        </span>
      </div>

      <div className="p-5">
        {recent.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-2 py-16 text-center">
            <ShieldCheck className="h-12 w-12 text-success" />
            <p className="display text-2xl text-foreground">Canteiro sem ocorrências</p>
            <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">Nenhuma infração registrada até agora</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {recent.map((v) => (
              <figure key={v.id} className="group m-0 border border-border bg-black">
                <div
                  className={`relative aspect-video overflow-hidden ${v.imagem_url ? "cursor-pointer" : ""}`}
                  onClick={() => v.imagem_url && setSelectedImage(v.imagem_url)}
                >
                  {v.imagem_url ? (
                    <img
                      src={v.imagem_url}
                      alt="Evidência da infração"
                      loading="lazy"
                      className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                      onError={(event) => {
                        event.currentTarget.style.display = "none";
                      }}
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center font-mono text-xs uppercase tracking-wider text-white/50">Sem imagem</div>
                  )}

                  <Brackets />

                  {/* "OSD" de câmera de monitoramento */}
                  <div className="absolute inset-x-0 top-0 flex items-center justify-between bg-gradient-to-b from-black/80 to-transparent p-2.5 pb-6 font-mono text-[10px] font-semibold uppercase tracking-wider text-white">
                    <span className="flex items-center gap-1.5">
                      <span className="led led-pulse !h-1.5 !w-1.5 text-destructive" /> {camLabel(v.id_dispositivo)}
                    </span>
                    <span className="bg-destructive px-1.5 py-0.5 text-destructive-foreground">{typeLabel(v.type)}</span>
                  </div>
                  <div className="absolute inset-x-0 bottom-0 flex items-end justify-between bg-gradient-to-t from-black/85 to-transparent p-2.5 pt-6 font-mono text-[10px] uppercase tracking-wider text-white">
                    <span>{formatDateTime(v.detected_at, "dd/MM/yy HH:mm:ss")}</span>
                    <span className="max-w-[45%] truncate text-white/80">{v.zone}</span>
                  </div>

                  {v.imagem_url && (
                    <div className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 transition-opacity group-hover:opacity-100">
                      <span className="flex items-center gap-1.5 bg-signal px-3 py-1.5 font-mono text-[11px] font-bold uppercase tracking-wider text-signal-foreground">
                        <Maximize2 className="h-3.5 w-3.5" /> Ampliar
                      </span>
                    </div>
                  )}
                </div>
              </figure>
            ))}
          </div>
        )}
      </div>

      <EvidenceModal src={selectedImage} onClose={() => setSelectedImage(null)} />
    </section>
  );
}
