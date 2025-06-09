import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import KpiSummary from './KpiSummary';

describe('KpiSummary', () => {
  const dummyKpiData = {
    totalNetProfit: 12345,
    profitFactor: 2.1,
    maxDrawdown: -3000,
    winRate: 0.75,
  };

  it('renders KPI titles and values correctly', () => {
    render(<KpiSummary kpiData={dummyKpiData} />);

    expect(screen.getByText(/Total Net Profit/i)).toBeInTheDocument();
    expect(screen.getByText('12345')).toBeInTheDocument();

    expect(screen.getByText(/Profit Factor/i)).toBeInTheDocument();
    expect(screen.getByText('2.1')).toBeInTheDocument();

    expect(screen.getByText(/Max Drawdown/i)).toBeInTheDocument();
    expect(screen.getByText('-3000')).toBeInTheDocument();

    expect(screen.getByText(/Win Rate/i)).toBeInTheDocument();
    expect(screen.getByText('0.75')).toBeInTheDocument();
  });

  it('renders loading message if no data is provided', () => {
    render(<KpiSummary kpiData={null} />);
    expect(screen.getByText(/Loading KPIs.../i)).toBeInTheDocument();
  });

  it('renders loading message if data is undefined', () => {
    render(<KpiSummary kpiData={undefined} />);
    expect(screen.getByText(/Loading KPIs.../i)).toBeInTheDocument();
  });
});
