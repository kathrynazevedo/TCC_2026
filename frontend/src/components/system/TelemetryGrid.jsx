import React from "react";
import {
  Activity, Box, CloudUpload, Cpu, Gauge, Hourglass, MemoryStick, RotateCcw, ScanLine, Siren, Target, Thermometer,
  Timer, Users, Zap, CalendarClock, HardHat, Shirt, ShieldAlert, Video,
} from "lucide-react";
import { timeAgo } from "@/lib/format";
import { cn } from "@/lib/utils";
import {
  STALE_AFTER_SECONDS, cpuLoadTone, decodeThrottle, describeCamera, formatMs, formatNumber, formatUptime, loadGroupLabel,
  orderValidationClasses, temperatureTone, usageTone, validationClassLabel,
} from "@/lib/telemetry";

const SEGMENTS = 20;

const TONE_TEXT = { ok: "text-success", warn: "text-warning", danger: "text-destructive", neutral: "text-foreground" };
const TONE_BAR = { ok: "bg-success", warn: "bg-warning", danger: "bg-destructive", neutral: "bg-primary" };

// Um indicador da placa: rótulo, valor grande, nota e (opcional) um medidor de 20 segmentos.
function Metric({ icon: Icon, label, value, unit, note, tone = "neutral", meter }) {
  return (
    <div className="panel relative overflow-hidden">
      <span className={cn("absolute inset-x-0 top-0 h-1", TONE_BAR[tone])} aria-hidden />
      <div className="flex items-start justify-between gap-3 p-4 pt-5">
        <div className="min-w-0">
          <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">{label}</p>
          <p className={cn("display mt-2.5 truncate text-4xl tabular-nums", TONE_TEXT[tone])} title={`${value} ${unit || ""}`.trim()}>
            {value}
            {unit && <span className="ml-1.5 font-mono text-sm font-semibold normal-case tracking-normal text-muted-foreground">{unit}</span>}
          </p>
        </div>
        <Icon className="h-5 w-5 shrink-0 text-muted-foreground" strokeWidth={2.25} aria-hidden />
      </div>
      {meter !== undefined && (
        <div className="flex gap-0.5 px-4 pb-3" aria-hidden>
          {Array.from({ length: SEGMENTS }, (_, index) => (
            <span key={index} className={cn("h-1.5 flex-1", index < meter ? TONE_BAR[tone] : "bg-border")} />
          ))}
        </div>
      )}
      {note && <p className="px-4 pb-4 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">{note}</p>}
      {!note && meter === undefined && <div className="pb-4" />}
    </div>
  );
}

const Group = ({ title, children, columns = "xl:grid-cols-4" }) => (
  <div className="space-y-3">
    <h3 className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">{title}</h3>
    <div className={cn("grid grid-cols-1 gap-4 sm:grid-cols-2", columns)}>{children}</div>
  </div>
);

// Tabela de resultados (carga de cena, validação do modelo): mesmo visual dos cartões.
function ResultTable({ title, caption, head, children }) {
  return (
    <div className="space-y-3">
      <h3 className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">{title}</h3>
      <div className="panel overflow-x-auto">
        <table className="w-full min-w-[560px] border-collapse text-left font-mono text-sm">
          <thead>
            <tr className="border-b border-border bg-surface text-[11px] uppercase tracking-wider text-muted-foreground">
              {head.map((label, index) => (
                <th key={label} className={cn("px-4 py-3 font-semibold", index > 0 && "text-right")}>{label}</th>
              ))}
            </tr>
          </thead>
          <tbody>{children}</tbody>
        </table>
        {caption && <p className="border-t border-border px-4 py-3 text-[11px] uppercase tracking-wider text-muted-foreground">{caption}</p>}
      </div>
    </div>
  );
}

const Cell = ({ children, strong }) => (
  <td className={cn("px-4 py-3 text-right tabular-nums", strong ? "font-semibold text-foreground" : "text-foreground")}>{children}</td>
);

// Meio de 0 a 20 segmentos para um valor numa faixa [min, max].
const toMeter = (value, min, max) =>
  value === undefined || value === null ? 0 : Math.round(Math.min(1, Math.max(0, (value - min) / (max - min))) * SEGMENTS);

const samples = (n) => (n === undefined ? "sem amostras ainda" : `${n} amostra${n === 1 ? "" : "s"}`);

/**
 * Cartões e tabelas com tudo que a placa informa pelo heartbeat (temperatura, FPS, latências, confiança por classe,
 * desempenho por carga de cena, validação do modelo, estabilidade...).
 * `telemetry` é o objeto `telemetria` de GET /api/status/edge; `online` diz se o heartbeat está chegando.
 */
export default function TelemetryGrid({ telemetry, online }) {
  const ageSeconds = telemetry?.atualizada_ha_segundos;
  const stale = !online || (ageSeconds !== undefined && ageSeconds > STALE_AFTER_SECONDS);

  if (!telemetry) {
    return (
      <section className="panel p-6">
        <div className="flex items-center gap-3">
          <Activity className="h-5 w-5 text-signal-ink" />
          <h2 className="display text-xl text-foreground">Telemetria da placa</h2>
        </div>
        <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
          Ainda sem dados. Eles chegam junto do heartbeat quando a Raspberry Pi roda a versão nova do programa
          (<span className="font-mono">main.py</span>) e o banco tem as colunas de telemetria (<span className="font-mono">db/schema.sql</span>).
        </p>
      </section>
    );
  }

  const t = telemetry;
  const throttle = decodeThrottle(t.limitacao);
  const camera = describeCamera(t);
  const preMs = formatMs(t.pre_ms);
  const infMs = formatMs(t.inferencia_ms);
  const posMs = formatMs(t.pos_ms);
  const totalMs = formatMs(t.total_ms);
  const decisionMs = formatMs(t.borda_decisao_ms);
  const sirenMs = formatMs(t.borda_sirene_ms);
  const apiMs = formatMs(t.borda_api_ms);
  const p95 = t.total_p95_ms !== undefined ? formatMs(t.total_p95_ms) : null;
  const loadGroups = ["1", "2", "3", "4"];
  const validation = t.validacao;
  const restartIn = t.reinicio_programado_em_s;
  const tempNote = [
    t.temperatura_max_c !== undefined && `máx. ${formatNumber(t.temperatura_max_c, 1)} °C`,
    t.temperatura_media_c !== undefined && `média ${formatNumber(t.temperatura_media_c, 1)} °C`,
  ].filter(Boolean).join(" · ");

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <Activity className="h-5 w-5 text-signal-ink" />
        <h2 className="display text-xl text-foreground">Telemetria da placa</h2>
        <span
          className={cn(
            "ml-auto flex items-center gap-2 border border-border bg-card px-3 py-1.5 font-mono text-[11px] font-semibold uppercase tracking-wider",
            stale ? "text-warning" : "text-foreground"
          )}
        >
          <span className={cn("led", stale ? "text-warning" : "led-pulse text-success")} />
          {stale
            ? `Sem sinal · últimos dados ${ageSeconds !== undefined ? timeAgo(Date.now() - ageSeconds * 1000) : ""}`.trim()
            : `Atualizado ${ageSeconds !== undefined ? timeAgo(Date.now() - ageSeconds * 1000) : "agora"}`}
        </span>
      </div>

      <div className={cn("space-y-6", stale && "opacity-60")}>
        <Group title="Hardware">
          <Metric
            icon={Thermometer}
            label="Temperatura da CPU"
            value={formatNumber(t.temperatura_c, 1)}
            unit="°C"
            tone={temperatureTone(t.temperatura_c)}
            meter={toMeter(t.temperatura_c, 30, 90)}
            note={tempNote || undefined}
          />
          <Metric
            icon={Zap}
            label="Energia e limitação"
            value={throttle.label}
            tone={throttle.tone}
            note={throttle.details.length ? throttle.details.join(" · ") : t.limitacao ? `código ${t.limitacao}` : undefined}
          />
          <Metric
            icon={MemoryStick}
            label="Memória em uso"
            value={formatNumber(t.memoria_pct, 0)}
            unit="%"
            tone={usageTone(t.memoria_pct)}
            meter={toMeter(t.memoria_pct, 0, 100)}
          />
          <Metric
            icon={Cpu}
            label="Carga da CPU"
            value={formatNumber(t.carga_cpu_pct, 0)}
            unit="%"
            tone={cpuLoadTone(t.carga_cpu_pct)}
            meter={toMeter(t.carga_cpu_pct, 0, 100)}
            note="média de 1 min · ~100% é normal com o modelo rodando"
          />
        </Group>

        <Group title="Desempenho da inferência" columns="xl:grid-cols-5">
          <Metric
            icon={Gauge}
            label="Taxa de quadros"
            value={formatNumber(t.fps, 1)}
            unit="FPS"
            note={t.fps_minimo !== undefined ? `pior janela: ${formatNumber(t.fps_minimo, 1)} FPS` : undefined}
          />
          <Metric icon={ScanLine} label="Pré-processamento" value={preMs.value} unit={preMs.unit} note="redimensionar + letterbox" />
          <Metric icon={Box} label="Inferência (YOLO)" value={infMs.value} unit={infMs.unit} note={t.modelo} />
          <Metric icon={Timer} label="Pós-processamento" value={posMs.value} unit={posMs.unit} note="NMS" />
          <Metric
            icon={Hourglass}
            label="Tempo total por quadro"
            value={totalMs.value}
            unit={totalMs.unit}
            note={p95 ? `p95: ${p95.value} ${p95.unit}` : undefined}
          />
        </Group>

        <Group title="Latência do alerta (da câmera até…)" columns="xl:grid-cols-3">
          <Metric icon={ScanLine} label="Decisão de alerta" value={decisionMs.value} unit={decisionMs.unit} note="inclui leitura e fila" />
          <Metric icon={Siren} label="Sirene acionada" value={sirenMs.value} unit={sirenMs.unit} note="último alerta" />
          <Metric icon={CloudUpload} label="Registro na API" value={apiMs.value} unit={apiMs.unit} note="último alerta · foto + banco" />
        </Group>

        <ResultTable
          title="Desempenho por carga de cena (pessoas no quadro)"
          head={["Pessoas no campo de visão", "FPS médio", "Inferência (ms)", "Latência ponta a ponta (ms)", "Temperatura (°C)", "Quadros"]}
          caption="Cada quadro entra no grupo da sua própria contagem de pessoas · latência = da câmera até a decisão de alerta"
        >
          {loadGroups.map((key) => {
            const row = t.carga_cena?.[key];
            return (
              <tr key={key} className={cn("border-b border-border last:border-0", !row && "text-muted-foreground")}>
                <td className="px-4 py-3 font-semibold text-foreground">
                  <Users className="mr-2 inline h-4 w-4 text-muted-foreground" aria-hidden />
                  {loadGroupLabel(key)}
                </td>
                <Cell strong>{formatNumber(row?.fps, 1)}</Cell>
                <Cell>{formatNumber(row?.inferencia_ms, 0)}</Cell>
                <Cell>{formatNumber(row?.borda_decisao_ms, 0)}</Cell>
                <Cell>{formatNumber(row?.temperatura_c, 1)}</Cell>
                <Cell>{row?.quadros ?? "—"}</Cell>
              </tr>
            );
          })}
        </ResultTable>

        <Group title="Confiança média da detecção" columns="xl:grid-cols-3">
          <Metric
            icon={HardHat}
            label="Capacete de segurança"
            value={formatNumber(t.conf_capacete_pct, 1)}
            unit={t.conf_capacete_pct !== undefined ? "%" : undefined}
            note={samples(t.conf_capacete_n)}
          />
          <Metric
            icon={Shirt}
            label="Colete refletivo"
            value={formatNumber(t.conf_colete_pct, 1)}
            unit={t.conf_colete_pct !== undefined ? "%" : undefined}
            note={samples(t.conf_colete_n)}
          />
          <Metric
            icon={ShieldAlert}
            label="Ausência de EPI (infração)"
            value={formatNumber(t.conf_ausencia_pct, 1)}
            unit={t.conf_ausencia_pct !== undefined ? "%" : undefined}
            note={`${samples(t.conf_ausencia_n)} · confiança da pessoa em infração`}
          />
        </Group>

        <ResultTable
          title="Validação do modelo (mAP por classe)"
          head={["Classe", "Precisão", "Recall", "mAP@50", "mAP@50-95"]}
          caption={
            validation
              ? [validation.modelo, validation.conjunto && `conjunto ${validation.conjunto}`, validation.imagens !== undefined && `${validation.imagens} imagens`]
                  .filter(Boolean).join(" · ")
              : "Sem validação enviada: rode a validação no Colab e coloque o validacao_modelo.json na pasta do programa na placa"
          }
        >
          {validation ? (
            orderValidationClasses(Object.keys(validation.classes)).map((name) => {
              const row = validation.classes[name];
              const overall = name === "todas";
              return (
                <tr key={name} className={cn("border-b border-border last:border-0", overall && "bg-surface")}>
                  <td className={cn("px-4 py-3", overall ? "font-semibold text-foreground" : "text-foreground")}>
                    <Target className="mr-2 inline h-4 w-4 text-muted-foreground" aria-hidden />
                    {validationClassLabel(name)}
                  </td>
                  <Cell>{formatNumber(row.precisao, 3)}</Cell>
                  <Cell>{formatNumber(row.recall, 3)}</Cell>
                  <Cell strong>{formatNumber(row.map50, 3)}</Cell>
                  <Cell>{formatNumber(row.map50_95, 3)}</Cell>
                </tr>
              );
            })
          ) : (
            <tr className="text-muted-foreground">
              <td className="px-4 py-3">—</td>
              {[1, 2, 3, 4].map((i) => <Cell key={i}>—</Cell>)}
            </tr>
          )}
        </ResultTable>

        <Group title="Estabilidade" columns={camera ? "xl:grid-cols-5" : undefined}>
          {camera && <Metric icon={Video} label="Câmera em uso" value={camera.value} tone={camera.tone} note={camera.note} />}
          <Metric icon={Hourglass} label="Tempo ligado" value={formatUptime(t.ligado_s)} note="desta execução do programa" />
          <Metric icon={Activity} label="Execução nº" value={t.execucao ?? "—"} note="partidas registradas" />
          <Metric
            icon={RotateCcw}
            label="Reinícios em 8 h"
            value={t.reinicios_8h ?? "—"}
            tone={t.quedas_8h > 0 ? "danger" : "ok"}
            note={
              t.quedas_8h !== undefined
                ? `${t.quedas_8h} queda(s) inesperada(s)${t.reinicios_programados_8h ? ` · ${t.reinicios_programados_8h} programado(s)` : ""}`
                : undefined
            }
          />
          <Metric
            icon={CalendarClock}
            label="Próximo reinício programado"
            value={restartIn === undefined ? "Desligado" : restartIn === 0 ? "Agora" : `em ${formatUptime(restartIn)}`}
            note={t.reinicio_apos_h ? `a cada ${formatNumber(t.reinicio_apos_h, 0)} h de operação` : "REINICIAR_APOS_HORAS=0"}
          />
        </Group>
      </div>
    </section>
  );
}
