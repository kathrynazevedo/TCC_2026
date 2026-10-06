import React from "react";
import { Menu, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import Sidebar from "./Sidebar";
import NotificationPanel from "./NotificationPanel";

export default function TopBar() {
  return (
    <header className="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-x-4 border-b border-slate-200 bg-white px-4 sm:px-6 lg:px-8 shadow-sm">
      
      <div className="flex lg:hidden">
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="text-slate-600">
              <Menu className="h-6 w-6" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="p-0 w-72 bg-slate-900 border-none [&>button]:text-white [&>button]:opacity-100 z-50">
            {/* Elementos escondidos apenas para satisfazer a acessibilidade e remover o erro do console */}
            <div className="sr-only">
              <SheetTitle>Menu de Navegação</SheetTitle>
              <SheetDescription>Acesse as páginas do sistema SafeWork</SheetDescription>
            </div>
            <Sidebar />
          </SheetContent>
        </Sheet>
      </div>

      <div className="flex flex-1 items-center justify-between gap-x-4">
        <div className="flex items-center gap-2 lg:hidden">
          <ShieldCheck className="h-8 w-8 text-blue-600" />
          <span className="font-bold text-slate-900">SafeWork</span>
        </div>

        <div className="hidden lg:block text-sm font-semibold text-slate-500 uppercase tracking-wider">
          Painel de Controle Operacional
        </div>

        <div className="flex items-center gap-x-2 ml-auto">
          <NotificationPanel />
          <div className="h-6 w-[1px] bg-slate-200 mx-2 hidden sm:block" />
          <div className="flex items-center gap-3">
             <div className="hidden sm:block text-right">
                <p className="text-xs font-bold text-slate-800">Admin</p>
                <p className="text-[10px] text-green-600 font-medium">Online</p>
             </div>
             <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-bold shadow-sm">
                RA
             </div>
          </div>
        </div>
      </div>
    </header>
  );
}