import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { BrowserRouter as Router } from 'react-router-dom'; // Needed for <Link>
import BacktestResultPage from './BacktestResultPage';

// Mock child components
jest.mock('./KpiSummary', () => () => <div data-testid="kpi-summary-mock">KpiSummary Mock</div>);
jest.mock('./AssetCurveGraph', () => () => <div data-testid="asset-curve-graph-mock">AssetCurveGraph Mock</div>);
jest.mock('./TradeHistoryTable', () => () => <div data-testid="trade-history-table-mock">TradeHistoryTable Mock</div>);

describe('BacktestResultPage', () => {
  beforeEach(() => {
    // Render BacktestResultPage within Router because it contains Link component
    render(
      <Router>
        <BacktestResultPage />
      </Router>
    );
  });

  it('renders the KpiSummary component', () => {
    expect(screen.getByTestId('kpi-summary-mock')).toBeInTheDocument();
    expect(screen.getByText('KpiSummary Mock')).toBeInTheDocument();
  });

  it('renders the AssetCurveGraph component', () => {
    expect(screen.getByTestId('asset-curve-graph-mock')).toBeInTheDocument();
    expect(screen.getByText('AssetCurveGraph Mock')).toBeInTheDocument();
  });

  it('renders the TradeHistoryTable component', () => {
    expect(screen.getByTestId('trade-history-table-mock')).toBeInTheDocument();
    expect(screen.getByText('TradeHistoryTable Mock')).toBeInTheDocument();
  });

  it('renders the page title "Backtest Results"', () => {
    expect(screen.getByRole('heading', { name: /Backtest Results/i })).toBeInTheDocument();
  });

  it('renders the "Back to Settings" link', () => {
    const link = screen.getByRole('link', { name: /Back to Settings/i });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', '/');
  });
});
