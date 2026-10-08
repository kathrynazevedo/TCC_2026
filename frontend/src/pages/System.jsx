import React, { useEffect, useRef, useState } from "react";
import { Cpu, Terminal, Wifi, WifiOff } from "lucide-react";
import { useEdgeStatus } from "@/api/queries";
import { timeAgo } from "@/lib/format";

const EDGE_IP = import.meta.env.VITE_EDGE_IP; // opcional, só informativo
const MAX_LOGS = 50;

const stamp = (message) => `[${new Date().toLocaleTimeString("pt-BR")}] ${message}`;

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
      api: "⚠️ Falha ao conectar com o Backend (API).",
      online: "Conexão com a Edge estabelecida.",
      offline: "⚠️ Perda de comunicação com a Edge (sem heartbeat recente).",
    };
    setLogs((old) => [...old, stamp(messages[state])].slice(-MAX_LOGS));
    previous.current = state;
  }, [state]);

  const online = state === "online";
  const device = data?.detalhes;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 max-w-[1200px] mx-auto animate-in fade-in duration-500">
      <div className="rounded-xl bg-slate-800 dark:bg-slate-900 border border-slate-700 p-6 text-slate-50 shadow-lg">
        <h3 className="flex items-center gap-2.5 font-bold text-sky-400 mb-5">
          <Cpu className="w-5 h-5" /> Conectividade Edge (Raspberry Pi)
        </h3>

        <div className="flex items-center gap-3 mb-4">
          <span
            className={`w-3 h-3 rounded-full transition-all ${online ? "bg-green-500 shadow-[0_0_8px_#22c55e]" : "bg-red-500 shadow-[0_0_8px_#ef4444]"}`}
          />
          <span className="flex items-center gap-2">
            {online ? <Wifi className="w-4 h-4 text-green-400" /> : <WifiOff className="w-4 h-4 text-red-400" />}
            {isLoading && "Verificando..."}
            {state === "online" && "Online (Ativa)"}
            {state === "offline" && "Offline (sem sinal)"}
            {state === "api" && "Backend inalcançável"}
          </span>
        </div>

        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
          {device && (
            <>
              <dt className="text-slate-400">Dispositivo</dt>
              <dd className="font-mono">{device.numero_serie}</dd>
              <dt className="text-slate-400">Último sinal</dt>
              <dd className="font-mono">{timeAgo(device.ultima_atividade)}</dd>
            </>
          )}
          {EDGE_IP && (
            <>
              <dt className="text-slate-400">IP configurado</dt>
              <dd className="font-mono">{EDGE_IP}</dd>
            </>
          )}
          {data && (
            <>
              <dt className="text-slate-400">Critério</dt>
              <dd>Offline após {data.limite_offline_segundos}s sem heartbeat</dd>
            </>
          )}
        </dl>

        <p className="text-slate-400 text-sm mt-5">
          A placa envia um heartbeat periódico para a API; o painel consulta o último sinal registrado no banco.
        </p>
      </div>

      <div className="rounded-xl bg-slate-800 dark:bg-slate-900 border border-slate-700 p-6 text-slate-50 shadow-lg">
        <h3 className="flex items-center gap-2.5 font-bold text-sky-400 mb-5">
          <Terminal className="w-5 h-5" /> Logs do Diagnóstico
        </h3>
        <div className="bg-[#090d16] text-green-500 font-mono text-[13px] p-4 rounded-md h-[220px] overflow-y-auto border border-slate-700 space-y-1.5">
          {logs.map((log, index) => (
            <div key={index}>{log}</div>
          ))}
        </div>
      </div>
    </div>
  );
}
