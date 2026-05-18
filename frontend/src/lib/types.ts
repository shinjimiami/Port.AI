// ── Auth ───────────────────────────────────────────────────────────────────────

export interface User {
  id: number;
  email: string;
  name: string;
  role: string;
  profile?: UserProfile | null;
}

export interface UserProfile {
  age?: number | null;
  risk_tolerance?: string | null;
  default_currency: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface RegisterRequest {
  email: string;
  name: string;
  password: string;
  age?: number;
  risk_tolerance?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

// ── Portfolio input ────────────────────────────────────────────────────────────

export type AssetClass = "US_STOCKS" | "IDX" | "CRYPTO";
export type RiskTolerance = "conservative" | "moderate" | "aggressive";
export type Horizon =
  | "1 month"
  | "3 months"
  | "6 months"
  | "1 year"
  | "3 years"
  | "5 years";

export interface GeneratePortfolioRequest {
  budget: number;
  currency: string;
  horizon: Horizon;
  asset_classes: AssetClass[];
  risk_tolerance?: RiskTolerance | null;
}

// ── Portfolio report ───────────────────────────────────────────────────────────

export interface AllocationItem {
  asset_class: string;
  percentage: number;
  amount: number;
}

export interface AssetItem {
  ticker: string;
  name: string;
  asset_class: string;
  sector?: string | null;
  allocation_percentage: number;
  amount: number;
  reasoning: string;
  current_price?: number | null;
  expected_return?: string | null;
}

export interface RiskMetrics {
  expected_return: string;
  risk_level: string;
  max_drawdown_estimate: string;
  sharpe_estimate?: string | null;
}

export interface RebalancingInfo {
  suggested_date?: string | null;
  trigger_conditions: string[];
}

export interface PortfolioReport {
  summary: string;
  total_budget: number;
  currency: string;
  horizon: string;
  risk_profile: string;
  allocation: AllocationItem[];
  assets: AssetItem[];
  risk_metrics: RiskMetrics;
  rebalancing: RebalancingInfo;
  market_context: string;
  warnings: string[];
  disclaimer: string;
}

// ── Portfolio record ───────────────────────────────────────────────────────────

export type PortfolioStatus = "pending" | "processing" | "completed" | "failed";

export interface Portfolio {
  id: number;
  budget: number;
  currency: string;
  horizon: string;
  asset_classes: string[];
  risk_tolerance?: string | null;
  allocation_plan?: Record<string, unknown> | null;
  selected_assets?: AssetItem[] | null;
  report?: PortfolioReport | null;
  status: PortfolioStatus;
  created_at: string;
  completed_at?: string | null;
}

export interface PortfolioListItem {
  id: number;
  budget: number;
  currency: string;
  horizon: string;
  status: PortfolioStatus;
  created_at: string;
}

// ── Market Dashboard ──────────────────────────────────────────────────────────

export interface FearGreedData {
  value: number;
  classification: string;
  timestamp: string;
  history: { value: number; classification: string }[];
}

export interface IndexQuote {
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_pct: number;
  currency: string;
}

export interface NewsArticle {
  title: string;
  description: string;
  url: string;
  source: string;
  published_at: string;
  image_url: string | null;
}

export interface AIBrief {
  brief: string;
  generated_at: string;
  model: string;
  is_mock: boolean;
}

export interface MarketDashboard {
  fear_greed: FearGreedData;
  indices: IndexQuote[];
  news: NewsArticle[];
}

// ── Progress ───────────────────────────────────────────────────────────────────

export interface ProgressEvent {
  node: string;
  message: string;
}

export interface StatusResponse {
  id: number;
  status: PortfolioStatus;
  current_node?: string | null;
  message?: string | null;
  created_at: string;
  completed_at?: string | null;
}
