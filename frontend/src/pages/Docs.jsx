import React, { useState } from "react";
import { FileText, Download, FileBarChart, HardHat, Loader2, FolderOutput } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";
import { getViolations } from "@/api/apiClient";
import { useAuth } from "@/lib/AuthContext";
import { exportCsv, exportDdsPdf, exportEvidenceZip } from "@/lib/reports";
import PageHeader from "@/components/common/PageHeader";
import { cn } from "@/lib/utils";

export default function Docs() {
  const { toast } = useToast();
  const { user } = useAuth();
  const [busy, setBusy] = useState(null); // "dds" | "csv" | "zip" | null

  // Busca os dados reais, gera o arquivo e avisa o resultado. Só um relatório por vez.
  const run = (key, generate) => async () => {
    try {
      setBusy(key);
      const violations = await getViolations();
      if (violations.length === 0) {
        toast({ title: "Nenhuma ocorrência registrada", description: "Não há dados para gerar este relatório." });
        return;
      }
      const result = await generate(violations);
      toast({
        title: "Relatório gerado com sucesso!",
        description: result?.falhas
          ? `${result.baixadas} imagem(ns) incluída(s); ${result.falhas} indisponível(is).`
          : "O download começará automaticamente.",
      });
    } catch (error) {
      console.error("Erro ao gerar relatório:", error);
      toast({ title: "Erro ao gerar relatório", description: error.message, variant: "destructive" });
    } finally {
      setBusy(null);
    }
  };

  const reports = [
    {
      key: "dds",
      code: "01",
      icon: FileText,
      title: "Pauta para DDS",
      text: "Resumo estatístico das violações recentes, em PDF, para embasar o Diálogo Diário de Segurança com os operários no canteiro.",
      cta: "Baixar PDF",
      working: "Gerando PDF...",
      tone: { bar: "bg-info", chip: "bg-info text-info-foreground", btn: "bg-info text-info-foreground hover:bg-info/90" },
      onClick: run("dds", (violations) => exportDdsPdf(violations, user.role)),
    },
    {
      key: "csv",
      code: "02",
      icon: FileBarChart,
      title: "Auditoria mensal",
      text: "Planilha completa (CSV, abre direto no Excel) com todas as ocorrências por zona, tipo e status. Ideal para cruzar dados e apresentar à diretoria.",
      cta: "Exportar Excel (CSV)",
      working: "Gerando planilha...",
      tone: { bar: "bg-success", chip: "bg-success text-success-foreground", btn: "bg-success text-success-foreground hover:bg-success/90" },
      onClick: run("csv", async (violations) => exportCsv(violations)),
    },
    {
      key: "zip",
      code: "03",
      icon: HardHat,
      title: "Backup de evidências",
      text: "Pacote ZIP com as imagens reais das 50 infrações mais recentes e a planilha correspondente, para respaldo jurídico e armazenamento frio.",
      cta: "Gerar arquivo ZIP",
      working: "Baixando imagens...",
      tone: { bar: "bg-signal", chip: "bg-signal text-signal-foreground", btn: "bg-signal text-signal-foreground hover:bg-signal/90" },
      onClick: run("zip", exportEvidenceZip),
    },
  ];

  return (
    <div className="animate-in fade-in space-y-8 duration-500">
      <PageHeader
        code="05"
        icon={FolderOutput}
        title="Central de relatórios"
        description="Documentos oficiais, planilhas de conformidade e histórico de ocorrências para auditorias (NR-06 e NR-18) e reuniões da CIPA."
      >
        <span className="flex items-center gap-2 border border-border bg-card px-3 py-2 font-mono text-[11px] font-semibold uppercase tracking-wider text-success">
          <span className="led led-pulse" /> Exportação ativa
        </span>
      </PageHeader>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {reports.map((report) => (
          <article key={report.key} className="panel group relative flex flex-col overflow-hidden transition-colors hover:border-foreground/40">
            <span className={cn("absolute inset-x-0 top-0 h-1.5", report.tone.bar)} aria-hidden />

            <div className="flex items-start justify-between p-6 pt-8">
              <span className="display text-7xl leading-none text-foreground/10 transition-colors group-hover:text-foreground/20">{report.code}</span>
              <div className={cn("chamfer flex h-14 w-14 items-center justify-center", report.tone.chip)}>
                <report.icon className="h-7 w-7" strokeWidth={2.25} />
              </div>
            </div>

            <div className="flex flex-1 flex-col px-6 pb-6">
              <h2 className="display text-3xl text-foreground">{report.title}</h2>
              <p className="mb-8 mt-3 flex-1 text-sm leading-relaxed text-muted-foreground">{report.text}</p>
              <button
                type="button"
                onClick={report.onClick}
                disabled={busy !== null}
                className={cn(
                  "flex h-12 w-full items-center justify-center gap-2 font-mono text-xs font-bold uppercase tracking-wider transition-all disabled:cursor-not-allowed disabled:opacity-50",
                  report.tone.btn
                )}
              >
                {busy === report.key ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" /> {report.working}
                  </>
                ) : (
                  <>
                    <Download className="h-4 w-4" /> {report.cta}
                  </>
                )}
              </button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
