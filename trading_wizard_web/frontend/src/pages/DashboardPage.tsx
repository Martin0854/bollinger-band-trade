import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button, Card } from '../components/common';
import {
  PortfolioSummaryCard,
  PositionsTable,
  PnLSummary,
} from '../components/dashboard';
import RecommendationsPanel from '../components/trade/RecommendationsPanel';
import { api } from '../services/api';

interface Position {
  id: string;
  stock_code: string;
  stock_name: string;
  quantity: number;
  avg_entry_price: number;
  total_cost: number;
  first_entry_date: string;
  entry_reason?: string;
  confidence_score?: number;
  current_price?: number;
  current_value?: number;
  unrealized_pnl?: number;
  unrealized_pnl_pct?: number;
}

interface PortfolioSummary {
  portfolio_id: string;
  initial_capital: number;
  cash_balance: number;
  total_invested: number;
  total_value: number;
  return_pct: number;
  position_count: number;
  positions: Position[];
  total_unrealized_pnl?: number;
}

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [includePrices, setIncludePrices] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPortfolio = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await api.get<PortfolioSummary>(
        `/portfolio?include_prices=${includePrices}`
      );
      setSummary(data);
    } catch (err) {
      console.error('Failed to fetch portfolio:', err);
      setError('포트폴리오를 불러오는데 실패했습니다');
    } finally {
      setIsLoading(false);
    }
  }, [includePrices]);

  useEffect(() => {
    fetchPortfolio();
  }, [fetchPortfolio]);

  const handleRefresh = () => {
    fetchPortfolio();
  };

  const togglePrices = () => {
    setIncludePrices((prev) => !prev);
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold text-gray-800">Trading Wizard</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">
              {user?.fingerprint ? `${user.fingerprint.slice(0, 8)}...` : ''}
            </span>
            <Button variant="secondary" size="sm" onClick={logout}>
              로그아웃
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Controls */}
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-3">
            <button
              onClick={togglePrices}
              className={`px-3 py-1 text-sm rounded-full transition-colors ${
                includePrices
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {includePrices ? '✓ 실시간 시세' : '시세 표시'}
            </button>
            <button
              onClick={handleRefresh}
              className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800"
              disabled={isLoading}
            >
              ↻ 새로고침
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-100 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Portfolio Summary */}
          <PortfolioSummaryCard summary={summary} isLoading={isLoading} />

          {/* P&L Summary (only when prices included) */}
          {includePrices && (
            <PnLSummary
              positions={summary?.positions || []}
              totalUnrealizedPnl={summary?.total_unrealized_pnl}
              isLoading={isLoading}
            />
          )}

          {/* Quick Actions */}
          <Card title="빠른 메뉴">
            <div className="space-y-3">
              <Button className="w-full" onClick={() => navigate('/trade')}>
                거래 입력
              </Button>
              <Button
                variant="secondary"
                className="w-full"
                onClick={() => alert('Coming soon')}
              >
                거래 이력
              </Button>
              <Button
                variant="secondary"
                className="w-full"
                onClick={() => alert('Coming soon')}
              >
                백테스트
              </Button>
              <Button
                variant="secondary"
                className="w-full"
                onClick={() => alert('Coming soon')}
              >
                설정
              </Button>
            </div>
          </Card>
        </div>

        {/* Daily Wizard Signals */}
        <div className="mt-6">
          <RecommendationsPanel
            onSelectRecommendation={() => navigate('/trade')}
          />
        </div>

        {/* Positions Table */}
        <div className="mt-6">
          <PositionsTable
            positions={summary?.positions || []}
            isLoading={isLoading}
            includePrices={includePrices}
          />
        </div>
      </main>
    </div>
  );
}
