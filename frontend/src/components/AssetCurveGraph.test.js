import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import AssetCurveGraph from './AssetCurveGraph';

// Mock react-chartjs-2
jest.mock('react-chartjs-2', () => ({
  Line: () => <canvas data-testid="mock-line-chart" />
}));

// Mock chartjs-plugin-zoom
jest.mock('chartjs-plugin-zoom', () => ({}));

// Mock chartjs-adapter-date-fns (or any other adapter you use)
jest.mock('chartjs-adapter-date-fns', () => {});

// Mock ChartJS.register (if not covered by react-chartjs-2 mock)
jest.mock('chart.js', () => ({
  ...jest.requireActual('chart.js'), // Import and retain default behavior
  Chart: {
    register: jest.fn(),
    // If you need to mock other Chart methods, do it here
  },
  // Mock specific controllers, elements, scales, plugins if needed and not covered
  // For example, if TimeScale is directly used and not just via options:
  TimeScale: jest.fn(),
  // Add other scales, elements, etc., as necessary based on actual component usage
  CategoryScale: jest.fn(),
  LinearScale: jest.fn(),
  PointElement: jest.fn(),
  LineElement: jest.fn(),
  Title: jest.fn(),
  Tooltip: jest.fn(),
  Legend: jest.fn(),
}));


describe('AssetCurveGraph', () => {
  const dummyAssetData = [{ date: '2023-01-01', equity: 10000 }];
  const emptyAssetData = [];

  it('renders a canvas for the chart when data is provided', () => {
    render(<AssetCurveGraph assetCurveData={dummyAssetData} />);
    expect(screen.getByTestId('mock-line-chart')).toBeInTheDocument();
  });

  it('shows loading text if no data is provided (empty array)', () => {
    render(<AssetCurveGraph assetCurveData={emptyAssetData} />);
    expect(screen.getByText(/Loading asset curve data.../i)).toBeInTheDocument();
  });

  it('shows loading text if data is null', () => {
    render(<AssetCurveGraph assetCurveData={null} />);
    expect(screen.getByText(/Loading asset curve data.../i)).toBeInTheDocument();
  });

  it('shows loading text if data is undefined', () => {
    render(<AssetCurveGraph assetCurveData={undefined} />);
    expect(screen.getByText(/Loading asset curve data.../i)).toBeInTheDocument();
  });
});
