// Regras de leitura da telemetria da placa (GET /api/status/edge -> telemetria).

// Acima disso a placa já reduz o clock sozinha (Raspberry Pi 4: ~80 °C).
export const TEMP_WARN = 65;
export const TEMP_CRITICAL = 80;
// Telemetria sem atualização há mais que isso é tratada como antiga (o heartbeat chega a cada ~30 s).
export const STALE_AFTER_SECONDS = 120;

export const temperatureTone = (celsius) => {
  if (celsius === undefined || celsius === null) return "neutral";
  if (celsius >= TEMP_CRITICAL) return "danger";
  if (celsius >= TEMP_WARN) return "warn";
  return "ok";
};

export const usageTone = (percent) => {
  if (percent === undefined || percent === null) return "neutral";
  if (percent >= 90) return "danger";
  if (percent >= 75) return "warn";
  return "ok";
};

// Carga de CPU: com o modelo rodando, ~100% (todos os núcleos ocupados) é o NORMAL desta placa, não um problema.
// Só preocupa quando passa muito disso (fila de processos esperando CPU).
export const cpuLoadTone = (percent) => {
  if (percent === undefined || percent === null) return "neutral";
  if (percent >= 150) return "danger";
  if (percent >= 110) return "warn";
  return "ok";
};

// Bits de `vcgencmd get_throttled` (os 4 primeiros são o estado atual; os de 16 a 19, o que já ocorreu desde o boot).
const THROTTLE_FLAGS = [
  [0x1, "subtensão agora"],
  [0x2, "frequência limitada agora"],
  [0x4, "CPU freada agora"],
  [0x8, "limite térmico suave agora"],
  [0x10000, "subtensão desde o boot"],
  [0x20000, "frequência já foi limitada"],
  [0x40000, "a CPU já foi freada"],
  [0x80000, "já houve limite térmico suave"],
];

// "0x0" -> { tone: "ok", label: "Sem limitação", details: [] }
export const decodeThrottle = (hex) => {
  if (!hex) return { tone: "neutral", label: "—", details: [] };
  const value = parseInt(hex, 16);
  if (Number.isNaN(value)) return { tone: "neutral", label: "—", details: [] };
  if (value === 0) return { tone: "ok", label: "Sem limitação", details: [] };
  const details = THROTTLE_FLAGS.filter(([bit]) => value & bit).map(([, text]) => text);
  const now = value & 0xf; // algo está limitando AGORA
  return { tone: now ? "danger" : "warn", label: now ? "Limitada agora" : "Já limitou", details };
};

// Câmera em uso. Só existe quando a placa tem câmera reserva; sem ela o cartão nem aparece.
export const describeCamera = (t) => {
  if (!t?.camera_ativa) return null;
  const reserve = { 1: "reserva pronta", 0: "reserva sem resposta" }[t.reserva_ok] ?? "reserva não testada";
  const onReserve = t.camera_ativa === "reserva";
  return {
    value: onReserve ? "Reserva" : "Principal",
    // fora do normal: a reserva está em uso, ou a principal está em uso mas não há reserva respondendo
    tone: onReserve || t.reserva_ok === 0 ? "warn" : "ok",
    note: `${t.trocas_camera ?? 0} troca(s) · ${reserve}`,
  };
};

// 3700 -> "1h 01min" · 125 -> "2min" · 40 -> "40s"
export const formatUptime = (seconds) => {
  if (seconds === undefined || seconds === null) return "—";
  const total = Math.max(0, Math.round(seconds));
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${String(minutes).padStart(2, "0")}min`;
  if (minutes > 0) return `${minutes}min`;
  return `${total}s`;
};

// Milissegundos: acima de 1 s mostra em segundos (2400 -> "2,4 s").
export const formatMs = (ms) => {
  if (ms === undefined || ms === null) return { value: "—", unit: "" };
  if (ms >= 1000) return { value: (ms / 1000).toFixed(1).replace(".", ","), unit: "s" };
  return { value: String(Math.round(ms)), unit: "ms" };
};

export const formatNumber = (value, digits = 1) =>
  value === undefined || value === null ? "—" : Number(value).toFixed(digits).replace(".", ",");

// "1" -> "1 pessoa" · "4" -> "4 ou mais"
export const loadGroupLabel = (key) => (key === "1" ? "1 pessoa" : key === "4" ? "4 ou mais" : `${key} pessoas`);

const CLASS_ORDER = ["capacete", "colete", "pessoa"];
const CLASS_LABELS = { capacete: "Capacete", colete: "Colete", pessoa: "Pessoa", todas: "Todas as classes" };

// Classes do modelo na ordem do documento (capacete, colete, pessoa, outras...) e "todas" por último.
export const orderValidationClasses = (names) => {
  const rank = (name) => (name === "todas" ? 99 : CLASS_ORDER.includes(name) ? CLASS_ORDER.indexOf(name) : 50);
  return [...names].sort((a, b) => rank(a) - rank(b) || a.localeCompare(b));
};

export const validationClassLabel = (name) => CLASS_LABELS[name] || name.charAt(0).toUpperCase() + name.slice(1);
