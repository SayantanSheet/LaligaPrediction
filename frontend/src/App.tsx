import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppShell } from "@/components/layout/AppShell";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { LoadingBlock } from "@/components/common/States";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const Predictor = lazy(() => import("./pages/Predictor"));
const Matches = lazy(() => import("./pages/Matches"));
const Standings = lazy(() => import("./pages/Standings"));
const Teams = lazy(() => import("./pages/Teams"));
const TeamDetail = lazy(() => import("./pages/TeamDetail"));
const Players = lazy(() => import("./pages/Players"));
const PlayerDetail = lazy(() => import("./pages/PlayerDetail"));
const Compare = lazy(() => import("./pages/Compare"));
const Injuries = lazy(() => import("./pages/Injuries"));
const ModelLab = lazy(() => import("./pages/ModelLab"));
const NotFound = lazy(() => import("./pages/NotFound"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 2, refetchOnWindowFocus: false, staleTime: 5 * 60 * 1000 },
  },
});

const App = () => (
  <QueryClientProvider client={queryClient}>
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange>
      <TooltipProvider delayDuration={150}>
        <Toaster position="top-right" />
        <BrowserRouter>
          <AppShell>
            <ErrorBoundary>
              <Suspense fallback={<LoadingBlock rows={6} />}>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/predict" element={<Predictor />} />
                  <Route path="/matches" element={<Matches />} />
                  <Route path="/standings" element={<Standings />} />
                  <Route path="/teams" element={<Teams />} />
                  <Route path="/teams/:team" element={<TeamDetail />} />
                  <Route path="/players" element={<Players />} />
                  <Route path="/players/:id" element={<PlayerDetail />} />
                  <Route path="/compare" element={<Compare />} />
                  <Route path="/injuries" element={<Injuries />} />
                  <Route path="/model" element={<ModelLab />} />
                  <Route path="*" element={<NotFound />} />
                </Routes>
              </Suspense>
            </ErrorBoundary>
          </AppShell>
        </BrowserRouter>
      </TooltipProvider>
    </ThemeProvider>
  </QueryClientProvider>
);

export default App;
