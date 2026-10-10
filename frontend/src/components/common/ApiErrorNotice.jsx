import React from "react";
import { WifiOff } from "lucide-react";

/** Faixa de aviso quando uma consulta à API falha. Não renderiza nada se não houver erro. */
export default function ApiErrorNotice({ error }) {
  if (!error) return null;

  return (
    <div
      role="alert"
      className="flex items-start gap-3 border border-destructive/40 border-l-4 border-l-destructive bg-destructive/10 p-4 text-sm text-foreground"
    >
      <WifiOff className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
      <div>
        <p className="font-mono text-xs font-bold uppercase tracking-wider text-destructive">Falha ao carregar os dados</p>
        <p className="mt-1 text-muted-foreground">{error.message} Tentando novamente automaticamente.</p>
      </div>
    </div>
  );
}
