import { useMemo, useState } from "react";
import { Check, ChevronsUpDown } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { usePlayers, useTeams } from "@/hooks/queries";
import { PlayerAvatar, TeamCrest } from "./Crest";

export function TeamPicker({ value, onChange, exclude, placeholder = "Select team", label, className }: {
  value: string | null; onChange: (t: string) => void; exclude?: string | null; placeholder?: string; label?: string; className?: string;
}) {
  const [open, setOpen] = useState(false);
  const { data, isLoading } = useTeams();
  const items = data?.items ?? [];
  const selected = items.find((t) => t.name === value);
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" role="combobox" aria-expanded={open} aria-label={label ?? placeholder}
          className={cn("h-14 w-full justify-between gap-3 px-3 text-left", className)}>
          <span className="flex min-w-0 items-center gap-3">
            {selected ? <TeamCrest team={selected.name} logo={selected.logo} size="md" /> : <span className="h-10 w-10 rounded-full border border-dashed" />}
            <span className="min-w-0">
              {label && <span className="block text-[11px] font-medium uppercase tracking-wider text-muted-foreground">{label}</span>}
              <span className={cn("block truncate text-sm font-semibold", !selected && "text-muted-foreground")}>
                {selected?.name ?? (isLoading ? "Loading teams…" : placeholder)}
              </span>
            </span>
          </span>
          <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[--radix-popover-trigger-width] min-w-[260px] p-0" align="start">
        <Command>
          <CommandInput placeholder="Search team…" />
          <CommandList>
            <CommandEmpty>No team found.</CommandEmpty>
            <CommandGroup>
              {items.map((t) => (
                <CommandItem key={t.name} value={t.name} disabled={t.name === exclude}
                  onSelect={() => { onChange(t.name); setOpen(false); }} className="gap-2">
                  <TeamCrest team={t.name} logo={t.logo} size="xs" />
                  <span className="flex-1">{t.name}</span>
                  {t.elo && <span className="text-xs text-muted-foreground tabular">{Math.round(t.elo)}</span>}
                  <Check className={cn("h-4 w-4", value === t.name ? "opacity-100" : "opacity-0")} />
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

export function PlayerPicker({ value, onChange, exclude, label, className }: {
  value: number | null; onChange: (id: number) => void; exclude?: number | null; label?: string; className?: string;
}) {
  const [open, setOpen] = useState(false);
  const { data, isLoading } = usePlayers({ min_minutes: 90, limit: 1000, sort: "minutes" });
  const items = useMemo(() => data?.items ?? [], [data]);
  const selected = items.find((p) => p.id === value);
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" role="combobox" aria-expanded={open} aria-label={label ?? "Select player"}
          className={cn("h-14 w-full justify-between gap-3 px-3 text-left", className)}>
          <span className="flex min-w-0 items-center gap-3">
            {selected ? <PlayerAvatar name={selected.name} photo={selected.photo} size="md" /> : <span className="h-10 w-10 rounded-full border border-dashed" />}
            <span className="min-w-0">
              {label && <span className="block text-[11px] font-medium uppercase tracking-wider text-muted-foreground">{label}</span>}
              <span className={cn("block truncate text-sm font-semibold", !selected && "text-muted-foreground")}>
                {selected ? `${selected.name}` : isLoading ? "Loading players…" : "Select player"}
              </span>
            </span>
          </span>
          <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[--radix-popover-trigger-width] min-w-[280px] p-0" align="start">
        <Command>
          <CommandInput placeholder="Search player or team…" />
          <CommandList>
            <CommandEmpty>No player found.</CommandEmpty>
            <CommandGroup>
              {items.map((p) => (
                <CommandItem key={p.id} value={`${p.name} ${p.team} ${p.id}`} disabled={p.id === exclude}
                  onSelect={() => { onChange(p.id); setOpen(false); }} className="gap-2">
                  <PlayerAvatar name={p.name} photo={p.photo} size="xs" />
                  <span className="min-w-0 flex-1 truncate">{p.name}</span>
                  <span className="truncate text-xs text-muted-foreground">{p.team} · {p.position}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
