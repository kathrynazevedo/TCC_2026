import React from "react";
import { cn } from "@/lib/utils";

/** Cantoneiras de "mira" de câmera. Posicione dentro de um contêiner `relative`. */
export default function Brackets({ className }) {
  const corner = "absolute h-3 w-3 border-signal";
  return (
    <span className={cn("pointer-events-none absolute inset-2", className)} aria-hidden>
      <span className={cn(corner, "left-0 top-0 border-l-2 border-t-2")} />
      <span className={cn(corner, "right-0 top-0 border-r-2 border-t-2")} />
      <span className={cn(corner, "bottom-0 left-0 border-b-2 border-l-2")} />
      <span className={cn(corner, "bottom-0 right-0 border-b-2 border-r-2")} />
    </span>
  );
}
