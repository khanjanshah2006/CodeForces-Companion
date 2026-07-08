/**
 * api.ts — Typed API Client for the Codeforces Companion FastAPI Backend
 * Base URL: http://localhost:8000/api/v1
 */

// In dev: Vite proxy forwards /api/v1 → http://localhost:8000/api/v1
// In prod: set VITE_API_BASE env var to the deployed backend URL
const BASE_URL =
  (typeof import.meta !== "undefined" && (import.meta as any).env?.VITE_API_BASE
    ? (import.meta as any).env.VITE_API_BASE
    : "") + "/api/v1";

// ---------------------------------------------------------------------------
// JWT Token Helpers — localStorage-backed
// ---------------------------------------------------------------------------
const TOKEN_KEY = "cf_auth_token";

export function getAuthToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setAuthToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearAuthToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

// ─── Response Types ────────────────────────────────────────────────────────

export interface UnsolvedProblem {
  problem_id: string;
  title: string;
  rating: number | null;
  tags: string[];
  failed_attempts: number;
  contest_id: number | null;
  index: string;
}

export interface TagInfo {
  tag: string;
  failure_index: number;
  unique_attempted: number;
  unique_solved: number;
  raw_failures: number;
  status?: string;
}

export interface AnalyticsSummary {
  handle: string;
  current_rating: number;
  max_rating: number;
  rank: string;
  overall_acceptance_rate: number;
  top_issue_verdict: string;
  problems_solved_by_rating: Record<string, number>;
  weak_tags: TagInfo[];
  strong_tags: TagInfo[];
  untried_tags: string[];
  unsolved_problems: UnsolvedProblem[];
}

export interface ProfileSummary {
  rank: string;
  rating: number;
  maxRating: number;
  maxRank: string;
  avatar: string;
  contribution: number;
}

export interface RatingHistoryItem {
  contestName: string;
  date: string;
  rating: number;
}

export interface TagCount {
  tag: string;
  count: number;
}

export interface SubmissionAnalytics {
  verdicts: Record<string, number>;
  topTags: TagCount[];
}

export interface CodeforcesStatsResponse {
  handle: string;
  profile: ProfileSummary;
  ratingHistory: RatingHistoryItem[];
  submissionAnalytics: SubmissionAnalytics;
}

export interface PotdResponse {
  problem_id: string;
  problem_title: string;
  problem_tag: string;
  problem_tags: string[];
  difficulty: number;
  status: "PENDING" | "SOLVED";
  assigned_date: string;
  streak: number;
}

export type VerifyStatus =
  | "NO_POTD_GENERATED"
  | "ALREADY_SOLVED"
  | "NEWLY_SOLVED"
  | "STILL_PENDING";

export interface VerifyResponse {
  status: VerifyStatus;
  problem_id?: string;
}

export interface AiCoachResponse {
  summary: string;
}

// ─── API Helpers ───────────────────────────────────────────────────────────

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(url, { ...options, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ─── Public API Functions ──────────────────────────────────────────────────

/**
 * POST /api/v1/sync/{handle}
 * Fetches fresh Codeforces data and persists to DB. MUST be called first.
 */
export async function syncUser(handle: string): Promise<AnalyticsSummary> {
  return request<AnalyticsSummary>(`${BASE_URL}/sync/${encodeURIComponent(handle.trim())}`, {
    method: "POST",
  });
}

/**
 * GET /api/v1/summary/{handle}
 * Returns cached analytics (15 min TTL). Does NOT write to DB.
 */
export async function getSummary(handle: string): Promise<AnalyticsSummary> {
  return request<AnalyticsSummary>(`${BASE_URL}/summary/${encodeURIComponent(handle.trim())}`);
}

/**
 * GET /api/v1/potd/{handle}
 * Returns (or generates) today's Problem of the Day. Idempotent.
 */
export async function getPotd(handle: string): Promise<PotdResponse> {
  return request<PotdResponse>(`${BASE_URL}/potd/${encodeURIComponent(handle.trim())}`);
}

/**
 * POST /api/v1/potd/{handle}/verify
 * Checks if the user solved today's POTD on Codeforces.
 */
export async function verifyPotd(handle: string): Promise<VerifyResponse> {
  return request<VerifyResponse>(
    `${BASE_URL}/potd/${encodeURIComponent(handle.trim())}/verify`,
    { method: "POST" }
  );
}

/**
 * GET /api/v1/summary/{handle}/ai-coach
 * Generates AI Coach diagnostic summary. Requires summary to be cached first.
 */
export async function getAiCoach(handle: string): Promise<AiCoachResponse> {
  return request<AiCoachResponse>(
    `${BASE_URL}/summary/${encodeURIComponent(handle.trim())}/ai-coach`
  );
}

/**
 * GET /api/v1/stats/{handle}
 * Returns aggregated user stats including rating history.
 */
export async function getStats(handle: string): Promise<CodeforcesStatsResponse> {
  return request<CodeforcesStatsResponse>(
    `${BASE_URL}/stats/${encodeURIComponent(handle.trim())}`
  );
}

// ---------------------------------------------------------------------------
// Auth API — TLE Proof-of-Ownership
// ---------------------------------------------------------------------------

export interface ChallengeResponse {
  problem_id: string;
  problem_title: string;
  problem_url: string;
  expires_at: string;
  snippet: string;
}

export interface AuthVerifyResponse {
  status: "ok" | "pending" | "expired";
  access_token?: string;
  cf_handle?: string;
}

export interface MeResponse {
  cf_handle: string;
  created_at: string;
  last_verified_at: string;
}

/**
 * POST /api/v1/auth/challenge/{handle}
 * Issues a TLE challenge for the given CF handle.
 */
export async function issueChallenge(handle: string): Promise<ChallengeResponse> {
  return request<ChallengeResponse>(
    `${BASE_URL}/auth/challenge/${encodeURIComponent(handle.trim())}`,
    { method: "POST" }
  );
}

/**
 * POST /api/v1/auth/verify/{handle}
 * Checks whether the user has submitted a TLE on the challenge problem.
 * Returns status "ok" with an access_token on success, or "pending" if
 * no matching submission is found yet (poll again).
 */
export async function verifyChallenge(handle: string): Promise<AuthVerifyResponse> {
  // Use raw fetch here so we can handle 202 (pending) without throwing.
  const token = getAuthToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(
    `${BASE_URL}/auth/verify/${encodeURIComponent(handle.trim())}`,
    { method: "POST", headers }
  );

  if (res.status === 202) {
    return { status: "pending" };
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<AuthVerifyResponse>;
}

/**
 * GET /api/v1/auth/me
 * Returns the currently authenticated user. Throws on 401 (expired/missing token).
 */
export async function getMe(): Promise<MeResponse> {
  return request<MeResponse>(`${BASE_URL}/auth/me`);
}
