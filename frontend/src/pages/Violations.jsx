import React, { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { deleteViolations, updateViolationStatus } from "@/api/apiClient";
import { useViolations } from "@/api/queries";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { AlertOctagon, AlertTriangle, CheckCheck, CheckCircle, Eye, Filter, HardHat, MapPin, Shirt, Trash2, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useToast } from "@/components/ui/use-toast";
import ApiErrorNotice from "@/components/common/ApiErrorNotice";
import EvidenceModal from "@/components/common/EvidenceModal";
import DeleteViolationsDialog from "@/components/common/DeleteViolationsDialog";
import PageHeader from "@/components/common/PageHeader";
import StatusTag from "@/components/common/StatusTag";
import { formatDateTime } from "@/lib/format";
import { typeLabel, personLabel } from "@/lib/violationLabels";

const itemClass = "cursor-pointer font-mono text-xs uppercase tracking-wide focus:bg-accent focus:text-accent-foreground";
const triggerClass = "h-10 w-48 rounded-sm border-input bg-background font-mono text-xs uppercase tracking-wide text-foreground";
const headClass = "h-11 font-mono text-[11px] font-semibold uppercase tracking-[0.15em] text-muted-foreground";
const actionBtn = "h-8 rounded-sm font-mono text-[11px] font-semibold uppercase tracking-wider";

// Barra lateral da linha: a cor já diz a gravidade antes de ler o status.
const ROW_BAR = {
  active: "bg-destructive",
  acknowledged: "bg-warning",
  resolved: "bg-success/50",
};

// Cada tipo de EPI ausente ganha ícone e cor, para a coluna ser reconhecida de relance.
const TYPE_STYLE = {
  "no-helmet": { icons: [HardHat], color: "border-warning/50 bg-warning/10 text-warning" },
  "no-vest": { icons: [Shirt], color: "border-info/50 bg-info/10 text-info" },
  // Falta de capacete e de colete ao mesmo tempo: os dois ícones, em vermelho (mais grave).
  "no-helmet-no-vest": { icons: [HardHat, Shirt], color: "border-destructive/60 bg-destructive/15 text-destructive" },
};
const UNKNOWN_TYPE_STYLE = { icons: [AlertTriangle], color: "border-border bg-muted text-muted-foreground" };

export default function Violations() {
  const [filterZone, setFilterZone] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");
  const [evidence, setEvidence] = useState(null); // violação cuja foto/cena está aberta no modal
  const [selectedIds, setSelectedIds] = useState(() => new Set());
  const [deleteOpen, setDeleteOpen] = useState(false);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: violations = [], error } = useViolations();

  // As opções do filtro vêm dos dados reais, não de uma lista fixa no código.
  const zones = useMemo(() => [...new Set(violations.map((v) => v.zone))].sort(), [violations]);
  const pendingCount = useMemo(() => violations.filter((v) => v.status === "active").length, [violations]);

  const updateMutation = useMutation({
    mutationFn: ({ id, status }) => updateViolationStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["violations"] });
      queryClient.invalidateQueries({ queryKey: ["metrics"] });
      toast({ title: "Status atualizado com sucesso" });
    },
    onError: (err) => toast({ title: "Não foi possível atualizar o status", description: err.message, variant: "destructive" }),
  });

  const deleteMutation = useMutation({
    mutationFn: ({ ids, password }) => deleteViolations(ids, password),
    onSuccess: (result, { ids }) => {
      queryClient.invalidateQueries({ queryKey: ["violations"] });
      queryClient.invalidateQueries({ queryKey: ["metrics"] });
      setSelectedIds((prev) => {
        const next = new Set(prev);
        ids.forEach((id) => next.delete(id));
        return next;
      });
      setDeleteOpen(false);
      const total = result.deleted;
      toast({ title: total === 1 ? "1 violação excluída" : `${total} violações excluídas` });
    },
    // Erros (senha incorreta, API fora do ar) aparecem dentro do diálogo, que continua aberto.
  });

  const filtered = violations.filter((v) => {
    if (filterZone !== "all" && v.zone !== filterZone) return false;
    if (filterStatus !== "all" && v.status !== filterStatus) return false;
    return true;
  });

  // Só vale a seleção do que está visível: filtrar a lista nunca faz apagar registros escondidos.
  const selectedVisible = filtered.filter((v) => selectedIds.has(v.id)).map((v) => v.id);
  const hasSelection = selectedVisible.length > 0;
  const allSelected = filtered.length > 0 && selectedVisible.length === filtered.length;
  const someSelected = hasSelection && !allSelected;

  const toggleOne = (id, checked) =>
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });

  const toggleAll = (checked) =>
    setSelectedIds((prev) => {
      const next = new Set(prev);
      filtered.forEach((v) => (checked ? next.add(v.id) : next.delete(v.id)));
      return next;
    });

  // Atalho: marca (ou desmarca) todas as resolvidas que estão visíveis, respeitando os filtros.
  const resolvedVisible = filtered.filter((v) => v.status === "resolved").map((v) => v.id);
  const allResolvedSelected = resolvedVisible.length > 0 && resolvedVisible.every((id) => selectedIds.has(id));

  const toggleResolved = () =>
    setSelectedIds((prev) => {
      const next = new Set(prev);
      resolvedVisible.forEach((id) => (allResolvedSelected ? next.delete(id) : next.add(id)));
      return next;
    });

  const openDelete = () => {
    deleteMutation.reset();
    setDeleteOpen(true);
  };

  return (
    <div className="animate-in fade-in relative space-y-6 duration-500">
      <PageHeader
        code="02"
        icon={AlertOctagon}
        title="Registro de violações"
        description="Histórico completo de detecções de não conformidade via Visão Computacional."
      >
        <div className="flex items-stretch border border-border bg-card font-mono">
          <div className="px-4 py-2 text-right">
            <div className="display text-3xl tabular-nums text-foreground">{violations.length}</div>
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground">registros</div>
          </div>
          <div className="border-l border-border bg-destructive px-4 py-2 text-right text-destructive-foreground">
            <div className="display text-3xl tabular-nums">{pendingCount}</div>
            <div className="text-[10px] uppercase tracking-widest opacity-90">pendentes</div>
          </div>
        </div>
      </PageHeader>

      <ApiErrorNotice error={error} />

      {/* Barra de filtros e ações em lote */}
      <div className="panel flex flex-wrap items-center gap-3 p-3">
        <span className="flex items-center gap-2 pl-1 font-mono text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
          <Filter className="h-4 w-4" /> Filtros
        </span>

        <Select onValueChange={setFilterZone} value={filterZone}>
          <SelectTrigger className={triggerClass} aria-label="Filtrar por zona">
            <SelectValue placeholder="Filtrar Zona" />
          </SelectTrigger>
          <SelectContent className="z-50 rounded-sm border-border bg-popover shadow-xl">
            <SelectItem className={itemClass} value="all">Todas as zonas</SelectItem>
            {zones.map((zone) => (
              <SelectItem key={zone} className={itemClass} value={zone}>{zone}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select onValueChange={setFilterStatus} value={filterStatus}>
          <SelectTrigger className={triggerClass} aria-label="Filtrar por status">
            <SelectValue placeholder="Filtrar Status" />
          </SelectTrigger>
          <SelectContent className="z-50 rounded-sm border-border bg-popover shadow-xl">
            <SelectItem className={itemClass} value="all">Todos os status</SelectItem>
            <SelectItem className={itemClass} value="active">Ativas</SelectItem>
            <SelectItem className={itemClass} value="acknowledged">Reconhecidas</SelectItem>
            <SelectItem className={itemClass} value="resolved">Resolvidas</SelectItem>
          </SelectContent>
        </Select>

        <div className="ml-auto flex flex-wrap items-center gap-3">
          {hasSelection ? (
            <div className="flex items-center gap-1 border border-signal/60 bg-signal/10 py-1 pl-3 pr-1 font-mono text-xs font-semibold uppercase tracking-wider text-foreground">
              {selectedVisible.length} selecionada(s)
              <button
                type="button"
                onClick={() => toggleAll(false)}
                aria-label="Limpar seleção"
                className="p-1 transition-colors hover:bg-signal/20"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ) : (
            <span className="border border-border bg-background px-3 py-2 font-mono text-xs uppercase tracking-wider text-muted-foreground">
              {filtered.length} resultado(s)
            </span>
          )}

          <Button
            onClick={toggleResolved}
            disabled={resolvedVisible.length === 0}
            variant="outline"
            title={resolvedVisible.length === 0 ? "Nenhuma violação resolvida na lista atual" : undefined}
            className={cn(
              "h-10 rounded-sm font-mono text-xs font-semibold uppercase tracking-wider",
              allResolvedSelected
                ? "border-success bg-success/15 text-success hover:bg-success/25 hover:text-success"
                : "border-success/50 text-success hover:bg-success/10 hover:text-success"
            )}
          >
            <CheckCheck className="mr-2 h-4 w-4" />
            {allResolvedSelected ? "Desmarcar resolvidas" : `Selecionar resolvidas (${resolvedVisible.length})`}
          </Button>

          <Button
            onClick={openDelete}
            disabled={!hasSelection}
            aria-label="Excluir violações selecionadas"
            className={cn(
              "h-10 rounded-sm font-mono text-xs font-semibold uppercase tracking-wider",
              hasSelection
                ? "bg-destructive text-destructive-foreground hover:bg-destructive/90"
                : "bg-muted text-muted-foreground"
            )}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            {hasSelection ? `Excluir (${selectedVisible.length})` : "Excluir"}
          </Button>
        </div>
      </div>

      {/* Tabela */}
      <div className="panel overflow-hidden">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="border-b border-border bg-surface hover:bg-surface">
                <TableHead className="w-14 pl-5 pr-0">
                  <Checkbox
                    checked={allSelected ? true : someSelected ? "indeterminate" : false}
                    onCheckedChange={(checked) => toggleAll(checked === true)}
                    disabled={filtered.length === 0}
                    aria-label="Selecionar todas as violações"
                  />
                </TableHead>
                <TableHead className={cn(headClass, "whitespace-nowrap")}>Data / hora</TableHead>
                <TableHead className={headClass}>Zona</TableHead>
                <TableHead className={headClass}>Ocorrência</TableHead>
                <TableHead className={headClass}>Pessoa</TableHead>
                <TableHead className={headClass}>Status</TableHead>
                <TableHead className={cn(headClass, "pr-6 text-right")}>Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((v) => {
                const typeStyle = TYPE_STYLE[v.type] || UNKNOWN_TYPE_STYLE;
                const multiIcon = typeStyle.icons.length > 1;
                const selected = selectedIds.has(v.id);

                return (
                  <TableRow
                    className={cn(
                      "border-b border-border transition-colors",
                      selected ? "bg-signal/10 hover:bg-signal/15" : "hover:bg-accent/40"
                    )}
                    data-state={selected ? "selected" : undefined}
                    key={v.id}
                  >
                    <TableCell className="relative w-14 py-3.5 pl-5 pr-0">
                      <span className={cn("absolute inset-y-0 left-0 w-[3px]", ROW_BAR[v.status] || ROW_BAR.active)} aria-hidden />
                      <Checkbox
                        checked={selected}
                        onCheckedChange={(checked) => toggleOne(v.id, checked === true)}
                        aria-label={`Selecionar violação de ${formatDateTime(v.detected_at)}`}
                      />
                    </TableCell>

                    <TableCell className="whitespace-nowrap py-3.5">
                      <div className="text-sm font-semibold text-foreground">{formatDateTime(v.detected_at, "dd/MM/yyyy")}</div>
                      <div className="font-mono text-xs tabular-nums text-muted-foreground">{formatDateTime(v.detected_at, "HH:mm:ss")}</div>
                    </TableCell>

                    <TableCell className="py-3.5">
                      <span className="inline-flex items-center gap-1.5 whitespace-nowrap font-mono text-xs uppercase tracking-wide text-foreground">
                        <MapPin className="h-3.5 w-3.5 text-signal-ink" />
                        {v.zone}
                      </span>
                    </TableCell>

                    <TableCell className="py-3.5">
                      <span className="inline-flex items-center gap-3">
                        <span className={cn("flex h-9 items-center justify-center gap-1 border", multiIcon ? "px-2" : "w-9", typeStyle.color)}>
                          {typeStyle.icons.map((Icon, index) => (
                            <Icon key={index} className={multiIcon ? "h-3.5 w-3.5" : "h-4 w-4"} />
                          ))}
                        </span>
                        <span className="whitespace-nowrap text-sm font-bold uppercase tracking-wide text-foreground">{typeLabel(v.type)}</span>
                      </span>
                    </TableCell>

                    <TableCell className="whitespace-nowrap py-3.5 font-mono text-xs uppercase tracking-wide text-muted-foreground">
                      {personLabel(v) || "—"}
                    </TableCell>

                    <TableCell className="py-3.5">
                      <StatusTag status={v.status} />
                    </TableCell>

                    <TableCell className="py-3.5 pr-5">
                      {/* Cada botão tem a sua "vaga" de largura fixa: as colunas ficam alinhadas entre as linhas. */}
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          onClick={() => setEvidence(v)}
                          disabled={!v.imagem_url}
                          variant="outline"
                          aria-label="Ver evidência"
                          title="Ver evidência"
                          className={cn(actionBtn, "border-info/50 px-3 text-info hover:bg-info/10 hover:text-info")}
                        >
                          <Eye className="h-3.5 w-3.5 xl:mr-1.5" /> <span className="hidden xl:inline">Evidência</span>
                        </Button>
                        <div className="w-[84px]">
                          {v.status === "active" && (
                            <Button
                              onClick={() => updateMutation.mutate({ id: v.id, status: "acknowledged" })}
                              disabled={updateMutation.isPending}
                              variant="outline"
                              className={cn(actionBtn, "w-full border-warning/50 text-warning hover:bg-warning/10 hover:text-warning")}
                            >
                              Analisar
                            </Button>
                          )}
                        </div>
                        <div className="w-[104px]">
                          {v.status !== "resolved" && (
                            <Button
                              onClick={() => updateMutation.mutate({ id: v.id, status: "resolved" })}
                              disabled={updateMutation.isPending}
                              className={cn(actionBtn, "w-full bg-success text-success-foreground hover:bg-success/90")}
                            >
                              <CheckCircle className="mr-1.5 h-3.5 w-3.5" /> Resolver
                            </Button>
                          )}
                        </div>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
              {filtered.length === 0 && (
                <TableRow className="hover:bg-transparent">
                  <TableCell className="py-16 text-center text-muted-foreground" colSpan={7}>
                    <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center border border-border bg-surface">
                      <AlertTriangle className="h-8 w-8 text-signal-ink" />
                    </div>
                    <p className="display text-2xl text-foreground">Nenhuma violação encontrada</p>
                    <p className="mt-2 font-mono text-xs uppercase tracking-wider">
                      {violations.length > 0 ? "Ajuste os filtros de busca" : "Nenhuma infração foi registrada ainda"}
                    </p>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      <EvidenceModal
        src={evidence?.imagem_url}
        people={evidence?.people}
        peopleTotal={evidence?.people_total}
        highlight={evidence?.person_number}
        onClose={() => setEvidence(null)}
      />

      <DeleteViolationsDialog
        open={deleteOpen}
        count={selectedVisible.length}
        onClose={() => setDeleteOpen(false)}
        onConfirm={(password) => deleteMutation.mutate({ ids: selectedVisible, password })}
        isPending={deleteMutation.isPending}
        error={deleteMutation.error}
      />
    </div>
  );
}
