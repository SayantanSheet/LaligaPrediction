export const pct = (v: number | null | undefined, digits = 1) =>
  v === null || v === undefined || Number.isNaN(v) ? "—" : `${v.toFixed(digits)}%`;

export const num = (v: number | null | undefined, digits = 0) =>
  v === null || v === undefined || Number.isNaN(v) ? "—" : v.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits });

/** Decimal odds implied by a probability given in percent. */
export const fairOdds = (p: number) => (p > 0 ? (100 / p).toFixed(2) : "—");

export const shortDate = (iso: string | null | undefined) =>
  iso ? new Date(iso.length === 10 ? `${iso}T12:00:00Z` : iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }) : "—";

export const dayMonth = (iso: string) =>
  new Date(iso.length === 10 ? `${iso}T12:00:00Z` : iso).toLocaleDateString(undefined, { day: "numeric", month: "short" });

export const kickoffTime = (iso: string) =>
  new Date(iso).toLocaleString(undefined, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

export const timeAgo = (iso: string | null | undefined) => {
  if (!iso) return "never";
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return `${Math.round(s / 86400)} d ago`;
};

export const seasonLabel = (season: number | null | undefined) => (season ? `${season}/${String(season + 1).slice(2)}` : "—");

export const initials = (name: string) =>
  name
    .replace(/[^A-Za-zÀ-ÿ ]/g, "")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();

export const slug = (team: string) => encodeURIComponent(team);
