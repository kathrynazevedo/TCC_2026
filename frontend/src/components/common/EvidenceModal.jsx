import React, { useEffect } from "react";
import { Camera, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { epiStateConfig } from "@/lib/violationLabels";

function EpiBadge({ label, epi }) {
  const config = epiStateConfig[epi?.estado] || epiStateConfig.desconhecido;
  const confidence = epi?.confianca === null || epi?.confianca === undefined ? "" : ` ${Math.round(epi.confianca * 100)}%`;
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300">
      {label}
      <span className={cn("px-1.5 py-0.5 rounded font-medium", config.color)}>
        {config.label}
        {epi?.estado === "desconhecido" ? "" : confidence}
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
      className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/80 backdrop-blur-sm p-4 animate-in fade-in duration-200"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Captura da infração"
    >
      <div
        className="relative bg-white dark:bg-slate-900 rounded-xl shadow-2xl max-w-4xl w-full max-h-[95vh] overflow-y-auto border border-slate-200 dark:border-slate-800"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex justify-between items-center p-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
          <h3 className="font-bold text-slate-800 dark:text-slate-200 flex items-center gap-2">
            <Camera className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            Evidência Capturada pela IA
          </h3>
          <button
            onClick={onClose}
            aria-label="Fechar"
            className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-full transition-colors text-slate-500 dark:text-slate-400"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="bg-slate-100 dark:bg-black/50 flex items-center justify-center p-4 min-h-[300px]">
          <img src={src} alt="Registro da infração gerado pelo YOLO" className="w-full h-auto max-h-[60vh] object-contain rounded shadow-sm" />
        </div>

        {hasPeople && (
          <div className="p-4 border-t border-slate-100 dark:border-slate-800">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">
              Cena: {peopleTotal ?? people.length} pessoa(s) em cena
            </p>
            <ul className="space-y-1.5">
              {people.map((person) => (
                <li
                  key={person.numero}
                  className={cn(
                    "flex flex-wrap items-center gap-x-4 gap-y-1 rounded-lg px-3 py-2 text-sm border",
                    person.numero === highlight
                      ? "border-blue-300 dark:border-blue-700 bg-blue-50 dark:bg-blue-900/20"
                      : "border-slate-100 dark:border-slate-800"
                  )}
                >
                  <span className="font-semibold text-slate-800 dark:text-slate-200 w-20">Pessoa {person.numero}</span>
                  <EpiBadge label="Capacete" epi={person.capacete} />
                  <EpiBadge label="Colete" epi={person.colete} />
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
