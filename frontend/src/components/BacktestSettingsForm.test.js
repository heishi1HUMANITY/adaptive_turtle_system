import React from 'react'; // Removed { act } as it's often implicitly handled or used more specifically
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'; // ensure act is imported
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
// jest.mock('./FileUpload', ...); // FileUpload is no longer used by BacktestSettingsForm
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
    // Mock global.fetch
    global.fetch = jest.fn();
    mockNavigate.mockClear(); // Clear mockNavigate calls before each test
    // Suppress console.log and console.error for cleaner test output
    jest.spyOn(console, 'log').mockImplementation(() => {});
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks(); // Restores fetch and console mocks
  });

  // Helper function to mock a successful file fetch
  const mockFilesFetchSuccess = (files = [{ name: 'default.csv', size: 100, created_at: new Date().toISOString() }]) => {
    global.fetch.mockImplementationOnce((url) => {
      if (url.includes('/api/data/files')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ files, total_files: files.length }),
        });
      }
      return Promise.resolve({ ok: false, json: () => Promise.resolve({ detail: "Unexpected fetch call" }) });
    });
  };

  // Helper function to mock a failed file fetch
  const mockFilesFetchFailure = (error = 'Failed to fetch') => {
    global.fetch.mockImplementationOnce((url) => {
       if (url.includes('/api/data/files')) {
        return Promise.reject(new Error(error));
      }
      return Promise.resolve({ ok: false, json: () => Promise.resolve({ detail: "Unexpected fetch call" }) });
    });
  };


  test('renders all form sections and initial values, handling file loading', async () => {
    mockFilesFetchSuccess([{ name: 'test_file.csv', size: 123, created_at: new Date().toISOString() }]);
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);

    // Wait for the files to be loaded and the select to be populated
    await waitFor(() => {
      expect(screen.getByLabelText(/Data File:/i)).toBeInTheDocument();
      expect(screen.getByDisplayValue('test_file.csv')).toBeInTheDocument();
    });

    expect(screen.getByText('自動売買システム バックテスト')).toBeInTheDocument();
    expect(screen.getByText('1. データと期間設定')).toBeInTheDocument();
    expect(screen.getByText('2. シミュレーション条件')).toBeInTheDocument();
    expect(screen.getByText('3. 戦略パラメータ (適応型短期タートルシステム)')).toBeInTheDocument();

    // Check one initial value as an example
    expect(screen.getByLabelText(/初期口座資金/i)).toHaveValue(1000000);
    expect(screen.getByLabelText(/スプレッド/i)).toHaveValue(1.0);
    // Add more checks for other initial values if necessary
  });

  test('updates state on input change (e.g., initial capital)', async () => {
    mockFilesFetchSuccess();
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
    await waitFor(() => expect(screen.getByLabelText(/Data File:/i)).toBeInTheDocument());

    const initialCapitalInput = screen.getByLabelText(/初期口座資金/i);
    act(() => {
      fireEvent.change(initialCapitalInput, { target: { value: '2000000' } });
    });
    expect(initialCapitalInput).toHaveValue(2000000);
  });

  test('displays validation error for invalid numeric input', async () => {
    mockFilesFetchSuccess();
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
    await waitFor(() => expect(screen.getByLabelText(/Data File:/i)).toBeInTheDocument());

    const spreadInput = screen.getByLabelText(/スプレッド/i);
    act(() => {
      fireEvent.change(spreadInput, { target: { value: 'abc' } });
    });
    expect(screen.getByText('スプレッド must be a valid number.')).toBeInTheDocument();
  });

  test('clears validation error when input becomes valid', async () => {
    mockFilesFetchSuccess();
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
    await waitFor(() => expect(screen.getByLabelText(/Data File:/i)).toBeInTheDocument());

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

  test('reset button clears inputs and errors, and resets selected file', async () => {
    mockFilesFetchSuccess([
      { name: 'file1.csv', size: 100, created_at: new Date().toISOString() },
      { name: 'file2.csv', size: 200, created_at: new Date().toISOString() },
    ]);
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
    await waitFor(() => expect(screen.getByDisplayValue('file1.csv')).toBeInTheDocument());
    const initialCapitalInput = screen.getByLabelText(/初期口座資金/i);
    const dataFileInput = screen.getByLabelText(/Data File:/i);

    // Change some values and cause an error
    act(() => {
      fireEvent.change(initialCapitalInput, { target: { value: 'abc' } }); // Error
      fireEvent.change(dataFileInput, { target: { value: 'file2.csv' } }); // Change selection
    });
    expect(screen.getByText('初期口座資金 must be a valid number.')).toBeInTheDocument();
    expect(dataFileInput).toHaveValue('file2.csv');
    act(() => {
      fireEvent.change(initialCapitalInput, { target: { value: '1200000' } }); // Valid value
    });
    expect(initialCapitalInput).toHaveValue(1200000);


    const resetButton = screen.getByRole('button', { name: /パラメータをデフォルト値に戻す/i });
    act(() => {
      fireEvent.click(resetButton);
    });

    expect(initialCapitalInput).toHaveValue(1000000); // Back to default
    expect(screen.queryByText('初期口座資金 must be a valid number.')).not.toBeInTheDocument(); // Error cleared
    // Selected file should reset to the first one in the list
    await waitFor(() => {
        expect(dataFileInput).toHaveValue('file1.csv');
    });
  });


  test('"Run Backtest" button performs validation, calls fetch, and navigates on success', async () => {
    mockFilesFetchSuccess([{ name: 'sample.csv', size: 123, created_at: new Date().toISOString() }]);
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
    await waitFor(() => expect(screen.getByLabelText(/Data File:/i)).toBeInTheDocument());
    const executeButton = screen.getByRole('button', { name: /バックテストを実行する/i });

    // Test case 1: Validation fails (e.g. numeric input)
    const spreadInput = screen.getByLabelText(/スプレッド/i);
    act(() => {
      fireEvent.change(spreadInput, { target: { value: '' } }); // Invalid: empty
    });
    act(() => {
      fireEvent.click(executeButton);
    });
    expect(screen.getByText('スプレッド must be a valid number.')).toBeInTheDocument();
    // Fetch for files was called, but not for backtest/run
    expect(global.fetch).toHaveBeenCalledTimes(1); // Only the files API call
    expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/api/data/files', expect.any(Object));
    expect(mockNavigate).not.toHaveBeenCalled();


    // Test case 2: Validation passes, API call succeeds
    act(() => {
      fireEvent.change(spreadInput, { target: { value: '1.5' } }); // Make it valid
    });
    expect(screen.queryByText('スプレッド must be a valid number.')).not.toBeInTheDocument();

    // Mock the backtest run API call specifically
    global.fetch.mockImplementationOnce((url) => {
      if (url.includes('/api/backtest/run')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ job_id: 'test-job-id-success' }),
        });
      }
      // This should not happen if files are already loaded
      return Promise.resolve({ ok: false, json: () => Promise.resolve({detail: "Unexpected fetch call"})});
    });


    await act(async () => {
      fireEvent.click(executeButton);
    });

    // Files API (1) + Backtest API (1) = 2 calls
    expect(global.fetch).toHaveBeenCalledTimes(2);
    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/backtest/run',
      expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('"data_file_name":"sample.csv"') // Ensure data_file_name is in payload
      })
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
    mockFilesFetchSuccess([{ name: 'error_case.csv', size: 123, created_at: new Date().toISOString() }]);
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
    await waitFor(() => expect(screen.getByLabelText(/Data File:/i)).toBeInTheDocument());

    const executeButton = screen.getByRole('button', { name: /バックテストを実行する/i });

    // Ensure form is valid (default values are assumed valid, file is selected)
    // Mock the backtest run API call to fail
    global.fetch.mockImplementationOnce((url) => {
      if (url.includes('/api/backtest/run')) {
        return Promise.resolve({
          ok: false,
          status: 500,
          text: () => Promise.resolve('Internal Server Error'),
        });
      }
      return Promise.resolve({ ok: false, json: () => Promise.resolve({detail: "Unexpected fetch call"})});
    });


    await act(async () => {
      fireEvent.click(executeButton);
    });

    expect(global.fetch).toHaveBeenCalledTimes(2); // Files API + Backtest API
    await waitFor(() => {
      expect(screen.getByText(/バックテストの開始に失敗しました。サーバーエラー: 500 - Internal Server Error/i)).toBeInTheDocument();
    });
    expect(mockNavigate).not.toHaveBeenCalled();
    expect(executeButton).not.toBeDisabled();
  });


   test('all inputs are disabled during execution', async () => {
    mockFilesFetchSuccess([{ name: 'disable_test.csv', size: 123, created_at: new Date().toISOString() }]);
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
    await waitFor(() => expect(screen.getByLabelText(/Data File:/i)).toBeInTheDocument());

    const initialExecuteButton = screen.getByRole('button', { name: /バックテストを実行する/i });

    // Mock the backtest run API to resolve after a delay
    global.fetch.mockImplementationOnce((url) => {
      if (url.includes('/api/backtest/run')) {
        return new Promise(resolve => setTimeout(() => resolve({
          ok: true,
          json: () => Promise.resolve({ job_id: 'test-job-id-disabled' })
        }), 50)); // Short delay
      }
      return Promise.resolve({ ok: false, json: () => Promise.resolve({detail: "Unexpected fetch call"})});
    });

    // No need to wrap fireEvent.click in act if it leads to async operations tested with findBy* or waitFor
    fireEvent.click(initialExecuteButton);

    // Wait for the button to change to "実行中..." and be disabled
    const executingButton = await screen.findByRole('button', { name: /実行中.../i });
    expect(executingButton).toBeDisabled();

    // Assert that other inputs are also disabled
    expect(screen.getByLabelText(/初期口座資金/i)).toBeDisabled();
    expect(screen.getByLabelText(/スプレッド/i)).toBeDisabled();
    expect(screen.getByLabelText(/Data File:/i)).toBeDisabled();
    expect(screen.getByRole('button', { name: /パラメータをデフォルト値に戻す/i })).toBeDisabled();
    // DateRangePicker inputs (using data-testid from its mock)
    expect(screen.getByTestId('start-date')).toBeDisabled();
    expect(screen.getByTestId('end-date')).toBeDisabled();


    // Wait for the API call to complete and the component to re-enable inputs
    await waitFor(() => {
      const finalExecuteButton = screen.getByRole('button', { name: /バックテストを実行する/i });
      expect(finalExecuteButton).not.toBeDisabled();
    }, { timeout: 200 }); // Increased timeout to accommodate the 50ms delay in fetch

    // Also check navigation after completion
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/loading/test-job-id-disabled', {
        state: { jobId: 'test-job-id-disabled' },
      });
    });
  });

  test('displays error if fetching files fails', async () => {
    mockFilesFetchFailure('Network Error');
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);

    await waitFor(() => {
      expect(screen.getByText(/Error fetching data files: Failed to fetch data files: undefined Network Error/i)).toBeInTheDocument();
    });
    // Dropdown might show a "failed to load" message or be empty
    const dataFileInput = screen.getByLabelText(/Data File:/i);
    expect(dataFileInput.options.length).toBe(1); // e.g., "Failed to load files"
    expect(dataFileInput.options[0].text).toMatch(/Failed to load files/i); // or "Loading..." if error not specific
  });

  test('shows message if no data files are available', async () => {
    mockFilesFetchSuccess([]); // No files
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);

    await waitFor(() => {
      expect(screen.getByText('No data files available on the server.')).toBeInTheDocument();
    });
    const dataFileInput = screen.getByLabelText(/Data File:/i);
     // The select might have a "Loading files..." or similar if no files and no error.
    // Based on current implementation, it shows "Loading files..." if availableDataFiles is empty and no error.
    // Let's adjust the component to show a specific "No files" message in the dropdown.
    // For now, we check the error message display.
    expect(dataFileInput.options[0].text).toMatch(/Loading files.../i); // Or whatever the placeholder is
  });

  test('"Run Backtest" button shows error if no data file is selected', async () => {
    // Mock fetch to return no files, so nothing is selected by default
    mockFilesFetchSuccess([]);
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);

    await waitFor(() => {
      // Ensure the "No data files available" message or similar is shown to confirm file loading attempt finished
      expect(screen.getByText(/No data files available on the server./i)).toBeInTheDocument();
    });

    const executeButton = screen.getByRole('button', { name: /バックテストを実行する/i });
    act(() => {
      fireEvent.click(executeButton);
    });

    // Expect a specific error message for no file selected
    await waitFor(() => {
        expect(screen.getByText('Please select a data file for the backtest.')).toBeInTheDocument();
    });
    // Fetch for /api/backtest/run should not have been called
    // The initial call for /api/data/files is expected.
    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/api/data/files', expect.any(Object));
    expect(mockNavigate).not.toHaveBeenCalled();
  });

});
