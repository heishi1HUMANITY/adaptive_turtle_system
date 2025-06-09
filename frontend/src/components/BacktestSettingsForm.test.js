import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'; // Import act
import '@testing-library/jest-dom'; // For extended matchers like .toBeDisabled()
import BacktestSettingsForm from './BacktestSettingsForm';

// Mock child components to simplify testing, focus on BacktestSettingsForm logic
jest.mock('./FileUpload', () => ({ disabled, onFileSelect }) => <input type="file" data-testid="file-upload" disabled={disabled} onChange={onFileSelect} />);
jest.mock('./DateRangePicker', () => ({ startDate, endDate, onStartDateChange, onEndDateChange, disabled }) => (
  <div>
    <input type="date" data-testid="start-date" value={startDate} onChange={e => onStartDateChange(e.target.value)} disabled={disabled} />
    <input type="date" data-testid="end-date" value={endDate} onChange={e => onEndDateChange(e.target.value)} disabled={disabled} />
  </div>
));

// NumericInput is complex enough that we might want to test its integration,
// or mock it if its internal validation becomes too complex for this form's unit test.
// For now, we'll test with the actual NumericInput to see validation integration.

describe('BacktestSettingsForm', () => {
  beforeEach(() => {
    // Clear console.log mocks if any were set up for API calls
    jest.spyOn(console, 'log').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('renders all form sections and initial values', () => {
    render(<BacktestSettingsForm />);
    expect(screen.getByText('自動売買システム バックテスト')).toBeInTheDocument();
    expect(screen.getByText('1. データと期間設定')).toBeInTheDocument();
    expect(screen.getByText('2. シミュレーション条件')).toBeInTheDocument();
    expect(screen.getByText('3. 戦略パラメータ (適応型短期タートルシステム)')).toBeInTheDocument();

    // Check one initial value as an example
    expect(screen.getByLabelText(/初期口座資金/i)).toHaveValue(1000000);
    expect(screen.getByLabelText(/スプレッド/i)).toHaveValue(1.0);
    // Add more checks for other initial values if necessary
  });

  test('updates state on input change (e.g., initial capital)', () => {
    render(<BacktestSettingsForm />);
    const initialCapitalInput = screen.getByLabelText(/初期口座資金/i);
    act(() => {
      fireEvent.change(initialCapitalInput, { target: { value: '2000000' } });
    });
    expect(initialCapitalInput).toHaveValue(2000000);
  });

  test('displays validation error for invalid numeric input', () => {
    render(<BacktestSettingsForm />);
    const spreadInput = screen.getByLabelText(/スプレッド/i);
    act(() => {
      fireEvent.change(spreadInput, { target: { value: 'abc' } });
    });
    expect(screen.getByText('スプレッド must be a valid number.')).toBeInTheDocument();
  });

  test('clears validation error when input becomes valid', () => {
    render(<BacktestSettingsForm />);
    const spreadInput = screen.getByLabelText(/スプレッド/i);
    act(() => {
      fireEvent.change(spreadInput, { target: { value: 'abc' } }); // Invalid
    });
    expect(screen.getByText('スプレッド must be a valid number.')).toBeInTheDocument();
    act(() => {
      fireEvent.change(spreadInput, { target: { value: '1.5' } }); // Valid
    });
    expect(screen.queryByText('スプレッド must be a valid number.')).not.toBeInTheDocument();
  });

  test('reset button clears inputs and errors', () => {
    render(<BacktestSettingsForm />);
    const initialCapitalInput = screen.getByLabelText(/初期口座資金/i);
    act(() => {
      fireEvent.change(initialCapitalInput, { target: { value: 'abc' } }); // Cause an error
    });
    expect(screen.getByText('初期口座資金 must be a valid number.')).toBeInTheDocument();

    act(() => {
      fireEvent.change(initialCapitalInput, { target: { value: '1200000' } }); // Change value
    });
    expect(initialCapitalInput).toHaveValue(1200000);

    const resetButton = screen.getByRole('button', { name: /パラメータをデフォルト値に戻す/i });
    act(() => {
      fireEvent.click(resetButton);
    });

    expect(initialCapitalInput).toHaveValue(1000000); // Back to default
    expect(screen.queryByText('初期口座資金 must be a valid number.')).not.toBeInTheDocument(); // Error cleared
  });

  test('"Run Backtest" button performs validation and shows executing state', async () => {
    render(<BacktestSettingsForm />);
    const executeButton = screen.getByRole('button', { name: /バックテストを実行する/i });

    // Test case 1: Validation fails
    const spreadInput = screen.getByLabelText(/スプレッド/i);
    act(() => {
      fireEvent.change(spreadInput, { target: { value: '' } }); // Invalid: empty
    });
    act(() => {
      fireEvent.click(executeButton);
    });
    expect(screen.getByText('スプレッド must be a valid number.')).toBeInTheDocument();
    expect(executeButton).not.toBeDisabled();
    expect(executeButton).toHaveTextContent('バックテストを実行する');

    // Test case 2: Validation passes
    act(() => {
      fireEvent.change(spreadInput, { target: { value: '1.5' } }); // Valid
    });
    expect(screen.queryByText('スプレッド must be a valid number.')).not.toBeInTheDocument();

    act(() => {
      fireEvent.click(executeButton);
    });

    // Check for executing state
    expect(executeButton).toBeDisabled();
    expect(executeButton).toHaveTextContent('実行中...');
    expect(screen.getByLabelText(/初期口座資金/i)).toBeDisabled(); // Example input

    // Wait for the mock API call (setTimeout) to finish
    await waitFor(() => {
      expect(executeButton).not.toBeDisabled();
      expect(executeButton).toHaveTextContent('バックテストを実行する');
      expect(screen.getByLabelText(/初期口座資金/i)).not.toBeDisabled();
    }, { timeout: 2500 }); // Timeout should be longer than the setTimeout in the component
  });
   test('all inputs are disabled during execution', async () => {
    render(<BacktestSettingsForm />);
    const executeButton = screen.getByRole('button', { name: /バックテストを実行する/i });

    // Ensure form is valid before clicking execute
    // (Assuming default values are valid, or set them to valid ones if not)
    // For example, if date pickers need values:
    // fireEvent.change(screen.getByTestId('start-date'), { target: { value: '2023-01-01' } });
    // fireEvent.change(screen.getByTestId('end-date'), { target: { value: '2023-12-31' } });

    act(() => {
      fireEvent.click(executeButton);
    });

    expect(executeButton).toBeDisabled();
    // Check a few inputs
    expect(screen.getByLabelText(/初期口座資金/i)).toBeDisabled();
    expect(screen.getByLabelText(/スプレッド/i)).toBeDisabled();
    expect(screen.getByRole('button', { name: /パラメータをデフォルト値に戻す/i })).toBeDisabled();
    expect(screen.getByTestId('file-upload')).toBeDisabled();
    expect(screen.getByTestId('start-date')).toBeDisabled();
    expect(screen.getByTestId('end-date')).toBeDisabled();


    await waitFor(() => {
      expect(executeButton).not.toBeDisabled();
    }, { timeout: 2500 });
  });
});
