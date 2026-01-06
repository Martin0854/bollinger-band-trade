import { useState, useEffect, useRef } from 'react';
import { Button } from '../common/Button';
import { Input } from '../common/Input';
import { Card } from '../common/Card';
import { api } from '../../services/api';

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

interface StockList {
  id: string;
  name: string;
  description: string | null;
  stock_count: number;
  created_at: string;
}

export function BacktestForm({ onSubmit, isLoading = false }: BacktestFormProps) {
  const [params, setParams] = useState<BacktestParams>({
    start_date: '2025-01-02',
    end_date: '2025-12-31',
    stock_list: '',
    initial_capital: 1000000,
    name: '',
  });

  const [customLists, setCustomLists] = useState<StockList[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch user's custom stock lists
  useEffect(() => {
    const fetchCustomLists = async () => {
      try {
        const lists = await api.get<StockList[]>('/stock-lists');
        setCustomLists(lists);
      } catch (err) {
        console.error('Failed to fetch custom stock lists:', err);
      }
    };
    fetchCustomLists();
  }, []);

  const handleChange = (field: keyof BacktestParams, value: string | number) => {
    setParams((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(params);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadError(null);
    setUploadSuccess(null);
    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('name', file.name.replace('.txt', ''));

      const result = await api.upload<StockList>('/stock-lists/upload', formData);

      setCustomLists((prev) => [result, ...prev]);
      setParams((prev) => ({ ...prev, stock_list: result.id }));
      setUploadSuccess(`"${result.name}" 업로드 완료 (${result.stock_count}개 종목)`);
    } catch (err: unknown) {
      const error = err as { detail?: string };
      setUploadError(error.detail || '파일 업로드에 실패했습니다');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDeleteList = async (listId: string, listName: string) => {
    if (!confirm(`"${listName}" 리스트를 삭제하시겠습니까?`)) return;

    try {
      await api.delete(`/stock-lists/${listId}`);
      setCustomLists((prev) => prev.filter((l) => l.id !== listId));
      if (params.stock_list === listId) {
        setParams((prev) => ({ ...prev, stock_list: '' }));
      }
    } catch (err) {
      console.error('Failed to delete stock list:', err);
    }
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
            required
          >
            <option value="">-- 종목 리스트를 선택하세요 --</option>
            {customLists.map((list) => (
              <option key={list.id} value={list.id}>
                {list.name} ({list.stock_count}개)
              </option>
            ))}
          </select>
          {customLists.length === 0 && (
            <p className="mt-1 text-sm text-amber-600">
              종목 리스트를 먼저 업로드해주세요.
            </p>
          )}

          {/* File upload section */}
          <div className="mt-3 p-3 border border-dashed border-gray-300 rounded-lg">
            <input
              type="file"
              ref={fileInputRef}
              accept=".txt"
              onChange={handleFileUpload}
              className="hidden"
              id="stock-list-upload"
            />
            <label
              htmlFor="stock-list-upload"
              className="flex items-center justify-center gap-2 cursor-pointer text-sm text-gray-600 hover:text-gray-800"
            >
              {isUploading ? (
                <span>업로드 중...</span>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  <span>종목 리스트 파일 업로드 (.txt)</span>
                </>
              )}
            </label>
            <p className="mt-1 text-xs text-gray-500 text-center">
              한 줄에 하나의 종목코드 (예: 005930)
            </p>
          </div>

          {uploadError && (
            <p className="mt-2 text-sm text-red-600">{uploadError}</p>
          )}
          {uploadSuccess && (
            <p className="mt-2 text-sm text-green-600">{uploadSuccess}</p>
          )}

          {/* Custom lists management */}
          {customLists.length > 0 && (
            <div className="mt-3">
              <p className="text-xs text-gray-500 mb-2">내 종목 리스트:</p>
              <div className="flex flex-wrap gap-2">
                {customLists.map((list) => (
                  <span
                    key={list.id}
                    className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-gray-100 rounded-full"
                  >
                    {list.name} ({list.stock_count})
                    <button
                      type="button"
                      onClick={() => handleDeleteList(list.id, list.name)}
                      className="text-gray-400 hover:text-red-500"
                    >
                      &times;
                    </button>
                  </span>
                ))}
              </div>
            </div>
          )}
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
