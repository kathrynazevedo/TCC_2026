import React, { useEffect } from "react";
import { Camera, Users, X } from "lucide-react";
import Brackets from "@/components/common/Brackets";
import { cn } from "@/lib/utils";
import { epiStateConfig } from "@/lib/violationLabels";

/** Capacete / Colete de uma pessoa da cena: OK, Ausente ou Não detectado (+ confiança quando houve detecção). */
function EpiTag({ label, epi }) {
  const config = epiStateConfig[epi?.estado] || epiStateConfig.desconhecido;
  const confidence =
    epi?.estado === "desconhecido" || epi?.confianca === null || epi?.confianca === undefined
      ? ""
      : ` ${Math.round(epi.confianca * 100)}%`;
  return (
    <span className="inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
      {label}
      <span className={cn("border px-1.5 py-0.5 font-semibold", config.color)}>
        {config.label}
        {confidence}
      </span>
    </span>
  );
}

/**
 * Modal com a foto da captura. Fecha com Esc, clicando fora ou no botão.
 * `people` (opcional) é a cena completa enviada pela placa: cada pessoa com o estado do capacete e do colete;
 * `highlight` destaca a pessoa da infração que abriu o modal.
 */
export default function EvidenceModal({ src, onClose, people = null, peopleTotal = null, highlight = null }) {
  useEffect(() => {
    if (!src) return undefined;
    const onKeyDown = (event) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [src, onClose]);

  if (!src) return null;

  const hasPeople = Array.isArray(people) && people.length > 0;

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
        className="relative max-h-[95vh] w-full max-w-4xl overflow-y-auto border border-border bg-card shadow-2xl"
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
          <img
            src={src}
            alt="Registro da infração gerado pelo YOLO"
            className={cn("h-auto w-full object-contain", hasPeople ? "max-h-[55vh]" : "max-h-[70vh]")}
          />
        </div>

        {hasPeople && (
          <div className="border-t border-border p-4">
            <p className="mb-3 flex items-center gap-2 font-mono text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              <Users className="h-3.5 w-3.5" />
              Cena: {peopleTotal ?? people.length} pessoa(s) em cena
            </p>
            <ul className="space-y-1.5">
              {people.map((person) => (
                <li
                  key={person.numero}
                  className={cn(
                    "flex flex-wrap items-center gap-x-5 gap-y-1.5 border px-3 py-2",
                    person.numero === highlight ? "border-signal bg-signal/10" : "border-border bg-surface"
                  )}
                >
                  <span className="display w-24 text-base text-foreground">Pessoa {person.numero}</span>
                  <EpiTag label="Capacete" epi={person.capacete} />
                  <EpiTag label="Colete" epi={person.colete} />
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
