import React from "react";

/**
 * Cabeçalho padrão das telas: código do módulo, título de placa de obra e a listra de alerta
 * na cor de sinal da tela. `children` vai para o canto direito (contadores, status ao vivo).
 */
export default function PageHeader({ code, title, description, icon: Icon, children }) {
  return (
    <header>
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 font-mono text-[11px] font-semibold uppercase tracking-[0.22em] text-signal-ink">
            <span className="h-2 w-2 bg-signal" aria-hidden />
            Módulo {code}
          </div>
          <h1 className="display mt-2 flex items-center gap-3 text-4xl text-foreground sm:text-5xl">
            {Icon && <Icon className="h-8 w-8 shrink-0 text-signal-ink sm:h-10 sm:w-10" strokeWidth={2.25} aria-hidden />}
            {title}
          </h1>
          {description && <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground">{description}</p>}
        </div>
        {children && <div className="flex flex-wrap items-center gap-3">{children}</div>}
      </div>
      <div className="hazard mt-5 h-1.5 w-full" aria-hidden />
    </header>
  );
}
