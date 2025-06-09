import React, { act } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom'; // Import MemoryRouter
import BacktestSettingsForm from './BacktestSettingsForm';

// Mock useNavigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'), // use actual for all non-hook parts
  useNavigate: () => mockNavigate,
}));

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
  let originalFetch;

  beforeEach(() => {
    // Clear console.log mocks if any were set up for API calls
    jest.spyOn(console, 'log').mockImplementation(() => {});
    // Mock global.fetch and save the original
    originalFetch = global.fetch;
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ job_id: 'default-job-id' }),
      })
    );
    mockNavigate.mockClear(); // Clear mockNavigate calls before each test
  });

  afterEach(() => {
    jest.restoreAllMocks(); // This will restore console.log
    global.fetch = originalFetch; // Restore original fetch
  });

  test('renders all form sections and initial values', () => {
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
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
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
    const initialCapitalInput = screen.getByLabelText(/初期口座資金/i);
    act(() => {
      fireEvent.change(initialCapitalInput, { target: { value: '2000000' } });
    });
    expect(initialCapitalInput).toHaveValue(2000000);
  });

  test('displays validation error for invalid numeric input', () => {
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
    const spreadInput = screen.getByLabelText(/スプレッド/i);
    act(() => {
      fireEvent.change(spreadInput, { target: { value: 'abc' } });
    });
    expect(screen.getByText('スプレッド must be a valid number.')).toBeInTheDocument();
  });

  test('clears validation error when input becomes valid', () => {
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
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
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
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

  test('"Run Backtest" button performs validation, calls fetch, and navigates on success', async () => {
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
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
    expect(global.fetch).not.toHaveBeenCalled(); // Fetch should not be called
    expect(mockNavigate).not.toHaveBeenCalled();


    // Test case 2: Validation passes, API call succeeds
    act(() => {
      fireEvent.change(spreadInput, { target: { value: '1.5' } }); // Valid
    });
    expect(screen.queryByText('スプレッド must be a valid number.')).not.toBeInTheDocument();

    // Set up successful fetch mock for this specific call if different from default
    global.fetch.mockImplementationOnce(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ job_id: 'test-job-id-success' }),
      })
    );

    await act(async () => {
      fireEvent.click(executeButton);
    });

    expect(global.fetch).toHaveBeenCalledTimes(1); // Or more, if there were previous valid calls in other tests not cleared. Best to check specific call.
    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/backtest/run',
      expect.objectContaining({ method: 'POST' })
    );

    // Check for executing state (momentarily)
    // This is hard to test precisely without more complex state inspection or visual regression.
    // We know it sets isExecuting to true, then false.

    // Check navigation
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/loading/test-job-id-success', {
        state: { jobId: 'test-job-id-success' },
      });
    });

    // Button should be re-enabled after API call
    expect(executeButton).not.toBeDisabled();
    expect(executeButton).toHaveTextContent('バックテストを実行する');
  });

  test('"Run Backtest" button shows error message on API failure', async () => {
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
    const executeButton = screen.getByRole('button', { name: /バックテストを実行する/i });

    // Ensure form is valid
    const spreadInput = screen.getByLabelText(/スプレッド/i);
    act(() => {
      fireEvent.change(spreadInput, { target: { value: '1.5' } });
    });

    // Set up failed fetch mock
    global.fetch.mockImplementationOnce(() =>
      Promise.resolve({
        ok: false,
        status: 500,
        text: () => Promise.resolve('Internal Server Error'),
      })
    );

    await act(async () => {
      fireEvent.click(executeButton);
    });

    expect(global.fetch).toHaveBeenCalledTimes(1);
    await waitFor(() => {
      expect(screen.getByText(/バックテストの開始に失敗しました。サーバーエラー: 500 - Internal Server Error/i)).toBeInTheDocument();
    });
    expect(mockNavigate).not.toHaveBeenCalled();
    expect(executeButton).not.toBeDisabled();
  });


   test('all inputs are disabled during execution', async () => {
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
    const executeButton = screen.getByRole('button', { name: /バックテストを実行する/i });

    // Ensure form is valid before clicking execute
    // (Assuming default values are valid)
    global.fetch.mockImplementationOnce(() => // Ensure fetch is mocked to resolve slowly or hang to check disabled state
      new Promise(resolve => setTimeout(() => resolve({
        ok: true,
        json: () => Promise.resolve({ job_id: 'test-job-id-disabled' })
      }), 100)) // Short delay to allow checking disabled state
    );

    await act(async () => {
      fireEvent.click(executeButton);
      // Immediately after click, check disabled state
      expect(executeButton).toBeDisabled();
      expect(screen.getByLabelText(/初期口座資金/i)).toBeDisabled();
      expect(screen.getByLabelText(/スプレッド/i)).toBeDisabled();
      expect(screen.getByRole('button', { name: /パラメータをデフォルト値に戻す/i })).toBeDisabled();
      expect(screen.getByTestId('file-upload')).toBeDisabled();
      expect(screen.getByTestId('start-date')).toBeDisabled();
      expect(screen.getByTestId('end-date')).toBeDisabled();
    });

    // After fetch completes and component processes this.
    await waitFor(() => {
      expect(executeButton).not.toBeDisabled();
      expect(mockNavigate).toHaveBeenCalledWith('/loading/test-job-id-disabled', {
        state: { jobId: 'test-job-id-disabled' },
      });
    });
  });
});
