/**
 * Type definitions for Trading Wizard Web.
 */

// User and Authentication
export interface User {
  id: string;
  fingerprint: string;
  nickname: string | null;
  created_at: string;
  last_login_at: string | null;
}

export interface AuthChallenge {
  challenge: string;
  expires_at: string;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
}

// Portfolio
export interface Portfolio {
  id: string;
  initial_capital: number;
  cash_balance: number;
  created_at: string;
  updated_at: string;
}

export interface PortfolioSummary extends Portfolio {
  total_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  realized_pnl: number;
  total_trades: number;
  positions_count: number;
}

// Position
export interface Position {
  id: string;
  stock_code: string;
  stock_name: string;
  quantity: number;
  avg_entry_price: number;
  first_entry_date: string;
  entry_reason: string | null;
  confidence_score: number | null;
  current_price?: number;
  current_value?: number;
  unrealized_pnl?: number;
  unrealized_pnl_pct?: number;
}

// Trade
export type TradeAction = 'BUY' | 'SELL';

export interface Trade {
  id: string;
  trade_date: string;
  stock_code: string;
  stock_name: string;
  action: TradeAction;
  quantity: number;
  price: number;
  total_amount: number;
  realized_pnl: number | null;
  reason: string | null;
  created_at: string;
}

export interface TradeInput {
  trade_date: string;
  stock_code: string;
  action: TradeAction;
  quantity: number;
  price: number;
  reason?: string;
}

// Stock
export interface Stock {
  code: string;
  name: string;
}

// Backtest
export interface BacktestParams {
  start_date: string;
  end_date: string;
  stock_list: string;
  initial_capital: number;
  name?: string;
}

export interface BacktestResult {
  id: string;
  name: string | null;
  start_date: string;
  end_date: string;
  stock_list_name: string;
  initial_capital: number;
  final_value: number;
  total_return_pct: number;
  max_drawdown_pct: number;
  total_trades: number;
  winning_trades: number;
  win_rate_pct: number;
  executed_at: string;
}

// Settings
export interface UserSettings {
  max_positions: number;
  max_position_pct: number;
  stop_loss_pct: number;
  confidence_threshold: number;
}

// Pagination
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// API Response helpers
export interface ApiMessage {
  message: string;
}

export interface ConstitutionWarning {
  field: string;
  message: string;
  recommended_value: number;
}
