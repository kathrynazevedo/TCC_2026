import React from "react";
import { cn } from "@/lib/utils";
import { statusConfig } from "@/lib/violationLabels";

/** Etiqueta quadrada de status (Ativa / Reconhecida / Resolvida), com as cores do tema. */
export default function StatusTag({ status, className }) {
  const config = statusConfig[status] || statusConfig.active;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 whitespace-nowrap border px-2 py-1 font-mono text-[10px] font-semibold uppercase tracking-wider",
        config.color,
        className
      )}
    >
      <span className="h-1.5 w-1.5 bg-current" aria-hidden />
      {config.label}
    </span>
  );
}
