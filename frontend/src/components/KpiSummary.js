import React from 'react';
import './KpiSummary.css';

const KpiSummary = ({ kpiData }) => {
  if (!kpiData) {
    return <div>Loading KPIs...</div>;
  }

  return (
    <div className="kpi-summary-container">
      <div className="kpi-card">
        <h4>Total Net Profit</h4>
        <p>{kpiData.totalNetProfit}</p>
      </div>
      <div className="kpi-card">
        <h4>Profit Factor</h4>
        <p>{kpiData.profitFactor}</p>
      </div>
      <div className="kpi-card">
        <h4>Max Drawdown</h4>
        <p>{kpiData.maxDrawdown}</p>
      </div>
      <div className="kpi-card">
        <h4>Win Rate</h4>
        <p>{kpiData.winRate}</p>
      </div>
    </div>
  );
};

export default KpiSummary;
