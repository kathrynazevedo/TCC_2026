import React from "react";
import { useQuery } from "@tanstack/react-query";
import { getAreas } from "@/api/apiClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MapPin, Camera } from "lucide-react";

export default function Zones() {
  const { data: areas = [], isLoading } = useQuery({
    queryKey: ["areas"],
    queryFn: getAreas,
  });

  return (
    <div className="space-y-6 max-w-[1400px] mx-auto animate-in fade-in duration-500">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Gestão de Zonas de Risco</h1>
        <p className="text-sm text-slate-500 mt-1">Monitoramento de áreas e dispositivos de borda ativos no canteiro</p>
      </div>

      {isLoading ? (
        <div className="text-sm text-slate-500">A carregar zonas...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {areas.map(area => (
            <Card key={area.id_area} className="shadow-sm border-slate-200 bg-white hover:border-blue-300 transition-all">
              <CardHeader className="pb-3 border-b border-slate-100 bg-slate-50/50 rounded-t-xl">
                <CardTitle className="text-lg font-bold text-slate-800 flex items-center gap-2">
                  <MapPin className="w-5 h-5 text-blue-600" />
                  {area.nome_area}
                </CardTitle>
              </CardHeader>
              <CardContent className="p-5 space-y-4">
                <div>
                  <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                    Monitorada via Câmera
                  </Badge>
                  <p className="text-xs text-slate-500 mt-2">
                    {area.descricao || "Área monitorada por visão computacional para conformidade de EPIs."}
                  </p>
                </div>

                <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-mono text-slate-600">
                  <span className="flex items-center gap-1 text-slate-500">
                    <Camera className="w-4 h-4 text-purple-600" /> Dispositivo:
                  </span>
                  <span className="font-bold text-slate-800">{area.numero_serie || "Nenhum atribuído"}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}