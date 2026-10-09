import { format } from "date-fns";
import { formatDateTime } from "@/lib/format";
import { typeLabel, severityConfig, statusConfig } from "@/lib/violationLabels";

function download(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

const today = () => format(new Date(), "dd-MM-yyyy");

// ---------------------------------------------------------------- CSV (abre direto no Excel)
// Escapa aspas e neutraliza fórmulas (=, +, -, @) para a planilha não executar conteúdo.
const csvCell = (value) => {
  let text = value === null || value === undefined ? "" : String(value);
  if (/^[=+\-@]/.test(text)) text = `'${text}`;
  return `"${text.replace(/"/g, '""')}"`;
};

export function buildCsv(violations) {
  const header = ["ID", "Data/Hora", "Zona", "Tipo", "Confiança (%)", "Severidade", "Status", "Evidência (URL)"];
  const rows = violations.map((v) => [
    v.id,
    formatDateTime(v.detected_at, "dd/MM/yyyy HH:mm:ss"),
    v.zone,
    typeLabel(v.type, "long"),
    v.confidence === null || v.confidence === undefined ? "" : Math.round(Number(v.confidence) * 100),
    (severityConfig[v.severity] || severityConfig.high).label,
    (statusConfig[v.status] || statusConfig.active).label,
    v.imagem_url || "",
  ]);
  // Separador ";" e BOM UTF-8: é o que o Excel em português espera para abrir com acentos corretos.
  return "﻿" + [header, ...rows].map((row) => row.map(csvCell).join(";")).join("\r\n");
}

export function exportCsv(violations) {
  download(new Blob([buildCsv(violations)], { type: "text/csv;charset=utf-8" }), `SafeWork_Auditoria_${today()}.csv`);
}

// ---------------------------------------------------------------- PDF (pauta do DDS)
export async function exportDdsPdf(violations, responsavel) {
  // Carregadas sob demanda: as bibliotecas de PDF são pesadas e só importam neste clique.
  const [{ jsPDF }, { default: autoTable }] = await Promise.all([import("jspdf"), import("jspdf-autotable")]);

  const doc = new jsPDF();
  doc.setFontSize(22);
  doc.setTextColor(30, 41, 59);
  doc.text("SafeWork - Relatório de Auditoria (DDS)", 14, 22);

  doc.setFontSize(11);
  doc.setTextColor(100, 116, 139);
  doc.text(`Data de Emissão: ${format(new Date(), "dd/MM/yyyy HH:mm")}`, 14, 30);
  doc.text(`Responsável: ${responsavel}`, 14, 36);

  const count = (predicate) => violations.filter(predicate).length;
  doc.text(
    `Total: ${violations.length}   |   Pendentes: ${count((v) => v.status === "active")}   |   ` +
      `Sem capacete: ${count((v) => v.type === "no-helmet")}   |   Sem colete: ${count((v) => v.type === "no-vest")}`,
    14,
    43
  );
  doc.setDrawColor(226, 232, 240);
  doc.line(14, 48, 196, 48);

  autoTable(doc, {
    startY: 54,
    head: [["Data / Hora", "Zona de Risco", "Tipo de Infração", "Severidade", "Status"]],
    body: violations.slice(0, 40).map((v) => [
      formatDateTime(v.detected_at, "dd/MM/yyyy HH:mm"),
      v.zone || "Geral",
      typeLabel(v.type, "long"),
      (severityConfig[v.severity] || severityConfig.high).pdf,
      (statusConfig[v.status] || statusConfig.active).pdf,
    ]),
    theme: "grid",
    headStyles: { fillColor: [37, 99, 235], textColor: 255, fontStyle: "bold" },
    alternateRowStyles: { fillColor: [248, 250, 252] },
    styles: { fontSize: 9, cellPadding: 4 },
    didDrawPage: (data) => {
      doc.setFontSize(8);
      doc.setTextColor(148, 163, 184);
      doc.text(
        `SafeWork - Visão Computacional para Segurança do Trabalho - Página ${doc.internal.getNumberOfPages()}`,
        data.settings.margin.left,
        doc.internal.pageSize.height - 10
      );
    },
  });

  if (violations.length > 40) {
    doc.setFontSize(9);
    doc.setTextColor(100, 116, 139);
    doc.text(`Exibindo as 40 ocorrências mais recentes de ${violations.length}.`, 14, doc.lastAutoTable.finalY + 8);
  }

  doc.save(`SafeWork_DDS_${today()}.pdf`);
}

// ---------------------------------------------------------------- ZIP (backup de evidências)
const MAX_EVIDENCE = 50;

/** Devolve { baixadas, falhas }. Lança erro se nenhuma imagem puder ser baixada. */
export async function exportEvidenceZip(violations) {
  const { default: JSZip } = await import("jszip");
  const withImage = violations.filter((v) => v.imagem_url).slice(0, MAX_EVIDENCE);
  if (withImage.length === 0) throw new Error("Nenhuma ocorrência possui imagem de evidência.");

  const zip = new JSZip();
  let baixadas = 0;

  // Em lotes pequenos para não saturar a conexão nem o navegador.
  for (let i = 0; i < withImage.length; i += 5) {
    await Promise.all(
      withImage.slice(i, i + 5).map(async (v) => {
        try {
          const response = await fetch(v.imagem_url);
          if (!response.ok) throw new Error(String(response.status));
          const stamp = formatDateTime(v.detected_at, "yyyyMMdd_HHmmss");
          zip.file(`infracao_${v.id}_${v.type}_${stamp}.jpg`, await response.blob());
          baixadas += 1;
        } catch {
          // imagem indisponível: segue com as demais
        }
      })
    );
  }

  if (baixadas === 0) throw new Error("Não foi possível baixar as imagens (verifique a conexão e o acesso ao Cloudinary).");

  zip.file("ocorrencias.csv", buildCsv(violations));
  download(await zip.generateAsync({ type: "blob" }), `SafeWork_Evidencias_${today()}.zip`);
  return { baixadas, falhas: withImage.length - baixadas };
}
