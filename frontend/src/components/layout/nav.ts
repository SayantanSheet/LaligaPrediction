import { CalendarDays, FlaskConical, GitCompareArrows, HeartPulse, LayoutDashboard, ListOrdered, Shield, Target, Users } from "lucide-react";

export const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, mobile: true },
  { to: "/predict", label: "Predictor", icon: Target, mobile: true },
  { to: "/matches", label: "Matches", icon: CalendarDays, mobile: true },
  { to: "/standings", label: "Standings", icon: ListOrdered, mobile: false },
  { to: "/teams", label: "Teams", icon: Shield, mobile: false },
  { to: "/players", label: "Players", icon: Users, mobile: true },
  { to: "/compare", label: "Compare", icon: GitCompareArrows, mobile: false },
  { to: "/injuries", label: "Injuries", icon: HeartPulse, mobile: false },
  { to: "/model", label: "Model Lab", icon: FlaskConical, mobile: false },
] as const;
