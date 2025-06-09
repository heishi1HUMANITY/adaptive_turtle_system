import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import BacktestResultPage from './BacktestResultPage';

// Mock child components
jest.mock('./KpiSummary', () => ({ kpiData }) => <div data-testid="kpi-summary-mock">KpiSummary Mock: {JSON.stringify(kpiData)}</div>);
jest.mock('./AssetCurveGraph', () => ({ assetCurveData }) => <div data-testid="asset-curve-graph-mock">AssetCurveGraph Mock: {assetCurveData.length} points</div>);
jest.mock('./TradeHistoryTable', () => ({ tradeHistoryData }) => <div data-testid="trade-history-table-mock">TradeHistoryTable Mock: {tradeHistoryData.length} trades</div>);

const renderWithRouter = (ui, { initialEntries = ['/results'], routePath = '/results', state = null } = {}) => {
  if (state) {
    initialEntries = [{ pathname: initialEntries[0], state }];
  }
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route path={routePath} element={ui} />
      </Routes>
    </MemoryRouter>
  );
};

describe('BacktestResultPage', () => {
  let originalFetch;

  beforeEach(() => {
    originalFetch = global.fetch;
    global.fetch = jest.fn(); // Default mock for fetch
  });

  afterEach(() => {
    global.fetch = originalFetch;
    jest.restoreAllMocks(); // Restore any other mocks if created in tests
  });

  it('renders loading state initially', () => {
    global.fetch.mockImplementationOnce(() => new Promise(() => {})); // Ensure fetch doesn't resolve
    renderWithRouter(<BacktestResultPage />, { state: { jobId: 'test-job-id' }});
    expect(screen.getByText(/Loading results.../i)).toBeInTheDocument();
  });

  it('displays error when jobId is missing', async () => {
    renderWithRouter(<BacktestResultPage /> ); // No state with jobId
    await waitFor(() => {
      expect(screen.getByText(/結果の読み込みに失敗しました。有効なジョブIDが指定されていません。設定ページから再度バックテストを実行してください。/i)).toBeInTheDocument();
    });
  });

  it('fetches and displays results successfully', async () => {
    const mockJobId = 'test-job-id-success';
    const mockKpiData = { totalNetProfit: 1000, winRate: 0.75 };
    const mockEquityCurve = [{ timestamp: '2023-01-01', equity: 10000 }];
    const mockTradeLog = [{ order_id: '1', symbol: 'BTCUSD', action: 'buy', quantity: 1, price: 30000, timestamp: '2023-01-01', realized_pnl: 0 }];

    global.fetch.mockImplementationOnce(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          results: mockKpiData,
          equity_curve: mockEquityCurve,
          trade_log: mockTradeLog,
        }),
      })
    );

    renderWithRouter(<BacktestResultPage />, { state: { jobId: mockJobId } });

    await waitFor(() => {
      expect(screen.getByTestId('kpi-summary-mock')).toBeInTheDocument();
      expect(screen.getByTestId('asset-curve-graph-mock')).toBeInTheDocument();
      expect(screen.getByTestId('trade-history-table-mock')).toBeInTheDocument();
    });

    expect(screen.getByText(/KpiSummary Mock/i)).toHaveTextContent(JSON.stringify(mockKpiData));
    expect(screen.getByText(/AssetCurveGraph Mock/i)).toHaveTextContent('1 points');
    // For trade history, we check length, and the transformation logic is tested implicitly by data being passed.
    expect(screen.getByText(/TradeHistoryTable Mock/i)).toHaveTextContent('1 trades');
    expect(global.fetch).toHaveBeenCalledWith(`http://localhost:8000/api/backtest/results/${mockJobId}`);
  });

  it('displays API error message when fetch is not ok', async () => {
    const mockJobId = 'test-job-id-apifail';
    global.fetch.mockImplementationOnce(() =>
      Promise.resolve({
        ok: false,
        status: 404,
        text: () => Promise.resolve(JSON.stringify({ detail: 'Job not found' })),
      })
    );

    renderWithRouter(<BacktestResultPage />, { state: { jobId: mockJobId } });

    await waitFor(() => {
      expect(screen.getByText(/サーバーからのエラー: Job not found \(ステータス: 404\)/i)).toBeInTheDocument();
    });
  });

  it('displays network error message when fetch fails', async () => {
    const mockJobId = 'test-job-id-networkfail';
    global.fetch.mockImplementationOnce(() => Promise.reject(new Error('Network request failed')));

    renderWithRouter(<BacktestResultPage />, { state: { jobId: mockJobId } });

    await waitFor(() => {
      expect(screen.getByText(/結果の読み込み中に通信エラーが発生しました。ネットワーク状況を確認するか、しばらくしてから再度お試しください。/i)).toBeInTheDocument();
    });
  });


  it('renders the page title "Backtest Results" and "Back to Settings" link on successful load', async () => {
    global.fetch.mockImplementationOnce(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ results: {}, equity_curve: [], trade_log: [] }),
      })
    );
    renderWithRouter(<BacktestResultPage />, { state: { jobId: 'test-job-static' } });

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Backtest Results/i })).toBeInTheDocument();
    });
    const link = screen.getByRole('link', { name: /Back to Settings/i });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', '/');
  });
});
