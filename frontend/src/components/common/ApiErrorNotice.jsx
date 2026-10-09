import React from "react";
import { WifiOff } from "lucide-react";

/** Faixa de aviso quando uma consulta à API falha. Não renderiza nada se não houver erro. */
export default function ApiErrorNotice({ error }) {
  if (!error) return null;

  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-xl border border-red-200 dark:border-red-900/50 bg-red-50 dark:bg-red-900/20 p-4 text-sm text-red-800 dark:text-red-300"
    >
      <WifiOff className="w-5 h-5 shrink-0 mt-0.5" />
      <div>
        <p className="font-semibold">Falha ao carregar os dados</p>
        <p className="text-red-700/90 dark:text-red-300/80">{error.message} Tentando novamente automaticamente.</p>
      </div>
    </div>
  );
}
