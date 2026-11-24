import { Ban, CircleAlert, CircleCheck, CircleSlash, Cross } from "lucide-react";
import { cn } from "@/lib/utils";
import type { InjuryStatus } from "@/api/types";

const map: Record<InjuryStatus, { icon: typeof Cross; cls: string }> = {
  Out: { icon: Cross, cls: "border-critical/40 bg-critical/10 text-critical" },
  Doubtful: { icon: CircleAlert, cls: "border-warning/50 bg-warning/10 text-foreground" },
  Suspended: { icon: Ban, cls: "border-serious/50 bg-serious/10 text-foreground" },
  Unavailable: { icon: CircleSlash, cls: "border-border bg-muted text-muted-foreground" },
  Available: { icon: CircleCheck, cls: "border-good/40 bg-good/10 text-good-text" },
};

/** Status always ships icon + label, never colour alone. */
export function StatusChip({ status, className }: { status: InjuryStatus; className?: string }) {
  const { icon: Icon, cls } = map[status] ?? map.Unavailable;
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium", cls, className)}>
      <Icon className="h-3 w-3" aria-hidden />
      {status}
    </span>
  );
}
