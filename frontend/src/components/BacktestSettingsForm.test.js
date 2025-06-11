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
    const initialExecuteButton = screen.getByRole('button', { name: /バックテストを実行する/i });

    // Ensure form is valid before clicking execute
    // (Assuming default values are valid)
    global.fetch.mockImplementationOnce(() => // Ensure fetch is mocked to resolve slowly or hang to check disabled state
      new Promise(resolve => setTimeout(() => resolve({
        ok: true,
        json: () => Promise.resolve({ job_id: 'test-job-id-disabled' })
      }), 100)) // Short delay to allow checking disabled state
    );

    // fireEvent.click is already wrapped in act by RTL for synchronous updates
    fireEvent.click(initialExecuteButton);

    // After the click, isExecuting should be true.
    // Wait for the button text to change and for it to be disabled.
    const executingButton = await screen.findByRole('button', { name: /実行中.../i });
    expect(executingButton).toBeDisabled();

    // Assert that other inputs are also disabled
    expect(screen.getByLabelText(/初期口座資金/i)).toBeDisabled();
    expect(screen.getByLabelText(/スプレッド/i)).toBeDisabled();
    expect(screen.getByRole('button', { name: /パラメータをデフォルト値に戻す/i })).toBeDisabled();
    expect(screen.getByTestId('file-upload')).toBeDisabled();
    expect(screen.getByTestId('start-date')).toBeDisabled();
    expect(screen.getByTestId('end-date')).toBeDisabled();

    // After fetch completes and component processes this (setIsExecuting(false) in finally).
    await waitFor(() => {
      // Button text should revert and it should be enabled
      const finalExecuteButton = screen.getByRole('button', { name: /バックテストを実行する/i });
      expect(finalExecuteButton).not.toBeDisabled();
      expect(mockNavigate).toHaveBeenCalledWith('/loading/test-job-id-disabled', {
        state: { jobId: 'test-job-id-disabled' },
      });
    });
  });

  // New describe block for Data File Selection Features
  describe('Data File Selection Features', () => {
    const mockFilesData = {
      files: [
        { name: 'file1.csv', size: 100, created_at: '2023-01-01T00:00:00Z' },
        { name: 'file2.csv', size: 200, created_at: '2023-01-02T00:00:00Z' },
      ],
      total_files: 2,
    };

    const fillRequiredNumericInputs = () => {
      // Helper to fill numeric inputs to pass their validation
      // Based on existing setup, default values might be valid.
      // If not, this function would set them.
      // For now, assume default values are valid or tests for numeric inputs cover changes.
      // Example:
      // fireEvent.change(screen.getByLabelText(/初期口座資金/i), { target: { value: '1000000' } });
      // fireEvent.change(screen.getByLabelText(/スプレッド/i), { target: { value: '1.0' } });
      // ... and so on for all required numeric fields.
      // For this test suite, we assume default values are fine unless a specific test changes one.
    };


    test('renders data file dropdown and populates options on successful fetch', async () => {
      global.fetch.mockImplementationOnce(() => // For /api/data/files
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockFilesData),
        })
      );
      render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);

      await waitFor(() => {
        expect(screen.getByLabelText('Select Data File:')).toBeInTheDocument();
      });

      const combobox = screen.getByRole('combobox', { name: /select data file/i });
      expect(combobox).toBeInTheDocument();

      expect(await screen.findByRole('option', { name: '-- Select a data file --' })).toBeInTheDocument();
      expect(await screen.findByRole('option', { name: 'file1.csv' })).toBeInTheDocument();
      expect(await screen.findByRole('option', { name: 'file2.csv' })).toBeInTheDocument();
    });

    test('shows error message if fetching data files fails', async () => {
      global.fetch.mockImplementationOnce(() => // For /api/data/files
        Promise.resolve({
          ok: false,
          status: 500,
          text: () => Promise.resolve('Server error fetching files'), // .text() for non-JSON error response
        })
      );
      render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);

      await waitFor(() => {
        expect(screen.getByText(/Failed to fetch data files. Status: 500/i)).toBeInTheDocument();
      });
    });

    test('validation prevents execution if no data file selected', async () => {
      global.fetch.mockImplementationOnce(() => // For /api/data/files
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockFilesData), // Assume files loaded
        })
      );
      render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
      await waitFor(() => { // Wait for file options to potentially load
        expect(screen.getByRole('option', { name: 'file1.csv' })).toBeInTheDocument();
      });

      fillRequiredNumericInputs(); // Ensure other fields are valid

      const executeButton = screen.getByRole('button', { name: /バックテストを実行する/i });
      fireEvent.click(executeButton);

      expect(await screen.findByText('Please select a data file to use for the backtest.')).toBeInTheDocument();
      // Check that fetch for backtest/run was not called.
      // The default mock in beforeEach is for backtest/run. We need to ensure it wasn't called for *this* interaction.
      // Check calls to fetch. If any call was to /api/backtest/run, this fails.
      const backtestRunCall = global.fetch.mock.calls.find(call => call[0].includes('/api/backtest/run'));
      expect(backtestRunCall).toBeUndefined();
    });

    test('selecting a file clears submit error related to file selection', async () => {
      global.fetch.mockImplementationOnce(() => // For /api/data/files
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockFilesData),
        })
      );
      render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
      await waitFor(() => {
        expect(screen.getByRole('option', { name: 'file1.csv' })).toBeInTheDocument();
      });

      fillRequiredNumericInputs();
      const executeButton = screen.getByRole('button', { name: /バックテストを実行する/i });
      fireEvent.click(executeButton); // Attempt to submit without selecting a file

      expect(await screen.findByText('Please select a data file to use for the backtest.')).toBeInTheDocument();

      const combobox = screen.getByRole('combobox', { name: /select data file/i });
      fireEvent.change(combobox, { target: { value: 'file1.csv' } });

      // The error message should be cleared upon changing the selection
      expect(screen.queryByText('Please select a data file to use for the backtest.')).not.toBeInTheDocument();
    });

    test('includes data_file_name in payload on execute when a file is selected', async () => {
      // Mock for /api/data/files
      global.fetch.mockImplementationOnce(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockFilesData),
        })
      );
      // Mock for /api/backtest/run specifically for this test to check payload
      const mockRunFetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ job_id: 'job-123-payload-test' }) }));
      global.fetch.mockImplementationOnce(mockRunFetch);


      render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
      await waitFor(() => expect(screen.getByRole('option', { name: 'file1.csv' })).toBeInTheDocument());

      fillRequiredNumericInputs(); // Ensure other inputs are valid

      const combobox = screen.getByRole('combobox', { name: /select data file/i });
      fireEvent.change(combobox, { target: { value: 'file1.csv' } });

      const executeButton = screen.getByRole('button', { name: /バックテストを実行する/i });
      await act(async () => {
        fireEvent.click(executeButton);
      });

      await waitFor(() => {
        expect(mockRunFetch).toHaveBeenCalled();
      });

      expect(mockRunFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/backtest/run',
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('"data_file_name":"file1.csv"'),
        })
      );
      // Also check other essential parts of the payload to ensure it's the correct call
       const parsedBody = JSON.parse(mockRunFetch.mock.calls[0][1].body);
       expect(parsedBody.data_file_name).toBe('file1.csv');
       expect(parsedBody.initial_capital).toBe(1000000); // Example default value check

      expect(mockNavigate).toHaveBeenCalledWith('/loading/job-123-payload-test', expect.anything());
    });
  });
});
