import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Users } from "lucide-react";

const mockWorkers = [
  { id: 1, name: "João Silva", role: "Pedreiro", status: "Ativo", zone: "Zona Norte" },
  { id: 2, name: "Carlos Souza", role: "Engenheiro Civil", status: "Ativo", zone: "Canteiro Central" },
  { id: 3, name: "Ana Paula", role: "Técnica de Segurança", status: "Ativa", zone: "Todas as Zonas" },
  { id: 4, name: "Marcos Lima", role: "Eletricista", status: "Em Férias", zone: "Almoxarifado" },
];

export default function Workers() {
  return (
    <div className="space-y-6 max-w-[1400px] mx-auto animate-in fade-in duration-500">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Equipe Operacional</h1>
        <p className="text-sm text-slate-500 mt-1">Gestão de funcionários autorizados no canteiro de obras</p>
      </div>
      
      <Card className="shadow-sm border-slate-200 bg-white">
        <CardHeader className="border-b border-slate-100 bg-slate-50 rounded-t-xl">
          <CardTitle className="flex items-center gap-2">
            <Users className="w-5 h-5 text-blue-600" />
            Trabalhadores Cadastrados
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="bg-slate-50/50 hover:bg-slate-50/50">
                <TableHead className="font-semibold text-slate-700">Nome do Funcionário</TableHead>
                <TableHead className="font-semibold text-slate-700">Função / Cargo</TableHead>
                <TableHead className="font-semibold text-slate-700">Zona de Atuação</TableHead>
                <TableHead className="font-semibold text-slate-700">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockWorkers.map(worker => (
                <TableRow key={worker.id} className="hover:bg-slate-50 transition-colors">
                  <TableCell className="font-medium text-slate-900">{worker.name}</TableCell>
                  <TableCell className="text-slate-600">{worker.role}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className="text-xs font-mono bg-white text-slate-700">
                      {worker.zone}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge className={worker.status === 'Ativo' ? "bg-green-100 text-green-700 border-none hover:bg-green-200" : "bg-slate-100 text-slate-600 border-none"}>
                      {worker.status}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}