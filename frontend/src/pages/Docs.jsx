import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileText, Download, FileBarChart, HardHat } from "lucide-react";

export default function Docs() {
  return (
    <div className="space-y-6 max-w-[1200px] mx-auto animate-in fade-in duration-500">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Relatórios de Conformidade</h1>
        <p className="text-sm text-slate-500 mt-1">Geração de documentos para auditoria (NR-06 e NR-18)</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="hover:border-blue-400 hover:shadow-md transition-all cursor-pointer border-slate-200 bg-white group">
          <CardContent className="p-6 flex flex-col items-center text-center h-full">
            <div className="w-16 h-16 rounded-2xl bg-blue-50 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <FileText className="w-8 h-8 text-blue-600" />
            </div>
            <h3 className="font-bold text-slate-800 text-lg">Pauta para DDS</h3>
            <p className="text-xs text-slate-500 mt-2 mb-6 flex-1">
              Resumo estatístico das últimas 24h para embasar o Diálogo Diário de Segurança com os operários.
            </p>
            <Button className="w-full bg-blue-600 hover:bg-blue-700 text-white">
              <Download className="w-4 h-4 mr-2" /> Baixar PDF
            </Button>
          </CardContent>
        </Card>

        <Card className="hover:border-green-400 hover:shadow-md transition-all cursor-pointer border-slate-200 bg-white group">
          <CardContent className="p-6 flex flex-col items-center text-center h-full">
            <div className="w-16 h-16 rounded-2xl bg-green-50 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <FileBarChart className="w-8 h-8 text-green-600" />
            </div>
            <h3 className="font-bold text-slate-800 text-lg">Auditoria Mensal</h3>
            <p className="text-xs text-slate-500 mt-2 mb-6 flex-1">
              Planilha detalhada de conformidade por setor, ideal para apresentação à diretoria e CIPA.
            </p>
            <Button className="w-full bg-green-600 hover:bg-green-700 text-white">
              <Download className="w-4 h-4 mr-2" /> Exportar Excel
            </Button>
          </CardContent>
        </Card>

        <Card className="hover:border-orange-400 hover:shadow-md transition-all cursor-pointer border-slate-200 bg-white group">
          <CardContent className="p-6 flex flex-col items-center text-center h-full">
            <div className="w-16 h-16 rounded-2xl bg-orange-50 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <HardHat className="w-8 h-8 text-orange-600" />
            </div>
            <h3 className="font-bold text-slate-800 text-lg">Histórico de EPIs</h3>
            <p className="text-xs text-slate-500 mt-2 mb-6 flex-1">
              Registro completo de imagens e logs das infrações detectadas pelo sistema de Visão Computacional.
            </p>
            <Button variant="outline" className="w-full text-orange-600 border-orange-200 hover:bg-orange-50 bg-white">
              <Download className="w-4 h-4 mr-2" /> Gerar Arquivo ZIP
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}