import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
      <p className="font-mono text-sm text-muted-foreground">404</p>
      <h1 className="text-2xl font-bold">Offside! This page doesn't exist.</h1>
      <Button asChild><Link to="/">Back to dashboard</Link></Button>
    </div>
  );
}
