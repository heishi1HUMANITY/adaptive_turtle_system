import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import DateRangePicker from './DateRangePicker';
import NumericInput from './NumericInput';
import ExecutionButton from './ExecutionButton';
import ResetButton from './ResetButton';

const BacktestSettingsForm = () => {
  const navigate = useNavigate();
  const [availableDataFiles, setAvailableDataFiles] = useState([]);
  const [selectedDataFile, setSelectedDataFile] = useState('');
  const [dataFilesError, setDataFilesError] = useState('');
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

  useEffect(() => {
    const fetchAvailableFiles = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/data/files');
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`Failed to fetch data files: ${response.status} ${errorText}`);
        }
        const data = await response.json();
        if (data.files && data.files.length > 0) {
          setAvailableDataFiles(data.files.map(file => file.name));
          setSelectedDataFile(data.files[0].name); // Select the first file by default
          setDataFilesError('');
        } else {
          setAvailableDataFiles([]);
          setSelectedDataFile('');
          setDataFilesError('No data files available on the server.');
        }
      } catch (error) {
        console.error('Error fetching data files:', error);
        setDataFilesError(`Error fetching data files: ${error.message}`);
        setAvailableDataFiles([]);
        setSelectedDataFile('');
      }
    };
    fetchAvailableFiles();
  }, []);

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

    if (!selectedDataFile) {
      setSubmitError('Please select a data file for the backtest.');
      // setIsExecuting(false); // Not needed here as it's not true yet
      return;
    }

    setIsExecuting(true);

    const payload = {
      markets: ["default_market"], // Hardcoded as per instructions
      // start_date: startDate, // These seem to be handled by backend or not used currently based on backend main.py
      // end_date: endDate, // These seem to be handled by backend or not used currently
      initial_capital: Number(initialCapital),
      // spread: Number(spread), // This was from original template, but not in Pydantic model for BacktestSettings
      entry_donchian_period: Number(entryPeriod),
      take_profit_long_exit_period: Number(exitPeriod),
      take_profit_short_exit_period: Number(exitPeriod),
      atr_period: Number(atrPeriod),
      stop_loss_atr_multiplier: 3.0, // Default, not in form
      risk_per_trade: Number(riskPercentage) / 100,
      total_portfolio_risk_limit: 0.1, // Default, not in form
      slippage_pips: Number(spread), // Using spread state for slippage_pips as it's more aligned
      commission_per_lot: Number(commission),
      pip_point_value: {"default_market": 0.01}, // Default
      lot_size: {"default_market": 100000}, // Default
      max_units_per_market: {"default_market": 10}, // Default
      data_file_name: selectedDataFile,
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
    // setDataFile(null); // Removed
    setSelectedDataFile(availableDataFiles.length > 0 ? availableDataFiles[0] : '');
    setDataFilesError('');
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
        <div>
          <label htmlFor="dataFileInput">Data File:</label>
          <select
            id="dataFileInput"
            value={selectedDataFile}
            onChange={(e) => {
              setSelectedDataFile(e.target.value);
              setDataFilesError(''); // Clear error when user selects a file
              setSubmitError(null); // Clear general submit error as well
            }}
            disabled={isExecuting || availableDataFiles.length === 0}
          >
            {availableDataFiles.length === 0 && !dataFilesError && <option value="">Loading files...</option>}
            {dataFilesError && <option value="">Failed to load files</option>}
            {availableDataFiles.map((fileName) => (
              <option key={fileName} value={fileName}>
                {fileName}
              </option>
            ))}
          </select>
          {dataFilesError && <p style={{ color: 'red' }}>{dataFilesError}</p>}
        </div>
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
