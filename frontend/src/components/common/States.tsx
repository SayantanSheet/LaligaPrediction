import type { ReactNode } from "react";
import { AlertTriangle, Inbox, RotateCw } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function LoadingBlock({ rows = 4, className }: { rows?: number; className?: string }) {
  return (
    <div className={cn("space-y-3", className)} aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-10 w-full" style={{ opacity: 1 - i * 0.12 }} />
      ))}
    </div>
  );
}

export function ErrorState({ error, onRetry, className }: { error: unknown; onRetry?: () => void; className?: string }) {
  const msg = error instanceof Error ? error.message : "Something went wrong.";
  return (
    <div className={cn("flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed p-8 text-center", className)}>
      <AlertTriangle className="h-6 w-6 text-critical" aria-hidden />
      <p className="max-w-md text-sm text-muted-foreground">{msg}</p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RotateCw className="mr-1.5 h-3.5 w-3.5" /> Retry
        </Button>
      )}
    </div>
  );
}

export function EmptyState({ title, children, icon, className }: { title: ReactNode; children?: ReactNode; icon?: ReactNode; className?: string }) {
  return (
    <div className={cn("flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed p-8 text-center", className)}>
      <span className="text-muted-foreground">{icon ?? <Inbox className="h-6 w-6" aria-hidden />}</span>
      <p className="text-sm font-medium">{title}</p>
      {children && <div className="max-w-md text-xs text-muted-foreground">{children}</div>}
    </div>
  );
}
