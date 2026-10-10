// Rótulos compartilhados por todas as telas. Os códigos ("no-helmet", "active"...) vêm da API.

const TYPES = {
  "no-helmet": { short: "Sem Capacete", alert: "Falta de Capacete", long: "Ausência de Capacete" },
  "no-vest": { short: "Sem Colete", alert: "Falta de Colete", long: "Ausência de Colete" },
  // Um registro só (mesma pessoa/quadro sem capacete E sem colete), não dois.
  "no-helmet-no-vest": { short: "Sem Capacete e Colete", alert: "Falta de Capacete e Colete", long: "Ausência de Capacete e Colete" },
};
const UNKNOWN_TYPE = { short: "Ausência de EPI", alert: "Falta de EPI", long: "Ausência de EPI" };

/** O registro envolve capacete ausente? (inclui o tipo "ambos") */
export const lacksHelmet = (type) => type === "no-helmet" || type === "no-helmet-no-vest";
/** O registro envolve colete ausente? (inclui o tipo "ambos") */
export const lacksVest = (type) => type === "no-vest" || type === "no-helmet-no-vest";

/** kind: "short" | "alert" | "long" */
export const typeLabel = (type, kind = "short") => (TYPES[type] || UNKNOWN_TYPE)[kind];

/** "Pessoa 2 de 3" quando a infração veio de uma ocorrência (cena completa); "" nos registros antigos. */
export const personLabel = (v) => {
  if (v?.person_number === null || v?.person_number === undefined) return "";
  return v.people_total ? `Pessoa ${v.person_number} de ${v.people_total}` : `Pessoa ${v.person_number}`;
};

// "color" usa os tokens do tema (claro/escuro), não cores fixas.

/** Estado de um EPI de uma pessoa na cena, como a placa o enviou. */
export const epiStateConfig = {
  ok: { label: "OK", color: "border-success/50 bg-success/10 text-success" },
  ausente: { label: "Ausente", color: "border-destructive/50 bg-destructive/10 text-destructive" },
  desconhecido: { label: "Não detectado", color: "border-border bg-muted text-muted-foreground" },
};

export const statusConfig = {
  active: { label: "Ativa", pdf: "PENDENTE", color: "border-destructive/50 bg-destructive/10 text-destructive" },
  acknowledged: { label: "Reconhecida", pdf: "EM ANÁLISE", color: "border-warning/50 bg-warning/10 text-warning" },
  resolved: { label: "Resolvida", pdf: "RESOLVIDO", color: "border-success/50 bg-success/10 text-success" },
};
