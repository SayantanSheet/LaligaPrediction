import { cn } from "@/lib/utils";
import type { FormResult } from "@/api/types";

const styles: Record<FormResult, string> = {
  W: "bg-good text-white",
  D: "bg-muted-foreground/30 text-foreground",
  L: "bg-critical text-white",
};
const titles: Record<FormResult, string> = { W: "Win", D: "Draw", L: "Loss" };

/** W/D/L chips. Letter + colour, so the result never depends on colour alone. Most recent last. */
export function FormPills({ form, size = "sm", className }: { form: string; size?: "sm" | "md"; className?: string }) {
  if (!form) return <span className="text-xs text-muted-foreground">—</span>;
  return (
    <span className={cn("inline-flex items-center gap-1", className)} aria-label={`Form: ${form.split("").map((c) => titles[c as FormResult] ?? c).join(", ")}`}>
      {form.split("").map((c, i) => (
        <span
          key={i}
          title={titles[c as FormResult]}
          className={cn(
            "inline-flex items-center justify-center rounded font-semibold",
            size === "sm" ? "h-5 w-5 text-[10px]" : "h-6 w-6 text-xs",
            styles[c as FormResult] ?? "bg-muted",
          )}
        >
          {c}
        </span>
      ))}
    </span>
  );
}
