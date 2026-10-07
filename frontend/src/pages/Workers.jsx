import React from "react";
import { useQuery } from "@tanstack/react-query";
import { getWorkers } from "@/api/apiClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Users, AlertTriangle } from "lucide-react";

export default function Workers() {
  const { data: workers = [], isLoading } = useQuery({
    queryKey: ["workers"],
    queryFn: getWorkers,
  });

  return (
    <div className="space-y-6 max-w-[1400px] mx-auto animate-in fade-in duration-500">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Equipe Operacional</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Gestão de funcionários autorizados no canteiro de obras</p>
      </div>
                    
      <Card className="shadow-sm border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
        <CardHeader className="border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 rounded-t-xl">
          <CardTitle className="flex items-center gap-2 text-slate-800 dark:text-slate-200">
            <Users className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            Trabalhadores Cadastrados
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="bg-slate-50/50 dark:bg-slate-800/30 hover:bg-slate-50/50 dark:hover:bg-slate-800/30 border-b border-slate-200 dark:border-slate-800">
                <TableHead className="font-semibold text-slate-700 dark:text-slate-300">Nome do Funcionário</TableHead>
                <TableHead className="font-semibold text-slate-700 dark:text-slate-300">Função / Cargo</TableHead>
                <TableHead className="font-semibold text-slate-700 dark:text-slate-300">Zona de Atuação</TableHead>
                <TableHead className="font-semibold text-slate-700 dark:text-slate-300">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-center py-12 text-slate-500 dark:text-slate-400">
                    Carregando equipe...
                  </TableCell>
                </TableRow>
              ) : workers.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-center py-16 text-slate-500 dark:text-slate-400">
                    <div className="w-16 h-16 bg-blue-50 dark:bg-blue-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
                      <AlertTriangle className="w-8 h-8 text-blue-400 dark:text-blue-500" />
                    </div>
                    <p className="text-lg font-medium text-slate-600 dark:text-slate-300">Nenhum trabalhador cadastrado</p>
                    <p className="text-sm mt-1">Insira registros na tabela do banco de dados para exibi-los aqui.</p>
                  </TableCell>
                </TableRow>
              ) : (
                workers.map(worker => (
                  <TableRow key={worker.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors border-b border-slate-100 dark:border-slate-800">
                    <TableCell className="font-medium text-slate-900 dark:text-slate-100">{worker.name}</TableCell>
                    <TableCell className="text-slate-600 dark:text-slate-400">{worker.role}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs font-mono bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700">
                        {worker.zone || "Geral"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={worker.status === 'Ativo' ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 border-none hover:bg-green-200 dark:hover:bg-green-900/50" : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border-none"}>
                        {worker.status}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}