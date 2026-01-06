import { useState, useEffect } from 'react';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import { Input } from '../common/Input';
import { UserSettings, ConstitutionWarning } from '../../types';

interface SettingsFormProps {
  initialSettings: UserSettings;
  onSave: (settings: UserSettings) => Promise<ConstitutionWarning[]>;
  isLoading?: boolean;
}

export function SettingsForm({
  initialSettings,
  onSave,
  isLoading = false,
}: SettingsFormProps) {
  const [settings, setSettings] = useState<UserSettings>(initialSettings);
  const [warnings, setWarnings] = useState<ConstitutionWarning[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    setSettings(initialSettings);
  }, [initialSettings]);

  // Check for potential Constitution III violations on change
  useEffect(() => {
    const newWarnings: ConstitutionWarning[] = [];

    if (settings.stop_loss_pct < 5) {
      newWarnings.push({
        field: 'stop_loss_pct',
        message: 'Constitution III 권장: 손절선 5% 이상',
        recommended_value: 5,
      });
    }

    if (settings.max_position_pct > 10) {
      newWarnings.push({
        field: 'max_position_pct',
        message: 'Constitution III 권장: 종목당 비중 10% 이하',
        recommended_value: 10,
      });
    }

    if (settings.max_positions > 15) {
      newWarnings.push({
        field: 'max_positions',
        message: 'Constitution III 권장: 최대 포지션 15개 이하',
        recommended_value: 15,
      });
    }

    setWarnings(newWarnings);
  }, [settings]);

  const handleChange = (field: keyof UserSettings, value: number) => {
    setSettings((prev) => ({ ...prev, [field]: value }));
    setSuccessMessage(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setSuccessMessage(null);

    try {
      const serverWarnings = await onSave(settings);
      setWarnings(serverWarnings);
      setSuccessMessage('설정이 저장되었습니다.');
    } catch (err) {
      console.error('Failed to save settings:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = () => {
    setSettings({
      max_positions: 15,
      max_position_pct: 10,
      stop_loss_pct: 5,
      confidence_threshold: 60,
    });
    setSuccessMessage(null);
  };

  return (
    <Card className="p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">전략 설정</h2>

      {warnings.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
          <h3 className="font-medium text-yellow-800 mb-2">
            ⚠️ Constitution III 경고
          </h3>
          <ul className="text-sm text-yellow-700 space-y-1">
            {warnings.map((w, i) => (
              <li key={i}>• {w.message}</li>
            ))}
          </ul>
        </div>
      )}

      {successMessage && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg mb-4">
          {successMessage}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <Input
            label="최대 포지션 수"
            type="number"
            value={settings.max_positions}
            onChange={(e) => handleChange('max_positions', Number(e.target.value))}
            min={1}
            max={50}
            helperText="동시에 보유할 수 있는 최대 종목 수 (권장: 15)"
          />
        </div>

        <div>
          <Input
            label="종목당 최대 비중 (%)"
            type="number"
            value={settings.max_position_pct}
            onChange={(e) => handleChange('max_position_pct', Number(e.target.value))}
            min={1}
            max={100}
            step={0.5}
            helperText="총 자본 대비 단일 종목 최대 투자 비율 (권장: 10%)"
          />
        </div>

        <div>
          <Input
            label="손절선 (%)"
            type="number"
            value={settings.stop_loss_pct}
            onChange={(e) => handleChange('stop_loss_pct', Number(e.target.value))}
            min={1}
            max={50}
            step={0.5}
            helperText="매수가 대비 손절 기준 (권장: 5%)"
          />
        </div>

        <div>
          <Input
            label="신뢰도 임계값"
            type="number"
            value={settings.confidence_threshold}
            onChange={(e) => handleChange('confidence_threshold', Number(e.target.value))}
            min={0}
            max={100}
            helperText="매수 신호 최소 신뢰도 점수 (권장: 60)"
          />
        </div>

        <div className="flex gap-3 pt-4">
          <Button
            type="submit"
            isLoading={isSaving || isLoading}
            disabled={isSaving || isLoading}
            className="flex-1"
          >
            저장
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={handleReset}
            disabled={isSaving || isLoading}
          >
            기본값으로 초기화
          </Button>
        </div>
      </form>

      <div className="mt-6 pt-6 border-t border-gray-200">
        <h3 className="font-medium text-gray-900 mb-2">Constitution III 원칙</h3>
        <ul className="text-sm text-gray-600 space-y-1">
          <li>• 손절선: 5% 이상 (리스크 관리)</li>
          <li>• 종목당 비중: 10% 이하 (분산 투자)</li>
          <li>• 최대 포지션: 15개 이하 (집중 관리)</li>
        </ul>
      </div>
    </Card>
  );
}
