import React from 'react';
import KpiSummary from './KpiSummary';
import AssetCurveGraph from './AssetCurveGraph';
import TradeHistoryTable from './TradeHistoryTable';
import { Link } from 'react-router-dom';
import './BacktestResultPage.css'; // Import CSS for this page

const dummyKpiData = {
  totalNetProfit: 15000,
  profitFactor: 1.8,
  maxDrawdown: -5000,
  winRate: 0.60,
};

const dummyAssetCurveData = [
  { date: '2023-01-01', equity: 100000 },
  { date: '2023-01-05', equity: 101000 },
  { date: '2023-01-10', equity: 100500 },
  { date: '2023-01-15', equity: 102000 },
  { date: '2023-01-20', equity: 103500 },
  { date: '2023-01-25', equity: 103000 },
  { date: '2023-01-30', equity: 104500 },
  { date: '2023-02-01', equity: 105000 },
  { date: '2023-02-05', equity: 105200 },
  { date: '2023-02-10', equity: 106000 },
];

const dummyTradeHistoryData = [
  { id: 1, date: '2023-01-01T10:00:00Z', type: 'Buy', symbol: 'AAPL', quantity: 10, price: 150.00, profit: null },
  { id: 2, date: '2023-01-03T14:30:00Z', type: 'Sell', symbol: 'AAPL', quantity: 10, price: 155.00, profit: 50.00 },
  { id: 3, date: '2023-01-04T09:15:00Z', type: 'Buy', symbol: 'MSFT', quantity: 5, price: 250.00, profit: null },
  { id: 4, date: '2023-01-05T11:00:00Z', type: 'Buy', symbol: 'GOOGL', quantity: 2, price: 2700.00, profit: null },
  { id: 5, date: '2023-01-06T15:45:00Z', type: 'Sell', symbol: 'MSFT', quantity: 5, price: 255.00, profit: 25.00 },
  { id: 6, date: '2023-01-07T10:30:00Z', type: 'Buy', symbol: 'TSLA', quantity: 3, price: 1100.00, profit: null },
  { id: 7, date: '2023-01-10T12:00:00Z', type: 'Sell', symbol: 'GOOGL', quantity: 2, price: 2750.00, profit: 100.00 },
  { id: 8, date: '2023-01-11T13:20:00Z', type: 'Buy', symbol: 'NVDA', quantity: 7, price: 280.00, profit: null },
  { id: 9, date: '2023-01-12T16:00:00Z', type: 'Sell', symbol: 'TSLA', quantity: 3, price: 1050.00, profit: -150.00 },
  { id: 10, date: '2023-01-13T09:45:00Z', type: 'Buy', symbol: 'AMZN', quantity: 1, price: 3200.00, profit: null },
  { id: 11, date: '2023-01-14T14:10:00Z', type: 'Sell', symbol: 'NVDA', quantity: 7, price: 290.00, profit: 70.00 },
  { id: 12, date: '2023-01-15T11:30:00Z', type: 'Buy', symbol: 'BTCUSD', quantity: 0.1, price: 40000.00, profit: null },
  { id: 13, date: '2023-01-17T10:05:00Z', type: 'Sell', symbol: 'AMZN', quantity: 1, price: 3250.00, profit: 50.00 },
  { id: 14, date: '2023-01-18T15:00:00Z', type: 'Buy', symbol: 'ETHUSD', quantity: 2, price: 3000.00, profit: null },
  { id: 15, date: '2023-01-19T12:45:00Z', type: 'Sell', symbol: 'BTCUSD', quantity: 0.1, price: 42000.00, profit: 200.00 },
  { id: 16, date: '2023-01-20T09:00:00Z', type: 'Buy', symbol: 'AAPL', quantity: 15, price: 160.00, profit: null },
  { id: 17, date: '2023-01-21T16:30:00Z', type: 'Sell', symbol: 'ETHUSD', quantity: 2, price: 2800.00, profit: -400.00 },
  { id: 18, date: '2023-01-24T10:10:00Z', type: 'Buy', symbol: 'MSFT', quantity: 10, price: 260.00, profit: null },
  { id: 19, date: '2023-01-25T11:50:00Z', type: 'Sell', symbol: 'AAPL', quantity: 15, price: 165.00, profit: 75.00 },
  { id: 20, date: '2023-01-26T13:00:00Z', type: 'Sell', symbol: 'MSFT', quantity: 10, price: 265.00, profit: 50.00 },
];


const BacktestResultPage = () => {
  return (
    <div className="backtest-result-page">
      <div className="results-header">
        <h2>Backtest Results</h2>
        <Link to="/" className="back-to-settings-link">Back to Settings</Link>
      </div>
      <KpiSummary kpiData={dummyKpiData} />
      <AssetCurveGraph assetCurveData={dummyAssetCurveData} />
      <TradeHistoryTable tradeHistoryData={dummyTradeHistoryData} />
    </div>
  );
};

export default BacktestResultPage;
