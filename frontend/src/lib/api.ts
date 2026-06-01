import axios from "axios";
import type {
  AIBrief,
  AdminUserItem,
  FearGreedData,
  FundamentalAnalysis,
  FundamentalCreateResponse,
  FundamentalListItem,
  GeneratePortfolioRequest,
  IndexQuote,
  LoginRequest,
  MarketDashboard,
  MarketSentimentData,
  NewsArticle,
  Portfolio,
  PortfolioListItem,
  RegisterRequest,
  StatusResponse,
  TokenResponse,
  User,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
});

// Attach JWT and fix Content-Type for every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("portai_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  // Let XHR set Content-Type with boundary when sending FormData
  if (config.data instanceof FormData) {
    delete config.headers["Content-Type"];
  }
  return config;
});

// Redirect to /login on 401
api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("portai_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────────

export const authApi = {
  register: (data: RegisterRequest) =>
    api.post<User>("/auth/register", data).then((r) => r.data),

  login: (data: LoginRequest) =>
    api.post<TokenResponse>("/auth/login", data).then((r) => r.data),

  me: () => api.get<User>("/auth/me").then((r) => r.data),
};

// ── Portfolio ─────────────────────────────────────────────────────────────────

export const portfolioApi = {
  generate: (data: GeneratePortfolioRequest) =>
    api.post<Portfolio>("/portfolio/generate", data).then((r) => r.data),

  history: (limit = 20, offset = 0) =>
    api
      .get<PortfolioListItem[]>(`/portfolio/history?limit=${limit}&offset=${offset}`)
      .then((r) => r.data),

  get: (id: number) =>
    api.get<Portfolio>(`/portfolio/${id}`).then((r) => r.data),

  status: (id: number) =>
    api.get<StatusResponse>(`/portfolio/${id}/status`).then((r) => r.data),

  save: (id: number) =>
    api.post(`/portfolio/${id}/save`).then((r) => r.data),
};

// ── Fundamental Analysis ──────────────────────────────────────────────────────

export const fundamentalApi = {
  analyze: (formData: FormData) =>
    api
      .post<FundamentalCreateResponse>("/fundamental/analyze", formData, {
        timeout: 120_000,
      })
      .then((r) => r.data),

  get: (id: number) =>
    api.get<FundamentalAnalysis>(`/fundamental/analyze/${id}`).then((r) => r.data),

  history: () =>
    api.get<FundamentalListItem[]>("/fundamental/history").then((r) => r.data),
};

// ── Admin ─────────────────────────────────────────────────────────────────────

// Separate axios instance for admin — no 401→/login redirect, reads portai_admin_token
const adminAxios = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
});
adminAxios.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("portai_admin_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const adminApi = {
  /** Verify any token directly without touching localStorage. */
  verifyToken: (token: string) =>
    adminAxios
      .get<User>("/auth/me", { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.data),

  /** Get the currently logged-in admin's profile (uses portai_admin_token). */
  me: () => adminAxios.get<User>("/auth/me").then((r) => r.data),

  users: () => adminAxios.get<AdminUserItem[]>("/admin/users").then((r) => r.data),

  updateRole: (userId: number, role: string) =>
    adminAxios.patch(`/admin/users/${userId}/role`, { role }).then((r) => r.data),
};

// ── Market ────────────────────────────────────────────────────────────────────

export const marketApi = {
  snapshot: () =>
    api.get<Record<string, unknown>>("/market/snapshot").then((r) => r.data),

  dashboard: () =>
    api.get<MarketDashboard>("/market/dashboard").then((r) => r.data),

  fearGreed: () =>
    api.get<FearGreedData>("/market/fear-greed").then((r) => r.data),

  sentiment: () =>
    api.get<MarketSentimentData>("/market/sentiment").then((r) => r.data),

  indices: () =>
    api.get<{ indices: IndexQuote[] }>("/market/indices").then((r) => r.data),

  news: () =>
    api.get<{ articles: NewsArticle[]; count: number }>("/market/news").then((r) => r.data),

  aiBrief: () =>
    api.get<AIBrief>("/market/ai-brief").then((r) => r.data),
};
