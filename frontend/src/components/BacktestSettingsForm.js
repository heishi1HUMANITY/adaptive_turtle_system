import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import FileUpload from './FileUpload';
import DateRangePicker from './DateRangePicker';
import NumericInput from './NumericInput';
import ExecutionButton from './ExecutionButton';
import ResetButton from './ResetButton';

const BacktestSettingsForm = () => {
  const navigate = useNavigate();
  const [dataFile, setDataFile] = useState(null);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [initialCapital, setInitialCapital] = useState(1000000);
  const [spread, setSpread] = useState(1.0);
  const [commission, setCommission] = useState(500);
  const [entryPeriod, setEntryPeriod] = useState(20);
  const [exitPeriod, setExitPeriod] = useState(10);
  const [atrPeriod, setAtrPeriod] = useState(20);
  const [riskPercentage, setRiskPercentage] = useState(1.0);
  const [isExecuting, setIsExecuting] = useState(false);

  const [initialCapitalError, setInitialCapitalError] = useState('');
  const [spreadError, setSpreadError] = useState('');
  const [commissionError, setCommissionError] = useState('');
  const [entryPeriodError, setEntryPeriodError] = useState('');
  const [exitPeriodError, setExitPeriodError] = useState('');
  const [atrPeriodError, setAtrPeriodError] = useState('');
  const [riskPercentageError, setRiskPercentageError] = useState('');
  const [submitError, setSubmitError] = useState(null);

  const validateNumericInput = (value, errorSetter, fieldName) => {
    if (value === '' || isNaN(Number(value))) {
      errorSetter(`${fieldName} must be a valid number.`);
      return false;
    }
    // Check for non-negative values for certain fields if necessary (example)
    if (['初期口座資金', 'スプレッド', '手数料', 'エントリー期間', 'エグジット期間', 'ATR期間', 'リスク割合'].includes(fieldName) && Number(value) < 0) {
      errorSetter(`${fieldName} cannot be negative.`);
      return false;
    }
    errorSetter('');
    return true;
  };

  const handleFileChange = (file) => {
    setDataFile(file);
    setSubmitError(null);
  };

  const handleStartDateChange = (date) => {
    setStartDate(date);
    setSubmitError(null);
  };

  const handleEndDateChange = (date) => {
    setEndDate(date);
    setSubmitError(null);
  };

  const handleExecuteBacktest = () => {
    setSubmitError(null); // Clear previous submission errors
    // Perform validation for all fields first
    const isInitialCapitalValid = validateNumericInput(initialCapital, setInitialCapitalError, '初期口座資金');
    const isSpreadValid = validateNumericInput(spread, setSpreadError, 'スプレッド');
    const isCommissionValid = validateNumericInput(commission, setCommissionError, '手数料');
    const isEntryPeriodValid = validateNumericInput(entryPeriod, setEntryPeriodError, 'エントリー期間');
    const isExitPeriodValid = validateNumericInput(exitPeriod, setExitPeriodError, 'エグジット期間');
    const isAtrPeriodValid = validateNumericInput(atrPeriod, setAtrPeriodError, 'ATR期間');
    const isRiskPercentageValid = validateNumericInput(riskPercentage, setRiskPercentageError, 'リスク割合');

    if (!isInitialCapitalValid || !isSpreadValid || !isCommissionValid || !isEntryPeriodValid || !isExitPeriodValid || !isAtrPeriodValid || !isRiskPercentageValid) {
      // No need to set setIsExecuting(false) here as it hasn't been set to true yet for this click.
      return; // Stop execution if any validation fails
    }

    setIsExecuting(true);

    const payload = {
      markets: ["default_market"], // Hardcoded as per instructions
      start_date: startDate,
      end_date: endDate,
      initial_capital: Number(initialCapital),
      spread: Number(spread),
      entry_donchian_period: Number(entryPeriod),
      take_profit_long_exit_period: Number(exitPeriod), // Mapped from exitPeriod
      take_profit_short_exit_period: Number(exitPeriod), // Mapped from exitPeriod
      atr_period: Number(atrPeriod),
      stop_loss_atr_multiplier: 3.0, // Sensible default
      risk_per_trade: Number(riskPercentage) / 100, // Convert percentage to fraction
      total_portfolio_risk_limit: 0.1, // Sensible default
      slippage_pips: 0.5, // Sensible default
      commission_per_lot: Number(commission),
      pip_point_value: {"default_market": 0.01}, // Sensible default
      lot_size: {"default_market": 100000}, // Sensible default
      max_units_per_market: {"default_market": 10} // Sensible default
      // dataFile is intentionally omitted as the backend uses a fixed file for now.
    };

    console.log("Executing backtest with parameters:", payload);

    fetch('http://localhost:8000/api/backtest/run', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
    .then(async response => {
      if (response.ok) {
        return response.json();
      } else {
        // Attempt to get more detailed error from backend
        const errorData = await response.text();
        console.error('Error starting backtest job:', response.status, errorData);
        setSubmitError(`バックテストの開始に失敗しました。サーバーエラー: ${response.status} - ${errorData || '詳細不明'}`);
        // Removed alert(`Error starting backtest: ${response.status} - ${errorData || 'Unknown error'}`);
        throw new Error(`Backend error: ${response.status}`);
      }
    })
    .then(data => {
      if (data.job_id) {
        console.log('Backtest job started successfully. Job ID:', data.job_id);
        navigate(`/loading/${data.job_id}`, { state: { jobId: data.job_id } });
      } else {
        // This case should ideally be caught by !response.ok, but as a fallback
        console.error('Failed to start backtest job: No job_id received', data);
        setSubmitError('バックテストの開始に失敗しました。サーバーから有効なJob IDが返されませんでした。');
        // Removed alert('Failed to start backtest: No job ID received.');
      }
    })
    .catch(error => {
      // Handles network errors or errors thrown from the .then() blocks
      console.error('Fetch error:', error);
      if (error.message.startsWith('Backend error:')) {
        // Error already set by the .then block for !response.ok
        // No need to call setSubmitError here again if it's a re-thrown backend error
      } else {
         setSubmitError('バックテストの開始に失敗しました。ネットワーク接続を確認するか、サーバーが起動しているか確認してください。');
        // Removed alert for generic fetch error, now handled by submitError state
      }
    })
    .finally(() => {
      setIsExecuting(false);
    });
  };

  const handleReset = () => {
    setInitialCapital(1000000);
    setSpread(1.0);
    setCommission(500);
    setEntryPeriod(20);
    setExitPeriod(10);
    setAtrPeriod(20);
    setRiskPercentage(1.0);
    setDataFile(null);
    setStartDate('');
    setEndDate('');

    setInitialCapitalError('');
    setSpreadError('');
    setCommissionError('');
    setEntryPeriodError('');
    setExitPeriodError('');
    setAtrPeriodError('');
    setRiskPercentageError('');
    setSubmitError(null); // Clear submit error on reset as well
    setIsExecuting(false); // Ensure isExecuting is reset
  };

  const createChangeHandler = (setter) => (e) => {
    setter(e.target.value);
    setSubmitError(null);
  };

  return (
    <div>
      <h1>自動売買システム バックテスト</h1>

      <h2>1. データと期間設定</h2>
      <div>
        <FileUpload onFileSelect={handleFileChange} disabled={isExecuting} />
        <DateRangePicker
          startDate={startDate}
          endDate={endDate}
          onStartDateChange={handleStartDateChange}
          onEndDateChange={handleEndDateChange}
          disabled={isExecuting}
        />
      </div>

      <h2>2. シミュレーション条件</h2>
      <div>
        <NumericInput
          id="initialCapital"
          label="初期口座資金 (JPY)"
          value={initialCapital}
          onChange={createChangeHandler(setInitialCapital)}
          onValidate={(value) => validateNumericInput(value, setInitialCapitalError, '初期口座資金')}
          error={initialCapitalError}
          tooltip="Initial account balance in JPY"
          disabled={isExecuting}
        />
        <NumericInput
          id="spread"
          label="スプレッド (pips)"
          value={spread}
          onChange={createChangeHandler(setSpread)}
          onValidate={(value) => validateNumericInput(value, setSpreadError, 'スプレッド')}
          error={spreadError}
          tooltip="Spread in pips"
          disabled={isExecuting}
        />
        <NumericInput
          id="commission"
          label="手数料 (円/ロット)"
          value={commission}
          onChange={createChangeHandler(setCommission)}
          onValidate={(value) => validateNumericInput(value, setCommissionError, '手数料')}
          error={commissionError}
          tooltip="Commission in JPY per lot"
          disabled={isExecuting}
        />
      </div>

      <h2>3. 戦略パラメータ (適応型短期タートルシステム)</h2>
      <div>
        <NumericInput
          id="entryPeriod"
          label="エントリー期間 (ドンチャン)"
          value={entryPeriod}
          onChange={createChangeHandler(setEntryPeriod)}
          onValidate={(value) => validateNumericInput(value, setEntryPeriodError, 'エントリー期間')}
          error={entryPeriodError}
          tooltip="Donchian channel entry period"
          disabled={isExecuting}
        />
        <NumericInput
          id="exitPeriod"
          label="エグジット期間 (ドンチャン)"
          value={exitPeriod}
          onChange={createChangeHandler(setExitPeriod)}
          onValidate={(value) => validateNumericInput(value, setExitPeriodError, 'エグジット期間')}
          error={exitPeriodError}
          tooltip="Donchian channel exit period"
          disabled={isExecuting}
        />
        <NumericInput
          id="atrPeriod"
          label="ATR期間"
          value={atrPeriod}
          onChange={createChangeHandler(setAtrPeriod)}
          onValidate={(value) => validateNumericInput(value, setAtrPeriodError, 'ATR期間')}
          error={atrPeriodError}
          tooltip="Average True Range period"
          disabled={isExecuting}
        />
        <NumericInput
          id="riskPercentage"
          label="リスク割合 (%)"
          value={riskPercentage}
          onChange={createChangeHandler(setRiskPercentage)}
          onValidate={(value) => validateNumericInput(value, setRiskPercentageError, 'リスク割合')}
          error={riskPercentageError}
          tooltip="Risk percentage per trade"
          disabled={isExecuting}
        />
        <ResetButton onClick={handleReset} disabled={isExecuting} />
      </div>

      {submitError && (
        <div style={{ color: 'red', marginTop: '10px', marginBottom: '10px', padding: '10px', border: '1px solid red', borderRadius: '4px' }}>
          {submitError}
        </div>
      )}
      <ExecutionButton onClick={handleExecuteBacktest} isExecuting={isExecuting} />
    </div>
  );
};

export default BacktestSettingsForm;
