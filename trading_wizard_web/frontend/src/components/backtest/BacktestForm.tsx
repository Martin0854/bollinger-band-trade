import { useState } from 'react';
import { Button } from '../common/Button';
import { Input } from '../common/Input';
import { Card } from '../common/Card';

interface BacktestFormProps {
  onSubmit: (params: BacktestParams) => void;
  isLoading?: boolean;
}

interface BacktestParams {
  start_date: string;
  end_date: string;
  stock_list: string;
  initial_capital: number;
  name?: string;
}

const STOCK_LIST_OPTIONS = [
  { value: 'kospi_top100_2023jan', label: '2023년 1월 KOSPI 100' },
  { value: 'kospi_top100_2024jan', label: '2024년 1월 KOSPI 100' },
  { value: 'kospi_top100_2025jan', label: '2025년 1월 KOSPI 100' },
  { value: 'kospi_top100_2026jan', label: '2026년 1월 KOSPI 100' },
];

export function BacktestForm({ onSubmit, isLoading = false }: BacktestFormProps) {
  const [params, setParams] = useState<BacktestParams>({
    start_date: '2025-01-02',
    end_date: '2025-12-31',
    stock_list: 'kospi_top100_2025jan',
    initial_capital: 1000000,
    name: '',
  });

  const handleChange = (field: keyof BacktestParams, value: string | number) => {
    setParams((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(params);
  };

  return (
    <Card className="p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">
        백테스트 실행
      </h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="백테스트 이름 (선택)"
          placeholder="예: 2025년 전체 백테스트"
          value={params.name || ''}
          onChange={(e) => handleChange('name', e.target.value)}
          maxLength={100}
        />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Input
            label="시작일"
            type="date"
            value={params.start_date}
            onChange={(e) => handleChange('start_date', e.target.value)}
            required
          />
          <Input
            label="종료일"
            type="date"
            value={params.end_date}
            onChange={(e) => handleChange('end_date', e.target.value)}
            required
          />
        </div>

        <div className="w-full">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            종목 리스트
          </label>
          <select
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            value={params.stock_list}
            onChange={(e) => handleChange('stock_list', e.target.value)}
          >
            {STOCK_LIST_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <p className="mt-1 text-sm text-gray-500">
            해당 연도 1월 기준 시가총액 상위 100종목
          </p>
        </div>

        <Input
          label="초기 자본금 (KRW)"
          type="number"
          value={params.initial_capital}
          onChange={(e) => handleChange('initial_capital', Number(e.target.value))}
          min={100000}
          step={100000}
          required
          helperText="최소 100,000원"
        />

        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-sm text-yellow-800">
            <strong>주의:</strong> 백테스트 실행에는 최대 3분이 소요될 수 있습니다.
            Yahoo Finance API에서 데이터를 수집하고 분석합니다.
          </p>
        </div>

        <Button
          type="submit"
          className="w-full"
          isLoading={isLoading}
          disabled={isLoading}
        >
          {isLoading ? '실행 중...' : '백테스트 실행'}
        </Button>
      </form>
    </Card>
  );
}
