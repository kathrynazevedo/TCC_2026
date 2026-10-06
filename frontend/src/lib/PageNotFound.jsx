import React from "react";
import { useLocation, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

export default function PageNotFound() {
  const location = useLocation();

  return (
    <div className="flex flex-col items-center justify-center h-[80vh] space-y-4">
      <h1 className="text-6xl font-bold text-primary">404</h1>
      <h2 className="text-2xl font-semibold">Página não encontrada</h2>
      <p className="text-muted-foreground">
        O caminho <code className="bg-muted px-2 py-1 rounded text-sm">{location.pathname}</code> não existe no sistema.
      </p>
      <Button asChild className="mt-4">
        <Link to="/">Voltar para o Dashboard</Link>
      </Button>
    </div>
  );
}