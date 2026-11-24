import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useTheme } from "next-themes";
import { Loader2, Menu, Moon, Search, Sun, Trophy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useHealth, usePlayers, useTeams } from "@/hooks/queries";
import { cn } from "@/lib/utils";
import { seasonLabel, shortDate } from "@/lib/format";
import { PlayerAvatar, TeamCrest } from "@/components/common/Crest";
import { NAV } from "./nav";

function Brand() {
  return (
    <Link to="/" className="flex items-center gap-2.5 px-2">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
        <Trophy className="h-4 w-4" />
      </span>
      <span className="leading-tight">
        <span className="block text-sm font-bold tracking-tight">LaLiga Prediction</span>
        <span className="block text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Pro Analytics</span>
      </span>
    </Link>
  );
}

function NavItems({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="space-y-0.5" aria-label="Main">
      {NAV.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/"}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
              isActive ? "bg-sidebar-accent text-foreground" : "text-sidebar-foreground/75 hover:bg-sidebar-accent/60 hover:text-foreground",
            )
          }
        >
          {({ isActive }) => (
            <>
              <Icon className={cn("h-4 w-4", isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground")} />
              {label}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}

function DataStatus({ compact = false }: { compact?: boolean }) {
  const { data, isError } = useHealth();
  if (isError) return <span className="text-xs text-critical">API offline</span>;
  if (!data) return <span className="flex items-center gap-1.5 text-xs text-muted-foreground"><Loader2 className="h-3 w-3 animate-spin" /> Connecting…</span>;
  const ready = data.model === "ready";
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="inline-flex cursor-default items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs text-muted-foreground">
          <span className={cn("h-1.5 w-1.5 rounded-full", ready ? "bg-good" : "bg-warning animate-pulse")} aria-hidden />
          {compact ? seasonLabel(data.data.latest_season) : `Data to ${shortDate(data.data.data_as_of)}`}
        </span>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs text-xs">
        <p>Model: {data.model}. Historical data covers {data.data.matches} matches up to {shortDate(data.data.data_as_of)} (season {seasonLabel(data.data.latest_season)}).</p>
        <p className="mt-1 text-muted-foreground">Live API requests today: {data.api_quota.used}/{data.api_quota.budget}</p>
      </TooltipContent>
    </Tooltip>
  );
}

function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const dark = resolvedTheme === "dark";
  return (
    <Button variant="ghost" size="icon" onClick={() => setTheme(dark ? "light" : "dark")} aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}>
      {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </Button>
  );
}

function GlobalSearch({ open, setOpen }: { open: boolean; setOpen: (v: boolean) => void }) {
  const navigate = useNavigate();
  const { data: teams } = useTeams();
  const { data: players } = usePlayers({ min_minutes: 90, limit: 1000, sort: "minutes" });
  const go = (to: string) => { setOpen(false); navigate(to); };
  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Search teams, players or pages…" />
      <CommandList>
        <CommandEmpty>No results.</CommandEmpty>
        <CommandGroup heading="Pages">
          {NAV.map((n) => (
            <CommandItem key={n.to} value={`page ${n.label}`} onSelect={() => go(n.to)} className="gap-2">
              <n.icon className="h-4 w-4 text-muted-foreground" /> {n.label}
            </CommandItem>
          ))}
        </CommandGroup>
        <CommandGroup heading="Teams">
          {teams?.items.map((t) => (
            <CommandItem key={t.name} value={`team ${t.name}`} onSelect={() => go(`/teams/${encodeURIComponent(t.name)}`)} className="gap-2">
              <TeamCrest team={t.name} logo={t.logo} size="xs" /> {t.name}
            </CommandItem>
          ))}
        </CommandGroup>
        <CommandGroup heading="Players">
          {players?.items.slice(0, 1000).map((p) => (
            <CommandItem key={p.id} value={`player ${p.name} ${p.team} ${p.id}`} onSelect={() => go(`/players/${p.id}`)} className="gap-2">
              <PlayerAvatar name={p.name} photo={p.photo} size="xs" />
              <span className="flex-1 truncate">{p.name}</span>
              <span className="text-xs text-muted-foreground">{p.team}</span>
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}

function WarmupBanner() {
  const { data, isError, failureCount } = useHealth();
  if (data?.model === "ready") return null;
  const msg = isError || (!data && failureCount > 0)
    ? "Waking up the prediction server — free hosting can take up to a minute on the first request."
    : data?.model === "training"
      ? "The model is training on the latest data. Predictions will be available in a few seconds."
      : data?.model === "error"
        ? `Model error: ${data.model_error ?? "unknown"}`
        : null;
  if (!msg) return null;
  return (
    <div role="status" className="flex items-center gap-2 border-b bg-warning/10 px-4 py-2 text-xs md:px-8">
      <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> {msg}
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [searchOpen, setSearchOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.key === "k" && (e.metaKey || e.ctrlKey)) || (e.key === "/" && !(e.target instanceof HTMLInputElement) && !(e.target instanceof HTMLTextAreaElement))) {
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [location.pathname]);

  return (
    <div className="min-h-screen bg-background">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col border-r bg-sidebar px-3 py-5 lg:flex">
        <Brand />
        <div className="mt-8 flex-1 overflow-y-auto scrollbar-thin">
          <NavItems />
        </div>
        <div className="space-y-2 border-t px-2 pt-4 text-[11px] leading-relaxed text-muted-foreground">
          <p>Dixon-Coles Poisson + XGBoost, LightGBM & Random Forest ensemble.</p>
          <p>Data: API-Football.</p>
        </div>
      </aside>

      <div className="lg:pl-60">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-2 border-b bg-background/85 px-4 backdrop-blur-md md:px-8">
          <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setMenuOpen(true)} aria-label="Open menu">
            <Menu className="h-5 w-5" />
          </Button>
          <div className="lg:hidden"><Brand /></div>
          <button
            onClick={() => setSearchOpen(true)}
            className="ml-auto flex h-9 items-center gap-2 rounded-lg border bg-muted/40 px-3 text-sm text-muted-foreground transition-colors hover:bg-muted md:w-72 lg:ml-0"
            aria-label="Search"
          >
            <Search className="h-4 w-4" />
            <span className="hidden md:inline">Search teams & players…</span>
            <kbd className="ml-auto hidden rounded border bg-background px-1.5 font-mono text-[10px] md:inline">⌘K</kbd>
          </button>
          <div className="ml-auto hidden items-center gap-2 sm:flex">
            <DataStatus />
          </div>
          <ThemeToggle />
        </header>
        <WarmupBanner />

        <main className="mx-auto w-full max-w-[1400px] px-4 pb-28 pt-6 md:px-8 lg:pb-12">{children}</main>
      </div>

      {/* Mobile bottom navigation */}
      <nav className="fixed inset-x-0 bottom-0 z-30 flex border-t bg-background/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-md lg:hidden" aria-label="Quick navigation">
        {NAV.filter((n) => n.mobile).map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} end={to === "/"}
            className={({ isActive }) => cn("flex flex-1 flex-col items-center gap-0.5 py-2.5 text-[10px] font-medium", isActive ? "text-primary" : "text-muted-foreground")}>
            <Icon className="h-5 w-5" />
            {label}
          </NavLink>
        ))}
        <button onClick={() => setMenuOpen(true)} className="flex flex-1 flex-col items-center gap-0.5 py-2.5 text-[10px] font-medium text-muted-foreground">
          <Menu className="h-5 w-5" /> More
        </button>
      </nav>

      <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
        <SheetContent side="left" className="w-72 p-4">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <Brand />
          <div className="mt-6"><NavItems onNavigate={() => setMenuOpen(false)} /></div>
          <div className="mt-6"><DataStatus /></div>
        </SheetContent>
      </Sheet>

      <GlobalSearch open={searchOpen} setOpen={setSearchOpen} />
    </div>
  );
}
