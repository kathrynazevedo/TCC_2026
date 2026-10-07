import React, { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileText, Download, FileBarChart, HardHat, Loader2, CheckCircle } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";
import { getViolations } from "@/api/apiClient";
import jsPDF from "jspdf";
import "jspdf-autotable";
import moment from "moment";

export default function Docs() {
  const { toast } = useToast();
  const [isGeneratingDDS, setIsGeneratingDDS] = useState(false);

  // Função para gerar o Relatório PDF Real
  const handleGenerateDDS = async () => {
    try {
      setIsGeneratingDDS(true);
      
      // 1. Busca os dados reais do backend
      const violations = await getViolations();
      
      // 2. Inicializa o documento PDF
      const doc = new jsPDF();
      
      // 3. Cabeçalho do PDF (Design)
      doc.setFontSize(22);
      doc.setTextColor(30, 41, 59); // slate-800
      doc.text("SafeWork - Relatório de Auditoria (DDS)", 14, 22);
      
      doc.setFontSize(11);
      doc.setTextColor(100, 116, 139); // slate-500
      doc.text(`Data de Emissão: ${moment().format('DD/MM/YYYY HH:mm')}`, 14, 30);
      doc.text(`Responsável: Administrador do Sistema`, 14, 36);

      // Linha separadora
      doc.setDrawColor(226, 232, 240); // slate-200
      doc.line(14, 42, 196, 42);

      // 4. Preparar os dados para a tabela
      const tableData = violations.slice(0, 40).map(v => [
        moment(v.detected_at).format("DD/MM/YYYY HH:mm"),
        v.zone || "Geral",
        v.type === 'no-helmet' ? 'Ausência de Capacete' : (v.type === 'no-vest' ? 'Ausência de Colete' : v.type),
        v.severity === 'high' ? 'ALTA' : (v.severity === 'medium' ? 'MÉDIA' : 'BAIXA'),
        v.status === 'active' ? 'PENDENTE' : (v.status === 'acknowledged' ? 'EM ANÁLISE' : 'RESOLVIDO')
      ]);

      // 5. Desenhar a Tabela Profissional
      doc.autoTable({
        startY: 50,
        head: [['Data / Hora', 'Zona de Risco', 'Tipo de Infração', 'Severidade', 'Status']],
        body: tableData,
        theme: 'grid',
        headStyles: { fillColor: [37, 99, 235], textColor: 255, fontStyle: 'bold' }, // Azul do Tailwind (blue-600)
        alternateRowStyles: { fillColor: [248, 250, 252] }, // slate-50
        styles: { fontSize: 9, cellPadding: 4 },
        didDrawPage: function (data) {
          // Rodapé em todas as páginas
          doc.setFontSize(8);
          doc.setTextColor(148, 163, 184);
          doc.text(
            `SafeWork - Visão Computacional para Segurança do Trabalho - Página ${doc.internal.getNumberOfPages()}`,
            data.settings.margin.left,
            doc.internal.pageSize.height - 10
          );
        }
      });

      // 6. Salvar e baixar o arquivo
      doc.save(`SafeWork_DDS_${moment().format('DD-MM-YYYY')}.pdf`);

      // 7. Feedback de Sucesso na Interface
      toast({
        title: "Relatório gerado com sucesso!",
        description: "O download do PDF começará automaticamente.",
        className: "bg-green-50 border-green-200 text-green-900",
      });

    } catch (error) {
      console.error("Erro ao gerar PDF:", error);
      toast({
        title: "Erro ao gerar relatório",
        description: "Verifique a conexão com o servidor.",
        variant: "destructive"
      });
    } finally {
      setIsGeneratingDDS(false);
    }
  };

  return (
    <div className="space-y-8 max-w-[1200px] mx-auto animate-in fade-in duration-500">
      
      <div className="bg-gradient-to-r from-slate-900 to-slate-800 rounded-2xl p-8 shadow-lg text-white flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <FileText className="w-8 h-8 text-blue-400" />
            Central de Relatórios
          </h1>
          <p className="text-slate-300 mt-2 text-sm max-w-xl leading-relaxed">
            Geração de documentos oficias, planilhas de conformidade e histórico de ocorrências para apresentação em auditorias (NR-06 e NR-18) e reuniões da CIPA.
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
              disabled={isGeneratingDDS}
              className={`w-full text-white shadow-md transition-all ${isGeneratingDDS ? 'bg-blue-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 hover:-translate-y-0.5'}`}
            >
              {isGeneratingDDS ? (
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
              Planilha bruta (Excel/CSV) detalhada por setor e funcionário. Ideal para cruzamento de dados e apresentação gerencial à diretoria.
            </p>
            <Button variant="outline" className="w-full text-green-700 dark:text-green-400 border-green-200 dark:border-green-900/50 hover:bg-green-50 dark:hover:bg-green-900/20 bg-transparent transition-all">
              <Download className="w-4 h-4 mr-2" /> Exportar Excel
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
              Baixe um pacote criptografado contendo as imagens reais das infrações para respaldo jurídico e armazenamento frio.
            </p>
            <Button variant="outline" className="w-full text-orange-700 dark:text-orange-400 border-orange-200 dark:border-orange-900/50 hover:bg-orange-50 dark:hover:bg-orange-900/20 bg-transparent transition-all">
              <Download className="w-4 h-4 mr-2" /> Gerar Arquivo ZIP
            </Button>
          </CardContent>
        </Card>

      </div>
    </div>
  );
}