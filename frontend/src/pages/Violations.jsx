import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getViolations, updateViolationStatus } from "@/api/apiClient";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { AlertTriangle, CheckCircle, Eye, Filter, X } from "lucide-react";
import { cn } from "@/lib/utils";
import moment from "moment";
import { useToast } from "@/components/ui/use-toast";

const typeLabels = {
  "no-helmet": "Sem Capacete",
  "no-vest": "Sem Colete",
  "person": "Pessoa Detectada",
};

const severityConfig = {
  low: { label: "Baixa", color: "bg-slate-100 text-slate-600" },
  medium: { label: "Média", color: "bg-yellow-100 text-yellow-700" },
  high: { label: "Alta", color: "bg-orange-100 text-orange-700" },
  critical: { label: "Crítica", color: "bg-red-100 text-red-700" },
};

const statusLabels = {
  active: { label: "Ativa", color: "bg-red-100 text-red-700 border-red-200" },
  acknowledged: { label: "Reconhecida", color: "bg-yellow-100 text-yellow-700 border-yellow-200" },
  resolved: { label: "Resolvida", color: "bg-green-100 text-green-700 border-green-200" },
};

export default function Violations() {
  const [filterZone, setFilterZone] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");
  const [selectedImage, setSelectedImage] = useState(null); // Estado para controlar o modal da imagem

  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: violations = [] } = useQuery({
    queryKey: ["violations"],
    queryFn: getViolations,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, status }) => updateViolationStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["violations"] });
      toast({ title: "Status atualizado com sucesso" });
    },
  });

  const filtered = violations.filter(v => {
    if (filterZone !== "all" && !v.zone.includes(filterZone)) return false;
    if (filterStatus !== "all" && v.status !== filterStatus) return false;
    return true;
  });

  return (
    <div className="space-y-6 max-w-[1400px] mx-auto animate-in fade-in duration-500 relative">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Registro de Violações</h1>
        <p className="text-sm text-slate-500 mt-1">Histórico completo de detecções de não conformidade via Visão Computacional</p>
      </div>

      <div className="flex flex-wrap gap-3 items-center bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <Filter className="w-4 h-4 text-slate-400" />
        
        <Select value={filterZone} onValueChange={setFilterZone}>
          <SelectTrigger className="w-40 bg-white border-slate-200">
            <SelectValue placeholder="Filtrar Zona" />
          </SelectTrigger>
          <SelectContent className="bg-white z-50 border-slate-200 shadow-lg">
            <SelectItem value="all" className="cursor-pointer hover:bg-slate-50">Todas Zonas</SelectItem>
            <SelectItem value="Norte" className="cursor-pointer hover:bg-slate-50">Zona Norte</SelectItem>
            <SelectItem value="Central" className="cursor-pointer hover:bg-slate-50">Canteiro Central</SelectItem>
            <SelectItem value="Almoxarifado" className="cursor-pointer hover:bg-slate-50">Almoxarifado</SelectItem>
          </SelectContent>
        </Select>

        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectTrigger className="w-40 bg-white border-slate-200">
            <SelectValue placeholder="Filtrar Status" />
          </SelectTrigger>
          <SelectContent className="bg-white z-50 border-slate-200 shadow-lg">
            <SelectItem value="all" className="cursor-pointer hover:bg-slate-50">Todos Status</SelectItem>
            <SelectItem value="active" className="cursor-pointer hover:bg-slate-50">Ativas</SelectItem>
            <SelectItem value="acknowledged" className="cursor-pointer hover:bg-slate-50">Reconhecidas</SelectItem>
            <SelectItem value="resolved" className="cursor-pointer hover:bg-slate-50">Resolvidas</SelectItem>
          </SelectContent>
        </Select>

        <Badge variant="secondary" className="ml-auto font-mono text-xs bg-slate-100 text-slate-600">
          {filtered.length} resultado(s)
        </Badge>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="bg-slate-50 border-b border-slate-200">
                <TableHead className="font-semibold text-slate-700">Data/Hora</TableHead>
                <TableHead className="font-semibold text-slate-700">Zona</TableHead>
                <TableHead className="font-semibold text-slate-700">Tipo</TableHead>
                <TableHead className="font-semibold text-slate-700">Severidade</TableHead>
                {/* Removido TableHead de Trabalhador */}
                <TableHead className="font-semibold text-slate-700">Status</TableHead>
                <TableHead className="font-semibold text-slate-700 text-right pr-6">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((v) => {
                const severity = severityConfig[v.severity] || severityConfig.medium;
                const status = statusLabels[v.status] || statusLabels.active;
                return (
                  <TableRow key={v.id} className="hover:bg-slate-50 transition-colors border-b border-slate-100">
                    <TableCell className="font-mono text-xs text-slate-600">
                      {v.detected_at ? moment(v.detected_at).format("DD/MM/YY HH:mm") : "—"}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs font-medium bg-white text-slate-700">
                        {v.zone}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm font-medium text-slate-900">
                      {typeLabels[v.type] || v.type}
                    </TableCell>
                    <TableCell>
                      <Badge className={cn("text-xs border-none", severity.color)}>{severity.label}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={cn("text-[10px] uppercase tracking-wider", status.color)}>
                        {status.label}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right pr-4">
                      <div className="flex gap-2 justify-end">
                        
                        {/* NOVO: Botão para abrir a imagem da infração */}
                        <Button
                          variant="outline" 
                          size="sm"
                          onClick={() => setSelectedImage(v.caminho_imagem || v.imagem_url)}
                          className="text-xs h-8 bg-white hover:bg-slate-100 text-blue-600 border-blue-200 hover:text-blue-700 hover:border-blue-300 transition-colors"
                        >
                          <Eye className="w-3 h-3 mr-1.5" /> Evidência
                        </Button>

                        {v.status === "active" && (
                          <Button
                            variant="outline" size="sm"
                            onClick={() => updateMutation.mutate({ id: v.id, status: "acknowledged" })}
                            className="text-xs h-8 bg-white hover:bg-slate-50 text-slate-700"
                          >
                            Analisar
                          </Button>
                        )}
                        {v.status !== "resolved" && (
                          <Button
                            size="sm"
                            onClick={() => updateMutation.mutate({ id: v.id, status: "resolved" })}
                            className="text-xs h-8 bg-green-600 hover:bg-green-700 text-white"
                          >
                            <CheckCircle className="w-3 h-3 mr-1.5" /> Resolver
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
              {filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-16 text-slate-500">
                    <AlertTriangle className="w-10 h-10 mx-auto mb-3 opacity-20" />
                    <p className="text-lg font-medium text-slate-600">Nenhuma violação encontrada</p>
                    <p className="text-sm">Tente ajustar os filtros de busca.</p>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* MODAL DE VISUALIZAÇÃO DA FOTO */}
      {selectedImage && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="relative bg-white rounded-xl shadow-2xl max-w-4xl w-full overflow-hidden border border-slate-200">
            
            <div className="flex justify-between items-center p-4 border-b border-slate-100 bg-slate-50">
              <h3 className="font-bold text-slate-800 flex items-center gap-2">
                <Eye className="w-5 h-5 text-blue-600" />
                Captura da Infração
              </h3>
              <button 
                onClick={() => setSelectedImage(null)} 
                className="p-1.5 hover:bg-slate-200 rounded-full transition-colors text-slate-500 hover:text-slate-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="bg-slate-100 flex items-center justify-center p-4 min-h-[400px]">
              {selectedImage ? (
                <img 
                  src={selectedImage} 
                  alt="Registro gerado pelo YOLO" 
                  className="w-full h-auto max-h-[70vh] object-contain rounded shadow-sm"
                />
              ) : (
                <div className="flex flex-col items-center text-slate-500 py-12">
                  <AlertTriangle className="w-12 h-12 mb-3 opacity-30" />
                  <p className="font-medium text-lg">Arquivo de imagem não anexado.</p>
                  <p className="text-sm mt-1">A Raspberry Pi não enviou a foto desta ocorrência.</p>
                </div>
              )}
            </div>

          </div>
        </div>
      )}
    </div>
  );
}