import React, { useEffect } from "react";
import { Camera, X } from "lucide-react";
import Brackets from "@/components/common/Brackets";

/** Modal com a foto da infração. Fecha com Esc, clicando fora ou no botão. */
export default function EvidenceModal({ src, onClose }) {
  useEffect(() => {
    if (!src) return undefined;
    const onKeyDown = (event) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [src, onClose]);

  if (!src) return null;

  return (
    <div
      className="animate-in fade-in fixed inset-0 z-[100] flex items-center justify-center bg-black/85 p-4 backdrop-blur-sm duration-200"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Captura da infração"
    >
      <div
        // data-screen: o modal precisa da cor de sinal das violações, mesmo aberto a partir do dashboard
        data-screen="violations"
        className="relative w-full max-w-4xl overflow-hidden border border-border bg-card shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="hazard h-2" aria-hidden />
        <div className="flex items-center justify-between border-b border-border bg-surface px-4 py-3">
          <h3 className="display flex items-center gap-2.5 text-xl text-foreground">
            <Camera className="h-5 w-5 text-signal-ink" />
            Evidência capturada pela IA
          </h3>
          <button
            onClick={onClose}
            aria-label="Fechar"
            className="p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="relative flex min-h-[300px] items-center justify-center bg-black p-4">
          <Brackets className="inset-4" />
          <img src={src} alt="Registro da infração gerado pelo YOLO" className="h-auto max-h-[70vh] w-full object-contain" />
        </div>
      </div>
    </div>
  );
}
