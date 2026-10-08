// Rótulos compartilhados por todas as telas. Os códigos ("no-helmet", "active"...) vêm da API.

const TYPES = {
  "no-helmet": { short: "Sem Capacete", alert: "Falta de Capacete", long: "Ausência de Capacete" },
  "no-vest": { short: "Sem Colete", alert: "Falta de Colete", long: "Ausência de Colete" },
};
const UNKNOWN_TYPE = { short: "Ausência de EPI", alert: "Falta de EPI", long: "Ausência de EPI" };

/** kind: "short" | "alert" | "long" */
export const typeLabel = (type, kind = "short") => (TYPES[type] || UNKNOWN_TYPE)[kind];

export const severityConfig = {
  low: { label: "Baixa", pdf: "BAIXA", color: "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300" },
  medium: { label: "Média", pdf: "MÉDIA", color: "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400" },
  high: { label: "Alta", pdf: "ALTA", color: "bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400" },
  critical: { label: "Crítica", pdf: "CRÍTICA", color: "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400" },
};

export const statusConfig = {
  active: {
    label: "Ativa",
    pdf: "PENDENTE",
    color: "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border-red-200 dark:border-red-900/50",
  },
  acknowledged: {
    label: "Reconhecida",
    pdf: "EM ANÁLISE",
    color: "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 border-yellow-200 dark:border-yellow-900/50",
  },
  resolved: {
    label: "Resolvida",
    pdf: "RESOLVIDO",
    color: "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 border-green-200 dark:border-green-900/50",
  },
};
