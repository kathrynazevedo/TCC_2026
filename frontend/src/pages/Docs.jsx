import React, { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileText, Download, FileBarChart, HardHat, Loader2, CheckCircle } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";
import { getViolations } from "@/api/apiClient";
import { useAuth } from "@/lib/AuthContext";
import { exportCsv, exportDdsPdf, exportEvidenceZip } from "@/lib/reports";

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
        className: "bg-green-50 border-green-200 text-green-900",
      });
    } catch (error) {
      console.error("Erro ao gerar relatório:", error);
      toast({ title: "Erro ao gerar relatório", description: error.message, variant: "destructive" });
    } finally {
      setBusy(null);
    }
  };

  const handleGenerateDDS = run("dds", (violations) => exportDdsPdf(violations, user.role));
  const handleExportCsv = run("csv", async (violations) => exportCsv(violations));
  const handleExportZip = run("zip", exportEvidenceZip);

  return (
    <div className="space-y-8 max-w-[1200px] mx-auto animate-in fade-in duration-500">
      
      <div className="bg-gradient-to-r from-slate-900 to-slate-800 rounded-2xl p-8 shadow-lg text-white flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <FileText className="w-8 h-8 text-blue-400" />
            Central de Relatórios
          </h1>
          <p className="text-slate-300 mt-2 text-sm max-w-xl leading-relaxed">
            Geração de documentos oficiais, planilhas de conformidade e histórico de ocorrências para apresentação em auditorias (NR-06 e NR-18) e reuniões da CIPA.
          </p>
        </div>
        <div className="bg-white/10 p-4 rounded-xl backdrop-blur-sm border border-white/10 hidden md:block">
          <p className="text-xs text-slate-300 font-mono uppercase tracking-wider mb-1">Status do Módulo</p>
          <div className="flex items-center gap-2 text-sm font-semibold text-green-400">
            <CheckCircle className="w-4 h-4" /> Exportação Ativa
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Card 1 */}
        <Card className="group relative overflow-hidden border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:shadow-xl hover:border-blue-300 dark:hover:border-blue-500 transition-all duration-300 flex flex-col">
          <div className="absolute top-0 left-0 w-full h-1 bg-blue-500 transform origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300" />
          <CardContent className="p-8 flex flex-col items-center text-center flex-1">
            <div className="w-20 h-20 rounded-2xl bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center mb-6 group-hover:scale-110 group-hover:bg-blue-100 dark:group-hover:bg-blue-900/40 transition-all duration-300 shadow-inner">
              <FileText className="w-10 h-10 text-blue-600 dark:text-blue-400" />
            </div>
            <h3 className="font-bold text-slate-900 dark:text-slate-100 text-xl mb-2">Pauta para DDS</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-8 flex-1 leading-relaxed">
              Resumo estatístico das violações recentes, pronto em formato PDF para embasar o Diálogo Diário de Segurança com os operários no canteiro.
            </p>
            <Button 
              onClick={handleGenerateDDS} 
              disabled={busy !== null}
              className={`w-full text-white shadow-md transition-all ${busy === "dds" ? 'bg-blue-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 hover:-translate-y-0.5'}`}
            >
              {busy === "dds" ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Gerando PDF...</>
              ) : (
                <><Download className="w-4 h-4 mr-2" /> Baixar PDF</>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Card 2 */}
        <Card className="group relative overflow-hidden border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:shadow-xl hover:border-green-300 dark:hover:border-green-500 transition-all duration-300 flex flex-col">
          <div className="absolute top-0 left-0 w-full h-1 bg-green-500 transform origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300" />
          <CardContent className="p-8 flex flex-col items-center text-center flex-1">
            <div className="w-20 h-20 rounded-2xl bg-green-50 dark:bg-green-900/20 flex items-center justify-center mb-6 group-hover:scale-110 group-hover:bg-green-100 dark:group-hover:bg-green-900/40 transition-all duration-300 shadow-inner">
              <FileBarChart className="w-10 h-10 text-green-600 dark:text-green-400" />
            </div>
            <h3 className="font-bold text-slate-900 dark:text-slate-100 text-xl mb-2">Auditoria Mensal</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-8 flex-1 leading-relaxed">
              Planilha completa (CSV, abre direto no Excel) com todas as ocorrências por zona, tipo e status. Ideal para cruzamento de dados e apresentação gerencial à diretoria.
            </p>
            <Button
              onClick={handleExportCsv}
              disabled={busy !== null}
              variant="outline"
              className="w-full text-green-700 dark:text-green-400 border-green-200 dark:border-green-900/50 hover:bg-green-50 dark:hover:bg-green-900/20 bg-transparent transition-all"
            >
              {busy === "csv" ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Gerando planilha...</>
              ) : (
                <><Download className="w-4 h-4 mr-2" /> Exportar Excel (CSV)</>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Card 3 */}
        <Card className="group relative overflow-hidden border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:shadow-xl hover:border-orange-300 dark:hover:border-orange-500 transition-all duration-300 flex flex-col">
          <div className="absolute top-0 left-0 w-full h-1 bg-orange-500 transform origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300" />
          <CardContent className="p-8 flex flex-col items-center text-center flex-1">
            <div className="w-20 h-20 rounded-2xl bg-orange-50 dark:bg-orange-900/20 flex items-center justify-center mb-6 group-hover:scale-110 group-hover:bg-orange-100 dark:group-hover:bg-orange-900/40 transition-all duration-300 shadow-inner">
              <HardHat className="w-10 h-10 text-orange-600 dark:text-orange-400" />
            </div>
            <h3 className="font-bold text-slate-900 dark:text-slate-100 text-xl mb-2">Backup de Evidências</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-8 flex-1 leading-relaxed">
              Baixe um pacote ZIP com as imagens reais das 50 infrações mais recentes e a planilha correspondente, para respaldo jurídico e armazenamento frio.
            </p>
            <Button
              onClick={handleExportZip}
              disabled={busy !== null}
              variant="outline"
              className="w-full text-orange-700 dark:text-orange-400 border-orange-200 dark:border-orange-900/50 hover:bg-orange-50 dark:hover:bg-orange-900/20 bg-transparent transition-all"
            >
              {busy === "zip" ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Baixando imagens...</>
              ) : (
                <><Download className="w-4 h-4 mr-2" /> Gerar Arquivo ZIP</>
              )}
            </Button>
          </CardContent>
        </Card>

      </div>
    </div>
  );
}