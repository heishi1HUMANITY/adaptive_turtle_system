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

    mockDataFilesFetch = jest.fn(() => Promise.resolve({
      ok: true,
      status: 200,
      json: async () => ({
        files: [
          { name: 'sample.csv', size: 100, created_at: '2023-01-01T00:00:00Z' },
          { name: 'file1.csv', size: 100, created_at: '2023-01-01T00:00:00Z' },
          { name: 'file2.csv', size: 200, created_at: '2023-01-02T00:00:00Z' },
        ]
      }),
      text: async () => JSON.stringify({ files: [ /* as above */ ] })
    }));
    mockRunBacktestFetch = jest.fn(() => Promise.resolve({
      ok: true,
      status: 200,
      json: async () => ({ job_id: 'test-job-id-success' }),
      text: async () => JSON.stringify({ job_id: 'test-job-id-success' })
    }));
    mockRunBacktestFailureFetch = jest.fn(() => Promise.resolve({
      ok: false, status: 500, text: async () => 'Internal Server Error', json: async () => ({detail: 'Internal Server Error'})
    }));
    mockRunBacktestDelayedFetch = jest.fn(() => new Promise(resolve => {
      resolveRunBacktestPromise = resolve;
    }));

    mockDataFilesFetch.mockClear();
    mockRunBacktestFetch.mockClear();
    mockRunBacktestFailureFetch.mockClear();
    mockRunBacktestDelayedFetch.mockClear();

    global.fetch = jest.fn();
    global.fetch.mockImplementation(async (url) => {
      if (url.includes('/api/data/files')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            files: [
              { name: 'sample.csv', size: 100, created_at: '2023-01-01T00:00:00Z' },
              { name: 'file1.csv', size: 100, created_at: '2023-01-01T00:00:00Z' },
              { name: 'file2.csv', size: 200, created_at: '2023-01-02T00:00:00Z' },
            ]
          }),
          text: async () => JSON.stringify({ files: [ /* as above */ ]})
        });
      }
      if (url.includes('/api/backtest/run')) {
        return mockRunBacktestFetch();
      }
      return Promise.resolve({
        ok: false,
        status: 404,
        text: async () => 'Unhandled fetch URL in default mock',
        json: async () => ({ detail: 'Unhandled fetch URL in default mock' })
      });
    });

    mockNavigate.mockClear();
  });

  afterEach(() => {
    jest.restoreAllMocks();
    global.fetch = originalFetch;
  });

  const waitForInitialLoad = async (options = { expectedFile: 'sample.csv' }) => {
    await waitFor(() => {
      const dataFilesCall = global.fetch.mock.calls.find(call => call[0].includes('/api/data/files'));
      expect(dataFilesCall).not.toBeUndefined();
      if (options.expectedFile) {
        expect(screen.getByRole('option', { name: options.expectedFile })).toBeInTheDocument();
      }
      expect(screen.queryByText(/Failed to fetch data files/i)).not.toBeInTheDocument();
    });
  };

  const selectFileAndWait = async (fileName) => {
    const fileSelect = screen.getByRole('combobox', { name: /select data file/i });
    await act(async () => {
      fireEvent.change(fileSelect, { target: { value: fileName } });
    });
    await waitFor(() => {
      expect(fileSelect).toHaveValue(fileName);
      expect(screen.queryByText('Please select a data file to use for the backtest.')).not.toBeInTheDocument();
    });
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0));
    });
  };

  test('renders all form sections and initial values', async () => {
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
    await waitForInitialLoad();
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });

    expect(screen.getByText('自動売買システム バックテスト')).toBeInTheDocument();
    expect(screen.getByText('1. データと期間設定')).toBeInTheDocument();
    expect(screen.getByText('2. シミュレーション条件')).toBeInTheDocument();
    expect(screen.getByText('3. 戦略パラメータ (適応型短期タートルシステム)')).toBeInTheDocument();
    expect(screen.getByLabelText(/初期口座資金/i)).toHaveValue(1000000);
    expect(screen.getByLabelText(/スプレッド/i)).toHaveValue(1.0);
  });

  test('updates state on input change (e.g., initial capital)', async () => {
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
    await waitForInitialLoad();
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
    const initialCapitalInput = screen.getByLabelText(/初期口座資金/i);
    act(() => {
      fireEvent.change(initialCapitalInput, { target: { value: '2000000' } });
    });
    expect(initialCapitalInput).toHaveValue(2000000);
  });

  test('displays validation error for invalid numeric input', async () => {
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
    await waitForInitialLoad();
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
    const spreadInput = screen.getByLabelText(/スプレッド/i);
    act(() => {
      fireEvent.change(spreadInput, { target: { value: 'abc' } });
    });
    expect(screen.getByText('スプレッド must be a valid number.')).toBeInTheDocument();
  });

  test('clears validation error when input becomes valid', async () => {
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
    await waitForInitialLoad();
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
    const spreadInput = screen.getByLabelText(/スプレッド/i);
    act(() => {
      fireEvent.change(spreadInput, { target: { value: 'abc' } });
    });
    expect(screen.getByText('スプレッド must be a valid number.')).toBeInTheDocument();
    act(() => {
      fireEvent.change(spreadInput, { target: { value: '1.5' } });
    });
    expect(screen.queryByText('スプレッド must be a valid number.')).not.toBeInTheDocument();
  });

  test('reset button clears inputs and errors', async () => {
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
    await waitForInitialLoad();
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
    const initialCapitalInput = screen.getByLabelText(/初期口座資金/i);
    act(() => {
      fireEvent.change(initialCapitalInput, { target: { value: 'abc' } });
    });
    expect(screen.getByText('初期口座資金 must be a valid number.')).toBeInTheDocument();
    act(() => {
      fireEvent.change(initialCapitalInput, { target: { value: '1200000' } });
    });
    expect(initialCapitalInput).toHaveValue(1200000);
    const resetButton = screen.getByRole('button', { name: /パラメータをデフォルト値に戻す/i });
    act(() => {
      fireEvent.click(resetButton);
    });
    expect(initialCapitalInput).toHaveValue(1000000);
    expect(screen.queryByText('初期口座資金 must be a valid number.')).not.toBeInTheDocument();
  });

  test('"Run Backtest" button performs validation, calls fetch, and navigates on success', async () => {
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
    await waitForInitialLoad();
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });

    const executeButton = screen.getByRole('button', { name: /バックテストを実行する/i });
    const spreadInput = screen.getByLabelText(/スプレッド/i);
    fireEvent.change(spreadInput, { target: { value: '' } });
    fireEvent.click(executeButton);
    expect(screen.getByText('スプレッド must be a valid number.')).toBeInTheDocument();
    expect(mockRunBacktestFetch).not.toHaveBeenCalled();
    expect(mockNavigate).not.toHaveBeenCalled();

    fireEvent.change(spreadInput, { target: { value: '1.5' } });
    await waitFor(() => expect(screen.queryByText('スプレッド must be a valid number.')).not.toBeInTheDocument());
    await selectFileAndWait('sample.csv');

    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: /select data file/i })).toHaveValue('sample.csv');
    });

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
    global.fetch.mockImplementation(async (url) => {
      if (url.includes('/api/data/files')) {
        return Promise.resolve({
          ok: true, status: 200, json: async () => ({
            files: [{ name: 'sample.csv', size: 100, created_at: '2023-01-01T00:00:00Z' }]
          })
        });
      }
      if (url.includes('/api/backtest/run')) {
        return mockRunBacktestFailureFetch();
      }
      return Promise.resolve({ ok: false, status: 404, text: async () => 'Unhandled URL in test-specific mock' });
    });
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
    await waitForInitialLoad();
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
    await selectFileAndWait('sample.csv');
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
    global.fetch.mockImplementation(async (url) => {
      if (url.includes('/api/data/files')) {
        return Promise.resolve({
          ok: true, status: 200, json: async () => ({
            files: [{ name: 'sample.csv', size: 100, created_at: '2023-01-01T00:00:00Z' }]
          })
        });
      }
      if (url.includes('/api/backtest/run')) {
        return mockRunBacktestDelayedFetch();
      }
      return Promise.resolve({ ok: false, status: 404, text: async () => 'Unhandled URL in test-specific mock' });
    });
    render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
    await waitForInitialLoad();
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
    await selectFileAndWait('sample.csv');
    const executeButton = screen.getByRole('button', { name: /バックテストを実行する/i });
    fireEvent.click(executeButton);
    const executingButton = await screen.findByRole('button', { name: /実行中.../i });
    expect(executingButton).toBeDisabled();
    expect(screen.getByLabelText(/初期口座資金/i)).toBeDisabled();
    expect(screen.getByLabelText(/スプレッド/i)).toBeDisabled();
    expect(screen.getByRole('combobox', { name: /select data file/i })).toBeDisabled();
    expect(screen.getByTestId('start-date')).toBeDisabled();
    expect(screen.getByTestId('end-date')).toBeDisabled();
    expect(screen.getByRole('button', { name: /パラメータをデフォルト値に戻す/i })).toBeDisabled();
    await act(async () => {
      resolveRunBacktestPromise({ ok: true, json: async () => ({ job_id: 'test-job-id-disabled' }) });
    });
    await waitFor(() => expect(screen.getByRole('button', { name: /バックテストを実行する/i })).not.toBeDisabled());
    expect(mockNavigate).toHaveBeenCalledWith('/loading/test-job-id-disabled', expect.anything());
  });

  describe('Data File Selection Features', () => {
    const mockFilesData = {
      files: [
        { name: 'file1.csv', size: 100, created_at: '2023-01-01T00:00:00Z' },
        { name: 'file2.csv', size: 200, created_at: '2023-01-02T00:00:00Z' },
      ],
      total_files: 2,
    };
    const fillRequiredNumericInputs = () => {};

    test('renders data file dropdown and populates options on successful fetch', async () => {
      global.fetch.mockImplementation(async (url) => {
        if (url.includes('/api/data/files')) {
          return Promise.resolve({ ok: true, status: 200, json: async () => mockFilesData });
        }
        return Promise.resolve({ ok: false, status: 404, text: async () => 'Unhandled URL' });
      });
      render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
      await waitForInitialLoad({ expectedFile: 'file1.csv' });
      await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
      expect(screen.getByLabelText('Select Data File:')).toBeInTheDocument();
      const combobox = screen.getByRole('combobox', { name: /select data file/i });
      expect(combobox).toBeInTheDocument();
      expect(await screen.findByRole('option', { name: '-- Select a data file --' })).toBeInTheDocument();
      expect(await screen.findByRole('option', { name: 'file1.csv' })).toBeInTheDocument();
      expect(await screen.findByRole('option', { name: 'file2.csv' })).toBeInTheDocument();
    });

    test('shows error message if fetching data files fails', async () => {
      global.fetch.mockImplementation(async (url) => {
        if (url.includes('/api/data/files')) {
          return Promise.resolve({
            ok: false, status: 500, text: async () => 'Server error fetching files',
            json: async () => ({ detail: 'Server error fetching files' })
          });
        }
        return Promise.resolve({ ok: false, status: 404, text: async () => 'Unhandled URL' });
      });
      render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
      // No waitForInitialLoad here as it expects success. Wait for error directly.
      await waitFor(() => {
        expect(screen.getByText(/Failed to fetch data files. Status: 500/i)).toBeInTheDocument();
      });
    });

    test('validation prevents execution if no data file selected', async () => {
      global.fetch.mockImplementation(async (url) => {
        if (url.includes('/api/data/files')) {
           return Promise.resolve({ok:true, status:200, json: async () => ({files: mockFilesData.files })});
        }
        if (url.includes('/api/backtest/run')) {
          return mockRunBacktestFetch();
        }
        return Promise.resolve({ ok: false, status: 404, text: async () => 'Unhandled URL' });
      });
      render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
      await waitForInitialLoad({ expectedFile: 'file1.csv' });
      await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
      fillRequiredNumericInputs();
      const executeButton = screen.getByRole('button', { name: /バックテストを実行する/i });
      fireEvent.click(executeButton);
      expect(await screen.findByText('Please select a data file to use for the backtest.')).toBeInTheDocument();
      const backtestRunCall = global.fetch.mock.calls.find(call => call[0].includes('/api/backtest/run') && call[1]?.method === 'POST');
      expect(backtestRunCall).toBeUndefined();
    });

    test('selecting a file clears submit error related to file selection', async () => {
       global.fetch.mockImplementation(async (url) => {
         if (url.includes('/api/data/files')) {
           return Promise.resolve({ok:true, status:200, json: async () => ({files: mockFilesData.files})});
         }
         if (url.includes('/api/backtest/run')) {
           return mockRunBacktestFetch();
         }
         return Promise.resolve({ ok: false, status: 404, text: async () => 'Unhandled URL' });
      });
      render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
      await waitForInitialLoad({ expectedFile: 'file1.csv' });
      await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
      fillRequiredNumericInputs();
      const executeButton = screen.getByRole('button', { name: /バックテストを実行する/i });
      fireEvent.click(executeButton);
      expect(await screen.findByText('Please select a data file to use for the backtest.')).toBeInTheDocument();
      await selectFileAndWait('file1.csv');
    });

    test('includes data_file_name in payload on execute when a file is selected', async () => {
      const mockSpecificRunFetch = jest.fn(() => Promise.resolve({ ok: true, json: async () => ({ job_id: 'job-123-payload-test' }) }));
      global.fetch.mockImplementation(async (url) => {
        if (url.includes('/api/data/files')) {
           return Promise.resolve({ok:true, status:200, json: async () => ({files: mockFilesData.files})});
        }
        if (url.includes('/api/backtest/run')) {
          return mockSpecificRunFetch();
        }
        return Promise.resolve({ ok: false, status: 404, text: async () => 'Unhandled URL in test-specific mock' });
      });
      render(<MemoryRouter><BacktestSettingsForm /></MemoryRouter>);
      await waitForInitialLoad({ expectedFile: 'file1.csv' });
      await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
      fillRequiredNumericInputs();
      await selectFileAndWait('file1.csv');

      await waitFor(() => {
        expect(screen.getByRole('combobox', { name: /select data file/i })).toHaveValue('file1.csv');
      });

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
       const parsedBody = JSON.parse(mockSpecificRunFetch.mock.calls[0][1].body);
       expect(parsedBody.data_file_name).toBe('file1.csv');
       expect(parsedBody.initial_capital).toBe(1000000);
      expect(mockNavigate).toHaveBeenCalledWith('/loading/job-123-payload-test', expect.anything());
    });
  });
});
