import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const mockZones = [
  { id: 1, name: "Zona Norte", code: "Norte", status: "Monitorada" },
  { id: 2, name: "Canteiro Central", code: "Central", status: "Monitorada" },
  { id: 3, name: "Almoxarifado", code: "Almoxarifado", status: " Não Monitorada" },
];

export default function Zones() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Gestão de Zonas de Risco</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {mockZones.map(zone => (
          <Card key={zone.id}>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">{zone.name}</CardTitle>
            </CardHeader>
            <CardContent>
              <Badge variant="outline" className="bg-success/10 text-success border-success/20">
                {zone.status}
              </Badge>
              <p className="text-xs text-muted-foreground mt-2 font-mono">Código: {zone.code}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}