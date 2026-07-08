/**
 * store.tsx — Global dashboard state via React Context
 * Holds the active CF handle and all fetched data so every component
 * can read it without prop-drilling.
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import {
  syncUser,
  getSummary,
  getPotd,
  getStats,
  type AnalyticsSummary,
  type PotdResponse,
  type CodeforcesStatsResponse,
} from "./api";

export type LoadState = "idle" | "loading" | "success" | "error";

interface DashboardStore {
  // Current handle being viewed
  handle: string;
  // Whether a sync/load is in flight
  loadState: LoadState;
  // Human-readable error message
  error: string | null;
  // The fetched analytics from the backend
  analytics: AnalyticsSummary | null;
  // The fetched POTD from the backend
  potd: PotdResponse | null;
  // The fetched stats (including rating history) from the backend
  stats: CodeforcesStatsResponse | null;
  // Trigger a full sync (POST /sync + GET /potd)
  doSync: (handle: string) => Promise<void>;
  // Update POTD status locally after successful verify
  markPotdSolved: () => void;
}

const DashboardContext = createContext<DashboardStore | null>(null);

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [handle, setHandle] = useState("");
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [potd, setPotd] = useState<PotdResponse | null>(null);
  const [stats, setStats] = useState<CodeforcesStatsResponse | null>(null);

  const doSync = useCallback(async (rawHandle: string) => {
    const h = rawHandle.trim();
    if (!h) return;

    setLoadState("loading");
    setError(null);

    try {
      // Step 1: Full sync — writes to DB, returns analytics
      const summary = await syncUser(h);
      setHandle(h);
      setAnalytics(summary);

      // Step 2: Warm the server-side in-memory SERVER_CACHE by calling
      // GET /summary/{handle}. The AI coach endpoint requires this cache
      // to be populated — POST /sync alone does NOT populate it.
      await getSummary(h);

      // Step 3: Fetch today's POTD (idempotent)
      const potdData = await getPotd(h);
      setPotd(potdData);

      // Step 4: Fetch stats (rating history)
      try {
        const statsData = await getStats(h);
        setStats(statsData);
      } catch (err) {
        console.error("Failed to fetch stats", err);
      }

      setLoadState("success");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setError(msg);
      setLoadState("error");
    }
  }, []);

  const markPotdSolved = useCallback(() => {
    setPotd((prev) => (prev ? { ...prev, status: "SOLVED" } : prev));
  }, []);

  return (
    <DashboardContext.Provider
      value={{ handle, loadState, error, analytics, potd, stats, doSync, markPotdSolved }}
    >
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboard(): DashboardStore {
  const ctx = useContext(DashboardContext);
  if (!ctx) throw new Error("useDashboard must be used within DashboardProvider");
  return ctx;
}
