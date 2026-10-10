import * as React from "react"
import * as CheckboxPrimitive from "@radix-ui/react-checkbox"
import { Check, Minus } from "lucide-react"

import { cn } from "@/lib/utils"

// Caixa quadrada na cor de sinal da tela (amarelo no painel, vermelho nas violações etc.).
const Checkbox = React.forwardRef(({ className, ...props }, ref) => (
  <CheckboxPrimitive.Root
    ref={ref}
    className={cn(
      "peer flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-[2px] border-2 border-input bg-background transition-colors hover:border-signal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal/50 disabled:cursor-not-allowed disabled:opacity-40 data-[state=checked]:border-signal data-[state=checked]:bg-signal data-[state=checked]:text-signal-foreground data-[state=indeterminate]:border-signal data-[state=indeterminate]:bg-signal data-[state=indeterminate]:text-signal-foreground",
      className
    )}
    {...props}>
    <CheckboxPrimitive.Indicator className={cn("flex items-center justify-center text-current")}>
      {props.checked === "indeterminate" ? <Minus className="h-3.5 w-3.5" strokeWidth={4} /> : <Check className="h-3.5 w-3.5" strokeWidth={4} />}
    </CheckboxPrimitive.Indicator>
  </CheckboxPrimitive.Root>
))
Checkbox.displayName = CheckboxPrimitive.Root.displayName

export { Checkbox }
