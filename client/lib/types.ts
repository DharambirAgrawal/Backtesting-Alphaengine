export type UserRole = "admin" | "user";
export type TradeAction = "BUY" | "SELL" | "HOLD";
export type ModelType = "lstm" | "xgboost";

export interface User {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface Portfolio {
  id: string;
  name: string;
  description: string | null;
  starting_capital: number;
  current_cash: number;
  holdings_value: number;
  total_value: number;
  profit_loss: number;
  profit_loss_pct: number;
  is_active: boolean;
  tickers: string[];
  created_at: string;
}

export interface Holding {
  ticker: string;
  shares: number;
  avg_buy_price: number;
  current_price: number;
  value: number;
  profit_loss: number;
  profit_loss_pct: number;
}

export interface Transaction {
  id: string;
  portfolio_id: string;
  ticker: string;
  action: TradeAction;
  shares: number;
  price_at_trade: number;
  total_value: number;
  llm_reasoning: string;
  tools_called: Record<string, unknown>;
  executed_at: string;
}

export interface PaginatedTransactions {
  transactions: Transaction[];
  total: number;
  limit: number;
  offset: number;
}

export interface AgentRun {
  id: string;
  portfolio_id: string;
  run_type: string | null;
  session: string | null;
  summary: string | null;
  trades_made: number;
  total_pl: number;
  started_at: string;
  completed_at: string | null;
  status: "running" | "done" | "failed" | "skipped";
}

export interface AgentRunEvaluation {
  ticker: string;
  action: TradeAction;
  llm_reasoning: string;
  tools_called: Record<string, unknown>;
  transaction: Transaction | null;
  summary_line: string | null;
}

export interface AgentRunDetail extends AgentRun {
  evaluations: AgentRunEvaluation[];
  held_all_positions: boolean;
}

export interface PerformanceStats {
  total_return_pct: number;
  sharpe_ratio: number;
  max_drawdown_pct: number;
  win_rate: number;
  total_trades: number;
  profitable_trades: number;
  best_trade: {
    ticker: string;
    gain_pct?: number;
  };
  worst_trade: {
    ticker: string;
    loss_pct?: number;
  };
}

export interface DashboardData {
  portfolio: Portfolio;
  performance: PerformanceStats;
  holdings: Holding[];
  recent_transactions: Transaction[];
  agent_runs: AgentRun[];
  next_run: string | null;
}

export interface ChartData {
  labels: string[];
  total_value: number[];
  cash: number[];
  holdings: number[];
}

export interface MLModel {
  id: string;
  ticker: string;
  model_type: ModelType;
  accuracy: number;
  training_rows: number;
  trained_at: string;
  is_active: boolean;
}

export interface ModelPortfolioReference {
  id: string;
  name: string;
  is_active: boolean;
}

export interface ModelCoverageItem {
  ticker: string;
  portfolios: ModelPortfolioReference[];
  trained_model_types: ModelType[];
  missing_model_types: ModelType[];
  coverage_pct: number;
  is_fully_trained: boolean;
  last_trained_at: string | null;
}

export interface ModelsOverview {
  summary: {
    tracked_tickers: number;
    referenced_portfolios: number;
    trained_model_count: number;
    fully_trained_tickers: number;
    missing_model_count: number;
  };
  available_model_types: ModelType[];
  coverage: ModelCoverageItem[];
}

export interface ModelAccuracyData {
  dates: string[];
  predicted: number[];
  actual: number[];
  rolling_accuracy: number[] | null;
}

export interface TickerSearchResult {
  ticker: string;
  name: string;
  exchange: string;
  type: string;
}

export interface TransactionFilters {
  limit?: number;
  offset?: number;
  ticker?: string;
  action?: TradeAction;
  search?: string;
  from?: string;
  to?: string;
}

export interface MessageResponse {
  message: string;
}

export interface ModelRetrainFailure {
  ticker: string;
  error: string;
}

export interface ModelRetrainAllResult {
  message: string;
  total_tickers: number;
  trained_count: number;
  failed_count: number;
  failed: ModelRetrainFailure[];
}
