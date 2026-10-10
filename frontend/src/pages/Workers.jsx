import React from "react";
import { AlertTriangle, Users } from "lucide-react";
import { useWorkers } from "@/api/queries";
import ApiErrorNotice from "@/components/common/ApiErrorNotice";
import PageHeader from "@/components/common/PageHeader";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { initials } from "@/lib/format";

const headClass = "h-11 font-mono text-[11px] font-semibold uppercase tracking-[0.15em] text-muted-foreground";

export default function Workers() {
  const { data: workers = [], isLoading, error } = useWorkers();
  const activeCount = workers.filter((w) => w.status?.toLowerCase() === "ativo").length;

  return (
    <div className="animate-in fade-in space-y-8 duration-500">
      <PageHeader
        code="04"
        icon={Users}
        title="Equipe operacional"
        description="Funcionários autorizados a atuar no canteiro de obras."
      >
        <div className="flex items-stretch border border-border bg-card font-mono">
          <div className="px-4 py-2 text-right">
            <div className="display text-3xl tabular-nums text-foreground">{workers.length}</div>
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground">cadastrados</div>
          </div>
          <div className="border-l border-border px-4 py-2 text-right">
            <div className="display text-3xl tabular-nums text-success">{activeCount}</div>
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground">ativos</div>
          </div>
        </div>
      </PageHeader>

      <ApiErrorNotice error={error} />

      <div className="panel overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="border-b border-border bg-surface hover:bg-surface">
              <TableHead className={cn(headClass, "pl-5")}>Funcionário</TableHead>
              <TableHead className={headClass}>Função / cargo</TableHead>
              <TableHead className={headClass}>Zona de atuação</TableHead>
              <TableHead className={headClass}>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow className="hover:bg-transparent">
                <TableCell colSpan={4} className="py-12 text-center font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  Carregando equipe...
                </TableCell>
              </TableRow>
            ) : workers.length === 0 ? (
              <TableRow className="hover:bg-transparent">
                <TableCell colSpan={4} className="py-16 text-center text-muted-foreground">
                  <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center border border-border bg-surface">
                    <AlertTriangle className="h-8 w-8 text-signal-ink" />
                  </div>
                  <p className="display text-2xl text-foreground">Nenhum trabalhador cadastrado</p>
                  <p className="mt-2 font-mono text-xs uppercase tracking-wider">Insira registros na tabela do banco para exibi-los aqui</p>
                </TableCell>
              </TableRow>
            ) : (
              workers.map((worker) => {
                const active = worker.status?.toLowerCase() === "ativo";
                return (
                  <TableRow key={worker.id} className="border-b border-border transition-colors hover:bg-accent/40">
                    <TableCell className="py-3.5 pl-5">
                      <span className="inline-flex items-center gap-3">
                        <span className="flex h-10 w-10 shrink-0 items-center justify-center border border-border bg-surface font-mono text-xs font-bold text-signal-ink">
                          {initials(worker.name)}
                        </span>
                        <span className="text-sm font-semibold text-foreground">{worker.name}</span>
                      </span>
                    </TableCell>
                    <TableCell className="py-3.5 text-sm text-muted-foreground">{worker.role}</TableCell>
                    <TableCell className="py-3.5">
                      <span className="inline-block border border-border bg-background px-2 py-1 font-mono text-[11px] uppercase tracking-wider text-foreground">
                        {worker.zone || "Geral"}
                      </span>
                    </TableCell>
                    <TableCell className="py-3.5">
                      <span
                        className={cn(
                          "inline-flex items-center gap-1.5 border px-2 py-1 font-mono text-[10px] font-semibold uppercase tracking-wider",
                          active ? "border-success/50 bg-success/10 text-success" : "border-border bg-muted text-muted-foreground"
                        )}
                      >
                        <span className="h-1.5 w-1.5 bg-current" aria-hidden />
                        {worker.status}
                      </span>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
