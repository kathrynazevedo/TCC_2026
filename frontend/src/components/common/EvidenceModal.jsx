import React, { useEffect } from "react";
import { Camera, X } from "lucide-react";

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
      className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/80 backdrop-blur-sm p-4 animate-in fade-in duration-200"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Captura da infração"
    >
      <div
        className="relative bg-white dark:bg-slate-900 rounded-xl shadow-2xl max-w-4xl w-full overflow-hidden border border-slate-200 dark:border-slate-800"
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
          <img src={src} alt="Registro da infração gerado pelo YOLO" className="w-full h-auto max-h-[70vh] object-contain rounded shadow-sm" />
        </div>
      </div>
    </div>
  );
}
