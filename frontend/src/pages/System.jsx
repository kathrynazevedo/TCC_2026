import React, { useEffect, useRef, useState } from "react";
import { Cpu, Terminal } from "lucide-react";
import { useEdgeStatus } from "@/api/queries";
import { timeAgo } from "@/lib/format";
import PageHeader from "@/components/common/PageHeader";
import { cn } from "@/lib/utils";

const EDGE_IP = import.meta.env.VITE_EDGE_IP; // opcional, só informativo
const MAX_LOGS = 50;

const stamp = (message) => `[${new Date().toLocaleTimeString("pt-BR")}] ${message}`;

const STATE_VIEW = {
  online: { word: "Online", tone: "text-success", note: "Placa enviando heartbeat normalmente." },
  offline: { word: "Offline", tone: "text-warning", note: "Sem heartbeat recente da placa." },
  api: { word: "API fora", tone: "text-destructive", note: "O backend não respondeu." },
};

export default function System() {
  const { data, error, isLoading } = useEdgeStatus();
  const [logs, setLogs] = useState(() => [stamp("Sistema de diagnóstico iniciado.")]);
  const previous = useRef(null);

  // Estado resumido: "api" (backend fora), "online" ou "offline" (placa sem heartbeat).
  const state = error ? "api" : data ? (data.online ? "online" : "offline") : null;

  // Registra no log apenas as mudanças de estado.
  useEffect(() => {
    if (!state || previous.current === state) return;
    const messages = {
      api: "ERRO  Falha ao conectar com o Backend (API).",
      online: "OK    Conexão com a Edge estabelecida.",
      offline: "WARN  Perda de comunicação com a Edge (sem heartbeat recente).",
    };
    setLogs((old) => [...old, stamp(messages[state])].slice(-MAX_LOGS));
    previous.current = state;
  }, [state]);

  const device = data?.detalhes;
  const view = state ? STATE_VIEW[state] : null;

  return (
    <div className="animate-in fade-in space-y-8 duration-500">
      <PageHeader
        code="06"
        icon={Cpu}
        title="Sistema"
        description="Diagnóstico da conexão entre a placa de borda (Raspberry Pi) e a API."
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Conectividade */}
        <section className="panel overflow-hidden">
          <div className="flex items-center gap-3 border-b border-border bg-surface px-5 py-4">
            <Cpu className="h-5 w-5 text-signal-ink" />
            <h2 className="display text-xl text-foreground">Conectividade da borda</h2>
          </div>

          <div className="flex items-center gap-5 p-6">
            <span
              className={cn(
                "led h-5 w-5 shrink-0",
                view ? view.tone : "text-muted-foreground",
                state === "online" && "led-pulse"
              )}
            />
            <div>
              <p className={cn("display text-5xl", view ? view.tone : "text-muted-foreground")}>
                {isLoading ? "Verificando" : view ? view.word : "—"}
              </p>
              <p className="mt-2 font-mono text-xs uppercase tracking-wider text-muted-foreground">{view?.note}</p>
            </div>
          </div>

          <dl className="grid grid-cols-[auto_1fr] gap-x-8 gap-y-3 border-t border-border bg-surface px-6 py-5 font-mono text-sm">
            {device && (
              <>
                <dt className="uppercase tracking-wider text-muted-foreground">Dispositivo</dt>
                <dd className="font-semibold text-foreground">{device.numero_serie}</dd>
                <dt className="uppercase tracking-wider text-muted-foreground">Último sinal</dt>
                <dd className="font-semibold text-foreground">{timeAgo(device.ultima_atividade)}</dd>
              </>
            )}
            {EDGE_IP && (
              <>
                <dt className="uppercase tracking-wider text-muted-foreground">IP configurado</dt>
                <dd className="font-semibold text-foreground">{EDGE_IP}</dd>
              </>
            )}
            {data && (
              <>
                <dt className="uppercase tracking-wider text-muted-foreground">Critério</dt>
                <dd className="text-foreground">Offline após {data.limite_offline_segundos}s sem heartbeat</dd>
              </>
            )}
          </dl>

          <p className="border-t border-border px-6 py-4 text-sm leading-relaxed text-muted-foreground">
            A placa envia um heartbeat periódico para a API; o painel consulta o último sinal registrado no banco.
          </p>
        </section>

        {/* Terminal de diagnóstico */}
        <section className="panel overflow-hidden">
          <div className="flex items-center gap-3 border-b border-border bg-surface px-5 py-4">
            <Terminal className="h-5 w-5 text-signal-ink" />
            <h2 className="display text-xl text-foreground">Logs do diagnóstico</h2>
          </div>
          <div className="h-[340px] space-y-1.5 overflow-y-auto bg-[#07090c] p-5 font-mono text-[13px] leading-relaxed text-[#35e08a]">
            {logs.map((log, index) => (
              <div key={index} className={cn(log.includes("ERRO") && "text-[#ff5a5a]", log.includes("WARN") && "text-[#ffb020]")}>
                <span className="mr-2 select-none text-white/30">$</span>
                {log}
              </div>
            ))}
            <div className="text-white/40">
              <span className="mr-2 select-none">$</span>
              <span className="animate-pulse">▍</span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
