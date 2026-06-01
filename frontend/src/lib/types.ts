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

export interface MarketSentimentComponent {
  key: string;
  name: string;
  score: number;
  value: number;
  label: string;
}

export interface MarketSentimentData {
  value: number;
  classification: string;
  generated_at: string;
  source: string;
  is_live: boolean;
  is_mock: boolean;
  refresh_seconds: number;
  sample_size: number;
  components: MarketSentimentComponent[];
  drivers: string[];
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
  sentiment: MarketSentimentData;
  indices: IndexQuote[];
  news: NewsArticle[];
}

// ── Fundamental Analysis ───────────────────────────────────────────────────────

export type FundamentalStatus = "pending" | "processing" | "completed" | "failed";
export type SignalKey = "STRONG_BUY" | "BUY" | "MODERATE_BUY" | "NEUTRAL" | "AVOID";
export type RedFlagSeverity = "HIGH" | "MEDIUM" | "LOW";

export interface FundamentalSignal {
  key: SignalKey;
  label: string;
}

export interface FundamentalScoreBreakdown {
  fundamental_health: number;
  growth_quality: number;
  earnings_integrity: number;
  valuation: number;
  business_momentum: number;
}

export interface EntryZone {
  attractive_entry: number;
  fair_entry: number;
  current_price: number;
  intrinsic_estimate: number;
}

export interface EntrySignal {
  total_score: number;
  signal: FundamentalSignal;
  breakdown: FundamentalScoreBreakdown;
  key_strengths: string[];
  key_risks: string[];
  entry_zone: EntryZone | null;
  suggested_horizon: string;
}

export interface RedFlag {
  severity: RedFlagSeverity;
  category: string;
  description: string;
}

export interface ValuationZone {
  key: string;
  label: string;
  price_to_intrinsic: number;
}

export interface ValuationResult {
  current_price: number | null;
  is_usd_report?: boolean;
  dcf: {
    base_fcf: number | null;
    growth_rate_pct: number;
    wacc_pct: number;
    terminal_growth_pct: number;
    intrinsic_value_per_share: number | null;
  };
  relative: {
    pe_current: number | null;
    pbv_current: number | null;
    eps_latest: number | null;
  };
  zone: ValuationZone | null;
  skipped: boolean;
}

export interface TrendSeries {
  values: (number | null)[];
  yoy_pct: (number | null)[];
  cagr_pct?: number | null;
  trend: string;
}

export interface TrendAnalysis {
  year_labels: number[];
  revenue: TrendSeries;
  net_income: TrendSeries;
  eps: TrendSeries;
  free_cash_flow: TrendSeries;
  margins: {
    gross_margin_pct: (number | null)[];
    operating_margin_pct: (number | null)[];
    net_margin_pct: (number | null)[];
    gross_trend: string;
    net_trend: string;
  };
  detected_patterns: string[];
}

export interface RatioYear {
  year: number;
  profitability: {
    gross_margin_pct: number | null;
    operating_margin_pct: number | null;
    net_margin_pct: number | null;
    roe_pct: number | null;
    roa_pct: number | null;
    roic_pct: number | null;
  };
  liquidity: {
    current_ratio: number | null;
    quick_ratio: number | null;
    cash_ratio: number | null;
  };
  solvency: {
    der: number | null;
    debt_to_assets: number | null;
    interest_coverage: number | null;
  };
  cash_quality: {
    cash_conversion_ratio: number | null;
    fcf_margin_pct: number | null;
    capex_intensity_pct: number | null;
  };
}

export interface FundamentalAnalysis {
  id: number;
  ticker: string;
  current_price: number | null;
  status: FundamentalStatus;
  error_message: string | null;
  ratios: { years: RatioYear[]; latest_year: RatioYear } | null;
  trend_analysis: TrendAnalysis | null;
  red_flags: RedFlag[];
  valuation: ValuationResult | null;
  entry_signal: EntrySignal | null;
  narrative_report: string | null;
  files: { filename: string; year: number | null; type: string }[];
  created_at: string;
  completed_at: string | null;
}

export interface FundamentalListItem {
  id: number;
  ticker: string;
  status: FundamentalStatus;
  score: number | null;
  signal: string | null;
  created_at: string;
}

export interface FundamentalCreateResponse {
  analysis_id: number;
  status: FundamentalStatus;
  ticker: string;
}

// ── Admin ─────────────────────────────────────────────────────────────────────

export interface AdminUserItem {
  id: number;
  email: string;
  name: string;
  role: "user" | "admin";
  created_at: string;
  portfolio_count: number;
  age?: number | null;
  risk_tolerance?: string | null;
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
  error_message?: string | null;
  created_at: string;
  completed_at?: string | null;
}
