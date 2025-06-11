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
// jest.mock('./FileUpload', () => ({ disabled, onFileSelect }) => <input type="file" data-testid="file-upload" disabled={disabled} onChange={onFileSelect} />); // Removed
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
  let mockDataFilesFetch;
  let mockRunBacktestFetch;
  let mockRunBacktestFailureFetch;
  let mockRunBacktestDelayedFetch;
  let resolveRunBacktestPromise;


  beforeEach(() => {
    jest.spyOn(console, 'log').mockImplementation(() => {});
    originalFetch = global.fetch;

    // Setup individual mocks for fetch calls
    // Ensure all potentially expected files are available for waitForInitialLoad variations
    mockDataFilesFetch = jest.fn(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        files: [
          { name: 'sample.csv', size: 100, created_at: '2023-01-01T00:00:00Z' },
          { name: 'file1.csv', size: 100, created_at: '2023-01-01T00:00:00Z' },
          { name: 'file2.csv', size: 200, created_at: '2023-01-02T00:00:00Z' },
        ]
      })
    }));
    mockRunBacktestFetch = jest.fn(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ job_id: 'test-job-id-success' })
    }));
    mockRunBacktestFailureFetch = jest.fn(() => Promise.resolve({
      ok: false, status: 500, text: () => Promise.resolve('Internal Server Error')
    }));
    mockRunBacktestDelayedFetch = jest.fn(() => new Promise(resolve => {
      resolveRunBacktestPromise = resolve;
    }));

    // Default fetch implementation routes to appropriate mock
    global.fetch = jest.fn(url => {
      if (url.includes('/api/data/files')) {
        return mockDataFilesFetch();
      }
      if (url.includes('/api/backtest/run')) {
        // This default might be overridden in specific tests if they use a different run mock
        return mockRunBacktestFetch();
      }
      return Promise.resolve({ ok: false, text: () => Promise.resolve('Unhandled fetch call') });
    });

    mockNavigate.mockClear();
  });

  afterEach(() => {
    jest.restoreAllMocks();
    global.fetch = originalFetch;
  });

  // Helper function for robust initial load wait
  const waitForInitialLoad = async (options = { expectedFile: 'sample.csv' }) => {
    await waitFor(() => {
      expect(mockDataFilesFetch).toHaveBeenCalled(); // From beforeEach setup
      if (options.expectedFile) {
        expect(screen.getByRole('option', { name: options.expectedFile })).toBeInTheDocument();
      }
      // Check that no data fetch error message is displayed initially
      expect(screen.queryByText(/Failed to fetch data files/i)).not.toBeInTheDocument();
    });
  };

  // Helper function for selecting a file and waiting for state update
  const selectFileAndWait = async (fileName) => {
    const fileSelect = screen.getByRole('combobox', { name: /select data file/i });
    await act(async () => {
      fireEvent.change(fileSelect, { target: { value: fileName } });
    });
    await waitFor(() => {
      expect(fileSelect).toHaveValue(fileName);
      // Ensure the "Please select a data file" error is cleared if it was present
      expect(screen.queryByText('Please select a data file to use for the backtest.')).not.toBeInTheDocument();
    });
  };

  test('renders all form sections and initial values', async () => {
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
    await waitForInitialLoad(); // Use helper

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
    // Override default fetch for /api/backtest/run for this test if needed, but default is success.
    // mockRunBacktestFetch is already set for success by default in beforeEach.

    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
    await waitForInitialLoad(); // Use helper

    const executeButton = screen.getByRole('button', { name: /バックテストを実行する/i });

    // Test case 1: Validation fails (e.g. spread)
    const spreadInput = screen.getByLabelText(/スプレッド/i);
    fireEvent.change(spreadInput, { target: { value: '' } }); // Invalid: empty
    fireEvent.click(executeButton);

    expect(screen.getByText('スプレッド must be a valid number.')).toBeInTheDocument();
    expect(mockRunBacktestFetch).not.toHaveBeenCalled();
    expect(mockNavigate).not.toHaveBeenCalled();

    // Test case 2: Validation passes, API call succeeds
    fireEvent.change(spreadInput, { target: { value: '1.5' } }); // Valid
    await waitFor(() => expect(screen.queryByText('スプレッド must be a valid number.')).not.toBeInTheDocument());

    await selectFileAndWait('sample.csv'); // Use helper

    // Now click execute
    await act(async () => {
      fireEvent.click(executeButton);
    });

    await waitFor(() => expect(mockRunBacktestFetch).toHaveBeenCalledTimes(1));
    expect(mockRunBacktestFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/backtest/run',
      expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('"data_file_name":"sample.csv"')
      })
    );

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/loading/test-job-id-success', expect.anything()));
    expect(executeButton).not.toBeDisabled();
    expect(executeButton).toHaveTextContent('バックテストを実行する');
  });

  test('"Run Backtest" button shows error message on API failure', async () => {
    // Crucially, override global.fetch for this test
    global.fetch.mockImplementation(url => {
      if (url.includes('/api/data/files')) return mockDataFilesFetch();
      if (url.includes('/api/backtest/run')) return mockRunBacktestFailureFetch(); // Use failure mock
      return Promise.resolve({ ok: false, text: () => 'Unhandled fetch' });
    });

    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
    await waitForInitialLoad(); // Use helper

    await selectFileAndWait('sample.csv'); // Use helper

    const executeButton = screen.getByRole('button', { name: /バックテストを実行する/i });
    await act(async () => {
      fireEvent.click(executeButton);
    });

    await waitFor(() => expect(mockRunBacktestFailureFetch).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByText(/バックテストの開始に失敗しました。サーバーエラー: 500 - Internal Server Error/i)).toBeInTheDocument());
    expect(mockNavigate).not.toHaveBeenCalled();
    expect(executeButton).not.toBeDisabled();
  });

  test('all inputs are disabled during execution', async () => {
    // Override global.fetch for this test
    global.fetch.mockImplementation(url => {
      if (url.includes('/api/data/files')) return mockDataFilesFetch();
      if (url.includes('/api/backtest/run')) return mockRunBacktestDelayedFetch(); // Use delayed mock
      return Promise.resolve({ ok: false, text: () => 'Unhandled fetch' });
    });

    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
    await waitForInitialLoad(); // Use helper

    await selectFileAndWait('sample.csv'); // Use helper

    const executeButton = screen.getByRole('button', { name: /バックテストを実行する/i });
    // For this specific test, clicking executeButton does not need to be wrapped in act
    // because we want to check the immediate synchronous state change of isExecuting
    // and then await the button text change. The subsequent promise resolution *is* wrapped in act.
    fireEvent.click(executeButton);

    const executingButton = await screen.findByRole('button', { name: /実行中.../i });
    expect(executingButton).toBeDisabled();

    expect(screen.getByLabelText(/初期口座資金/i)).toBeDisabled();
    expect(screen.getByLabelText(/スプレッド/i)).toBeDisabled();
    expect(screen.getByRole('combobox', { name: /select data file/i })).toBeDisabled();
    expect(screen.getByTestId('start-date')).toBeDisabled();
    expect(screen.getByTestId('end-date')).toBeDisabled();
    expect(screen.getByRole('button', { name: /パラメータをデフォルト値に戻す/i })).toBeDisabled();

    // Resolve the delayed fetch
    await act(async () => {
      resolveRunBacktestPromise({ ok: true, json: () => Promise.resolve({ job_id: 'test-job-id-disabled' }) });
    });

    await waitFor(() => expect(screen.getByRole('button', { name: /バックテストを実行する/i })).not.toBeDisabled());
    expect(mockNavigate).toHaveBeenCalledWith('/loading/test-job-id-disabled', expect.anything());
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
      // This test uses mockFilesData which has file1.csv, file2.csv
      // So, we override the /api/data/files part of the global fetch for this test.
      global.fetch.mockImplementation(url => {
        if (url.includes('/api/data/files')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(mockFilesData) });
        }
        // /api/backtest/run should use the default from beforeEach (mockRunBacktestFetch)
        // or be explicitly set if a different run behavior is needed.
        if (url.includes('/api/backtest/run')) return mockRunBacktestFetch();
        return Promise.resolve({ ok: false, text: () => 'Unhandled fetch' });
      });

      render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
      await waitForInitialLoad({ expectedFile: 'file1.csv' }); // Use helper

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
      global.fetch.mockImplementation(url => { // Override for this test
        if (url.includes('/api/data/files')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(mockFilesData) });
        }
        if (url.includes('/api/backtest/run')) return mockRunBacktestFetch();
        return Promise.resolve({ ok: false, text: () => 'Unhandled fetch' });
      });
      render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
      await waitForInitialLoad({ expectedFile: 'file1.csv' });

      fillRequiredNumericInputs();
      const executeButton = screen.getByRole('button', { name: /バックテストを実行する/i });
      fireEvent.click(executeButton); // Attempt to submit without selecting a file

      expect(await screen.findByText('Please select a data file to use for the backtest.')).toBeInTheDocument();

      await selectFileAndWait('file1.csv'); // Use helper, this also asserts error is cleared
    });

    test('includes data_file_name in payload on execute when a file is selected', async () => {
      const mockSpecificRunFetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ job_id: 'job-123-payload-test' }) }));
      global.fetch.mockImplementation(url => { // Override for this test
        if (url.includes('/api/data/files')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(mockFilesData) });
        }
        if (url.includes('/api/backtest/run')) return mockSpecificRunFetch();
        return Promise.resolve({ ok: false, text: () => 'Unhandled fetch' });
      });

      render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
      await waitForInitialLoad({ expectedFile: 'file1.csv' });

      fillRequiredNumericInputs(); // Ensure other inputs are valid

      await selectFileAndWait('file1.csv'); // Use helper

      const executeButton = screen.getByRole('button', { name: /バックテストを実行する/i });
      await act(async () => {
        fireEvent.click(executeButton);
      });

      await waitFor(() => {
        expect(mockSpecificRunFetch).toHaveBeenCalled();
      });

      expect(mockSpecificRunFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/backtest/run',
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('"data_file_name":"file1.csv"'),
        })
      );
      // Also check other essential parts of the payload to ensure it's the correct call
       const parsedBody = JSON.parse(mockSpecificRunFetch.mock.calls[0][1].body);
       expect(parsedBody.data_file_name).toBe('file1.csv');
       expect(parsedBody.initial_capital).toBe(1000000); // Example default value check

      expect(mockNavigate).toHaveBeenCalledWith('/loading/job-123-payload-test', expect.anything());
    });
  });
});
