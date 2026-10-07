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
  low: { label: "Baixa", color: "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300" },
  medium: { label: "Média", color: "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400" },
  high: { label: "Alta", color: "bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400" },
  critical: { label: "Crítica", color: "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400" },
};

const statusLabels = {
  active: { label: "Ativa", color: "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border-red-200 dark:border-red-900/50" },
  acknowledged: { label: "Reconhecida", color: "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 border-yellow-200 dark:border-yellow-900/50" },
  resolved: { label: "Resolvida", color: "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 border-green-200 dark:border-green-900/50" },
};

export default function Violations() {
  const [filterZone, setFilterZone] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");
  const [selectedImage, setSelectedImage] = useState(null);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: violations = [] } = useQuery({ queryKey: ["violations"], queryFn: getViolations });

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
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Registro de Violações</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Histórico completo de detecções de não conformidade via Visão Computacional</p>
      </div>

      <div className="flex flex-wrap gap-3 items-center bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm transition-colors">
        <Filter className="w-4 h-4 text-slate-400"/>
        
        <Select onValueChange={setFilterZone} value={filterZone}>
          <SelectTrigger className="w-40 bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 dark:text-slate-200">
            <SelectValue placeholder="Filtrar Zona"/>
          </SelectTrigger>
          <SelectContent className="bg-white dark:bg-slate-800 z-50 border-slate-200 dark:border-slate-700 shadow-lg">
            <SelectItem className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700 dark:focus:bg-slate-700" value="all">Todas Zonas</SelectItem>
            <SelectItem className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700 dark:focus:bg-slate-700" value="Norte">Zona Norte</SelectItem>
            <SelectItem className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700 dark:focus:bg-slate-700" value="Central">Canteiro Central</SelectItem>
            <SelectItem className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700 dark:focus:bg-slate-700" value="Almoxarifado">Almoxarifado</SelectItem>
          </SelectContent>
        </Select>

        <Select onValueChange={setFilterStatus} value={filterStatus}>
          <SelectTrigger className="w-40 bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 dark:text-slate-200">
            <SelectValue placeholder="Filtrar Status"/>
          </SelectTrigger>
          <SelectContent className="bg-white dark:bg-slate-800 z-50 border-slate-200 dark:border-slate-700 shadow-lg">
            <SelectItem className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700 dark:focus:bg-slate-700" value="all">Todos Status</SelectItem>
            <SelectItem className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700 dark:focus:bg-slate-700" value="active">Ativas</SelectItem>
            <SelectItem className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700 dark:focus:bg-slate-700" value="acknowledged">Reconhecidas</SelectItem>
            <SelectItem className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700 dark:focus:bg-slate-700" value="resolved">Resolvidas</SelectItem>
          </SelectContent>
        </Select>

        <Badge className="ml-auto font-mono text-xs bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400" variant="secondary">
          {filtered.length} resultado(s)
        </Badge>
      </div>

      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm transition-colors">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50">
                <TableHead className="font-semibold text-slate-700 dark:text-slate-300">Data/Hora</TableHead>
                <TableHead className="font-semibold text-slate-700 dark:text-slate-300">Zona</TableHead>
                <TableHead className="font-semibold text-slate-700 dark:text-slate-300">Tipo</TableHead>
                <TableHead className="font-semibold text-slate-700 dark:text-slate-300">Severidade</TableHead>
                <TableHead className="font-semibold text-slate-700 dark:text-slate-300">Status</TableHead>
                <TableHead className="font-semibold text-slate-700 dark:text-slate-300 text-right pr-6">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((v) => {
                const severity = severityConfig[v.severity] || severityConfig.medium;
                const status = statusLabels[v.status] || statusLabels.active;

                return (
                  <TableRow className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors border-b border-slate-100 dark:border-slate-800" key={v.id}>
                    <TableCell className="font-mono text-xs text-slate-600 dark:text-slate-400">
                      {v.detected_at ? moment(v.detected_at).format("DD/MM/YY HH:mm") : "-"}
                    </TableCell>
                    <TableCell>
                      <Badge className="text-xs font-medium bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 dark:border-slate-600" variant="outline">
                        {v.zone}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm font-medium text-slate-900 dark:text-slate-200">
                      {typeLabels[v.type] || v.type}
                    </TableCell>
                    <TableCell>
                      <Badge className={cn("border-none text-xs", severity.color)}>{severity.label}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={cn("border text-[10px] tracking-wider uppercase", status.color)}>
                        {status.label}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right pr-4">
                      <div className="flex gap-2 justify-end">
                        <Button 
                          onClick={() => setSelectedImage(v.imagem_url)} 
                          size="sm" 
                          variant="outline"
                          className="text-xs h-8 bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-900/50 transition-colors"
                        >
                          <Eye className="w-3 h-3 mr-1.5"/> Evidência
                        </Button>
                        {v.status === "active" && (
                          <Button 
                            onClick={() => updateMutation.mutate({ id: v.id, status: "acknowledged" })} 
                            size="sm" 
                            variant="outline"
                            className="text-xs h-8 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 dark:border-slate-700"
                          >
                            Analisar
                          </Button>
                        )}
                        {v.status !== "resolved" && (
                          <Button 
                            onClick={() => updateMutation.mutate({ id: v.id, status: "resolved" })} 
                            size="sm"
                            className="text-xs h-8 bg-green-600 dark:bg-green-600 hover:bg-green-700 dark:hover:bg-green-700 text-white border-none"
                          >
                            <CheckCircle className="w-3 h-3 mr-1.5"/> Resolver
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
              {filtered.length === 0 && (
                <TableRow>
                  <TableCell className="text-center py-16 text-slate-500 dark:text-slate-400" colSpan={6}>
                    <div className="w-16 h-16 bg-blue-50 dark:bg-blue-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
                      <AlertTriangle className="w-8 h-8 text-blue-400 dark:text-blue-500"/>
                    </div>
                    <p className="text-lg font-medium text-slate-600 dark:text-slate-300">Nenhuma violação encontrada</p>
                    <p className="text-sm mt-1">Tente ajustar os filtros de busca.</p>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      {selectedImage && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/80 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="relative bg-white dark:bg-slate-900 rounded-xl shadow-2xl max-w-4xl w-full overflow-hidden border border-slate-200 dark:border-slate-800">
            <div className="flex justify-between items-center p-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
              <h3 className="font-bold text-slate-800 dark:text-slate-200 flex items-center gap-2">
                <Eye className="w-5 h-5 text-blue-600 dark:text-blue-400"/>
                Captura da Infração
              </h3>
              <button onClick={() => setSelectedImage(null)} className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-full transition-colors text-slate-500 dark:text-slate-400">
                <X className="w-5 h-5"/>
              </button>
            </div>
            <div className="bg-slate-100 dark:bg-black/50 flex items-center justify-center p-4 min-h-[400px]">
              {selectedImage ? (
                <img src={selectedImage} alt="Registro gerado pelo YOLO" className="w-full h-auto max-h-[70vh] object-contain rounded shadow-sm" />
              ) : (
                <div className="flex flex-col items-center text-slate-500 dark:text-slate-400 py-12">
                  <AlertTriangle className="w-12 h-12 mb-3 opacity-30"/>
                  <p className="font-medium text-lg">Arquivo de imagem não anexado.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}