import React, { useState } from 'react';
import FileUpload from './FileUpload';
import DateRangePicker from './DateRangePicker';
import NumericInput from './NumericInput';
import ExecutionButton from './ExecutionButton';
import ResetButton from './ResetButton';

const BacktestSettingsForm = () => {
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
  };

  const handleStartDateChange = (date) => {
    setStartDate(date);
  };

  const handleEndDateChange = (date) => {
    setEndDate(date);
  };

  const handleExecuteBacktest = () => {
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

    setIsExecuting(true); // Set executing state only if all validations pass

    const params = {
      dataFile,
      startDate,
      endDate,
      initialCapital,
      spread,
      commission,
      entryPeriod,
      exitPeriod,
      atrPeriod,
      riskPercentage,
    };
    console.log("Backtest Parameters:", params);

    // Simulate API call
    setTimeout(() => {
      console.log("API call finished (mock)");
      setIsExecuting(false);
      // Here you would typically handle the response from the backend
    }, 2000); // Mock 2-second delay
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
    setIsExecuting(false); // Ensure isExecuting is reset
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
          onChange={(e) => setInitialCapital(e.target.value)}
          onValidate={(value) => validateNumericInput(value, setInitialCapitalError, '初期口座資金')}
          error={initialCapitalError}
          tooltip="Initial account balance in JPY"
          disabled={isExecuting}
        />
        <NumericInput
          id="spread"
          label="スプレッド (pips)"
          value={spread}
          onChange={(e) => setSpread(e.target.value)}
          onValidate={(value) => validateNumericInput(value, setSpreadError, 'スプレッド')}
          error={spreadError}
          tooltip="Spread in pips"
          disabled={isExecuting}
        />
        <NumericInput
          id="commission"
          label="手数料 (円/ロット)"
          value={commission}
          onChange={(e) => setCommission(e.target.value)}
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
          onChange={(e) => setEntryPeriod(e.target.value)}
          onValidate={(value) => validateNumericInput(value, setEntryPeriodError, 'エントリー期間')}
          error={entryPeriodError}
          tooltip="Donchian channel entry period"
          disabled={isExecuting}
        />
        <NumericInput
          id="exitPeriod"
          label="エグジット期間 (ドンチャン)"
          value={exitPeriod}
          onChange={(e) => setExitPeriod(e.target.value)}
          onValidate={(value) => validateNumericInput(value, setExitPeriodError, 'エグジット期間')}
          error={exitPeriodError}
          tooltip="Donchian channel exit period"
          disabled={isExecuting}
        />
        <NumericInput
          id="atrPeriod"
          label="ATR期間"
          value={atrPeriod}
          onChange={(e) => setAtrPeriod(e.target.value)}
          onValidate={(value) => validateNumericInput(value, setAtrPeriodError, 'ATR期間')}
          error={atrPeriodError}
          tooltip="Average True Range period"
          disabled={isExecuting}
        />
        <NumericInput
          id="riskPercentage"
          label="リスク割合 (%)"
          value={riskPercentage}
          onChange={(e) => setRiskPercentage(e.target.value)}
          onValidate={(value) => validateNumericInput(value, setRiskPercentageError, 'リスク割合')}
          error={riskPercentageError}
          tooltip="Risk percentage per trade"
          disabled={isExecuting}
        />
        <ResetButton onClick={handleReset} disabled={isExecuting} />
      </div>

      <ExecutionButton onClick={handleExecuteBacktest} isExecuting={isExecuting} />
    </div>
  );
};

export default BacktestSettingsForm;
