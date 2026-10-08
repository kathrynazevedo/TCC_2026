import React, { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateViolationStatus } from "@/api/apiClient";
import { useViolations } from "@/api/queries";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { AlertTriangle, CheckCircle, Eye, Filter } from "lucide-react";
import { cn } from "@/lib/utils";
import { useToast } from "@/components/ui/use-toast";
import ApiErrorNotice from "@/components/common/ApiErrorNotice";
import EvidenceModal from "@/components/common/EvidenceModal";
import { formatDateTime } from "@/lib/format";
import { typeLabel, severityConfig, statusConfig } from "@/lib/violationLabels";

const itemClass = "cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700 dark:focus:bg-slate-700";
const triggerClass = "w-44 bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 dark:text-slate-200";
const headClass = "font-semibold text-slate-700 dark:text-slate-300";

export default function Violations() {
  const [filterZone, setFilterZone] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");
  const [selectedImage, setSelectedImage] = useState(null);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: violations = [], error } = useViolations();

  // As opções do filtro vêm dos dados reais, não de uma lista fixa no código.
  const zones = useMemo(() => [...new Set(violations.map((v) => v.zone))].sort(), [violations]);

  const updateMutation = useMutation({
    mutationFn: ({ id, status }) => updateViolationStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["violations"] });
      queryClient.invalidateQueries({ queryKey: ["metrics"] });
      toast({ title: "Status atualizado com sucesso" });
    },
    onError: (err) => toast({ title: "Não foi possível atualizar o status", description: err.message, variant: "destructive" }),
  });

  const filtered = violations.filter((v) => {
    if (filterZone !== "all" && v.zone !== filterZone) return false;
    if (filterStatus !== "all" && v.status !== filterStatus) return false;
    return true;
  });

  return (
    <div className="space-y-6 max-w-[1400px] mx-auto animate-in fade-in duration-500 relative">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Registro de Violações</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Histórico completo de detecções de não conformidade via Visão Computacional</p>
      </div>

      <ApiErrorNotice error={error} />

      <div className="flex flex-wrap gap-3 items-center bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm transition-colors">
        <Filter className="w-4 h-4 text-slate-400" />

        <Select onValueChange={setFilterZone} value={filterZone}>
          <SelectTrigger className={triggerClass} aria-label="Filtrar por zona">
            <SelectValue placeholder="Filtrar Zona" />
          </SelectTrigger>
          <SelectContent className="bg-white dark:bg-slate-800 z-50 border-slate-200 dark:border-slate-700 shadow-lg">
            <SelectItem className={itemClass} value="all">Todas Zonas</SelectItem>
            {zones.map((zone) => (
              <SelectItem key={zone} className={itemClass} value={zone}>{zone}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select onValueChange={setFilterStatus} value={filterStatus}>
          <SelectTrigger className={triggerClass} aria-label="Filtrar por status">
            <SelectValue placeholder="Filtrar Status" />
          </SelectTrigger>
          <SelectContent className="bg-white dark:bg-slate-800 z-50 border-slate-200 dark:border-slate-700 shadow-lg">
            <SelectItem className={itemClass} value="all">Todos Status</SelectItem>
            <SelectItem className={itemClass} value="active">Ativas</SelectItem>
            <SelectItem className={itemClass} value="acknowledged">Reconhecidas</SelectItem>
            <SelectItem className={itemClass} value="resolved">Resolvidas</SelectItem>
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
                <TableHead className={headClass}>Data/Hora</TableHead>
                <TableHead className={headClass}>Zona</TableHead>
                <TableHead className={headClass}>Tipo</TableHead>
                <TableHead className={headClass}>Confiança</TableHead>
                <TableHead className={headClass}>Severidade</TableHead>
                <TableHead className={headClass}>Status</TableHead>
                <TableHead className={cn(headClass, "text-right pr-6")}>Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((v) => {
                const severity = severityConfig[v.severity] || severityConfig.medium;
                const status = statusConfig[v.status] || statusConfig.active;
                const confidence = v.confidence === null || v.confidence === undefined ? null : Math.round(Number(v.confidence) * 100);

                return (
                  <TableRow className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors border-b border-slate-100 dark:border-slate-800" key={v.id}>
                    <TableCell className="font-mono text-xs text-slate-600 dark:text-slate-400">{formatDateTime(v.detected_at)}</TableCell>
                    <TableCell>
                      <Badge className="text-xs font-medium bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 dark:border-slate-600" variant="outline">
                        {v.zone}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm font-medium text-slate-900 dark:text-slate-200">{typeLabel(v.type)}</TableCell>
                    <TableCell className="font-mono text-xs text-slate-600 dark:text-slate-400">{confidence === null ? "-" : `${confidence}%`}</TableCell>
                    <TableCell>
                      <Badge className={cn("border-none text-xs", severity.color)}>{severity.label}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={cn("border text-[10px] tracking-wider uppercase", status.color)}>{status.label}</Badge>
                    </TableCell>
                    <TableCell className="text-right pr-4">
                      <div className="flex gap-2 justify-end">
                        <Button
                          onClick={() => setSelectedImage(v.imagem_url)}
                          disabled={!v.imagem_url}
                          size="sm"
                          variant="outline"
                          className="text-xs h-8 bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-900/50 transition-colors"
                        >
                          <Eye className="w-3 h-3 mr-1.5" /> Evidência
                        </Button>
                        {v.status === "active" && (
                          <Button
                            onClick={() => updateMutation.mutate({ id: v.id, status: "acknowledged" })}
                            disabled={updateMutation.isPending}
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
                            disabled={updateMutation.isPending}
                            size="sm"
                            className="text-xs h-8 bg-green-600 hover:bg-green-700 text-white border-none"
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
                  <TableCell className="text-center py-16 text-slate-500 dark:text-slate-400" colSpan={7}>
                    <div className="w-16 h-16 bg-blue-50 dark:bg-blue-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
                      <AlertTriangle className="w-8 h-8 text-blue-400 dark:text-blue-500" />
                    </div>
                    <p className="text-lg font-medium text-slate-600 dark:text-slate-300">Nenhuma violação encontrada</p>
                    <p className="text-sm mt-1">{violations.length > 0 ? "Tente ajustar os filtros de busca." : "Nenhuma infração foi registrada ainda."}</p>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      <EvidenceModal src={selectedImage} onClose={() => setSelectedImage(null)} />
    </div>
  );
}
