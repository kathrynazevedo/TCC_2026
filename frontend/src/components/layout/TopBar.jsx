import React, { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { HardHat, Menu, Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import Sidebar from "./Sidebar";
import NotificationPanel from "./NotificationPanel";
import { useAuth } from "@/lib/AuthContext";
import { useEdgeStatus } from "@/api/queries";
import { initials } from "@/lib/format";
import { screenFor } from "@/lib/screens";

// Relógio do painel: a sala de controle sempre mostra a hora do servidor de quem está olhando.
function LiveClock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="hidden whitespace-nowrap text-right leading-none sm:block" aria-label="Data e hora atuais">
      <div className="font-mono text-lg font-semibold tabular-nums text-foreground">{format(now, "HH:mm:ss")}</div>
      <div className="mt-1 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
        {format(now, "EEE, dd MMM yyyy", { locale: ptBR })}
      </div>
    </div>
  );
}

// Estado real da placa (heartbeat) e da API, atualizado a cada 10s.
function LinkStatus() {
  const { data, error, isLoading } = useEdgeStatus();

  let tone = "text-muted-foreground";
  let label = "Verificando";
  if (error) {
    tone = "text-destructive";
    label = "API fora do ar";
  } else if (data) {
    tone = data.online ? "text-success" : "text-warning";
    label = data.online ? "Placa online" : "Placa offline";
  } else if (!isLoading) {
    label = "Sem dados";
  }

  return (
    <div className={`hidden items-center gap-2 whitespace-nowrap border border-border bg-card px-3 py-2 font-mono text-[11px] font-semibold uppercase tracking-wider md:flex ${tone}`}>
      <span className="led led-pulse" />
      {label}
    </div>
  );
}

export default function TopBar({ isDarkMode, setIsDarkMode }) {
  const { user } = useAuth();
  const { pathname } = useLocation();
  const screen = screenFor(pathname);

  return (
    <header className="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-x-4 border-b border-border bg-background/90 px-4 backdrop-blur sm:px-6 lg:px-8">
      {/* linha de sinal: muda de cor com a tela */}
      <span className="pointer-events-none absolute inset-x-0 bottom-[-1px] h-[2px] bg-signal" aria-hidden />

      <div className="flex lg:hidden">
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Abrir menu" className="text-foreground hover:bg-accent">
              <Menu className="h-6 w-6" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="z-50 w-72 border-none p-0">
            <div className="sr-only">
              <SheetTitle>Menu de Navegação</SheetTitle>
              <SheetDescription>Acesse as páginas do sistema SafeWork</SheetDescription>
            </div>
            {/* Sem as props de recolher: no celular o menu sempre abre inteiro */}
            <Sidebar />
          </SheetContent>
        </Sheet>
      </div>

      <div className="flex flex-1 items-center justify-between gap-x-4">
        {/* Logo no celular */}
        <div className="flex items-center gap-2 lg:hidden">
          <div className="chamfer-sm flex h-8 w-8 items-center justify-center bg-primary text-primary-foreground">
            <HardHat className="h-5 w-5" />
          </div>
          <span className="display text-xl text-foreground">SafeWork</span>
        </div>

        {/* Onde estou */}
        <div className="hidden min-w-0 whitespace-nowrap lg:block">
          <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground">SafeWork / Sala de controle</div>
          <div className="display mt-1 flex items-center gap-2 text-xl text-foreground">
            <span className="font-mono text-sm font-semibold text-signal-ink">{screen.code}</span>
            {screen.label}
          </div>
        </div>

        <div className="ml-auto flex items-center gap-x-2 sm:gap-x-4">
          <LinkStatus />
          <LiveClock />

          <span className="mx-1 hidden h-8 w-px bg-border sm:block" aria-hidden />

          <Button
            variant="ghost"
            size="icon"
            aria-label="Alternar tema"
            onClick={() => setIsDarkMode(!isDarkMode)}
            className="text-foreground hover:bg-accent"
          >
            {isDarkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </Button>

          <NotificationPanel />

          <div className="flex items-center gap-3 pl-1">
            <div className="hidden whitespace-nowrap text-right xl:block">
              <p className="text-sm font-semibold leading-none text-foreground">{user.role}</p>
              <p className="mt-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Gestão completa</p>
            </div>
            <div className="chamfer-sm flex h-10 w-10 shrink-0 items-center justify-center bg-signal font-mono text-xs font-bold text-signal-foreground">
              {initials(user.name)}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
