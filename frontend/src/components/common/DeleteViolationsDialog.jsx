import React, { useEffect, useState } from "react";
import { Loader2, ShieldAlert, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";

/**
 * Confirmação de exclusão: pede a senha antes de apagar. Quem confere a senha é a API;
 * aqui só coletamos e mostramos o erro (`error`) sem fechar o diálogo.
 */
export default function DeleteViolationsDialog({ open, count, onClose, onConfirm, isPending, error }) {
  const [password, setPassword] = useState("");

  // Cada abertura começa com o campo limpo; uma senha errada também limpa para nova tentativa.
  useEffect(() => {
    if (open) setPassword("");
  }, [open]);
  useEffect(() => {
    if (error) setPassword("");
  }, [error]);

  const submit = (event) => {
    event.preventDefault();
    if (password && !isPending) onConfirm(password);
  };

  return (
    <Dialog open={open} onOpenChange={(next) => !next && !isPending && onClose()}>
      {/* data-screen: o diálogo fica num portal e precisa carregar a cor de sinal das violações (vermelho) */}
      <DialogContent data-screen="violations" className="max-w-md gap-0 overflow-hidden rounded-sm border-border bg-card p-0 shadow-2xl">
        <div className="hazard h-2" aria-hidden />
        <form onSubmit={submit} className="grid gap-5 p-6">
          <DialogHeader>
            <DialogTitle className="display flex items-center gap-2.5 text-2xl text-destructive">
              <Trash2 className="h-6 w-6" />
              Excluir {count === 1 ? "1 violação" : `${count} violações`}
            </DialogTitle>
            <DialogDescription className="text-sm leading-relaxed text-muted-foreground">
              Os registros serão removidos da tela e do banco de dados, junto com as imagens de evidência. Esta ação não pode ser desfeita.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-2">
            <Label htmlFor="delete-password" className="flex items-center gap-1.5 font-mono text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              <ShieldAlert className="h-4 w-4" /> Senha de autorização
            </Label>
            <Input
              id="delete-password"
              type="password"
              autoFocus
              autoComplete="off"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Digite a senha"
              disabled={isPending}
              className="h-11 rounded-sm border-input bg-background font-mono"
              aria-invalid={Boolean(error)}
              aria-describedby={error ? "delete-password-error" : undefined}
            />
            {error && (
              <p id="delete-password-error" role="alert" className="border-l-[3px] border-destructive bg-destructive/10 px-3 py-2 font-mono text-xs font-semibold uppercase tracking-wide text-destructive">
                {error.message}
              </p>
            )}
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button type="button" variant="outline" onClick={onClose} disabled={isPending} className="h-10 rounded-sm font-mono text-xs font-semibold uppercase tracking-wider">
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={!password || isPending}
              className="h-10 rounded-sm bg-destructive font-mono text-xs font-semibold uppercase tracking-wider text-destructive-foreground hover:bg-destructive/90"
            >
              {isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Trash2 className="mr-2 h-4 w-4" />}
              Excluir
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
