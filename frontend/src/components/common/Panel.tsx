import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Panel({ title, subtitle, action, children, className, bodyClassName }: {
  title?: ReactNode; subtitle?: ReactNode; action?: ReactNode; children: ReactNode; className?: string; bodyClassName?: string;
}) {
  return (
    <section className={cn("rounded-xl border bg-card text-card-foreground shadow-sm", className)}>
      {(title || action) && (
        <header className="flex flex-wrap items-start justify-between gap-3 px-5 pt-5">
          <div className="min-w-0">
            {title && <h2 className="text-sm font-semibold tracking-tight">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      <div className={cn("p-5", bodyClassName)}>{children}</div>
    </section>
  );
}

export function PageHeader({ title, description, actions, eyebrow }: { title: ReactNode; description?: ReactNode; actions?: ReactNode; eyebrow?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        {eyebrow && <div className="mb-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">{eyebrow}</div>}
        <h1 className="text-2xl font-bold tracking-tight md:text-3xl">{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function StatTile({ label, value, sub, icon, className }: { label: ReactNode; value: ReactNode; sub?: ReactNode; icon?: ReactNode; className?: string }) {
  return (
    <div className={cn("rounded-xl border bg-card p-4 shadow-sm", className)}>
      <div className="flex items-center justify-between gap-2 text-xs font-medium text-muted-foreground">
        <span>{label}</span>
        {icon && <span className="text-muted-foreground/70">{icon}</span>}
      </div>
      <div className="mt-2 text-2xl font-semibold tracking-tight tabular">{value}</div>
      {sub && <div className="mt-1 text-xs text-muted-foreground">{sub}</div>}
    </div>
  );
}
