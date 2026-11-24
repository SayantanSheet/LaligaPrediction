import { useState } from "react";
import { cn } from "@/lib/utils";
import { initials } from "@/lib/format";

const sizes = { xs: "h-5 w-5 text-[8px]", sm: "h-7 w-7 text-[10px]", md: "h-10 w-10 text-xs", lg: "h-14 w-14 text-sm", xl: "h-20 w-20 text-lg" };

export function TeamCrest({ team, logo, size = "sm", className }: { team: string; logo?: string | null; size?: keyof typeof sizes; className?: string }) {
  const [broken, setBroken] = useState(false);
  if (!logo || broken) {
    return (
      <span className={cn("inline-flex shrink-0 items-center justify-center rounded-full bg-muted font-semibold text-muted-foreground", sizes[size], className)} aria-hidden>
        {initials(team)}
      </span>
    );
  }
  return (
    <img
      src={logo}
      alt=""
      loading="lazy"
      onError={() => setBroken(true)}
      className={cn("shrink-0 object-contain", sizes[size], className)}
    />
  );
}

export function PlayerAvatar({ name, photo, size = "md", className }: { name: string; photo?: string | null; size?: keyof typeof sizes; className?: string }) {
  const [broken, setBroken] = useState(false);
  if (!photo || broken) {
    return (
      <span className={cn("inline-flex shrink-0 items-center justify-center rounded-full bg-muted font-semibold text-muted-foreground", sizes[size], className)} aria-hidden>
        {initials(name)}
      </span>
    );
  }
  return (
    <img src={photo} alt="" loading="lazy" onError={() => setBroken(true)} className={cn("shrink-0 rounded-full bg-muted object-cover", sizes[size], className)} />
  );
}
