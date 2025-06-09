import React, { useState, useEffect } from 'react';
import { useLocation, Link } from 'react-router-dom';
import KpiSummary from './KpiSummary';
import AssetCurveGraph from './AssetCurveGraph';
import TradeHistoryTable from './TradeHistoryTable';
import './BacktestResultPage.css'; // Import CSS for this page

const BacktestResultPage = () => {
  const location = useLocation();
  const [kpiData, setKpiData] = useState(null);
  const [assetCurveData, setAssetCurveData] = useState([]);
  const [tradeHistoryData, setTradeHistoryData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const jobId = location.state?.jobId;

    if (!jobId) {
      setError("結果の読み込みに失敗しました。有効なジョブIDが指定されていません。設定ページから再度バックテストを実行してください。");
      setLoading(false);
      return;
    }

    const fetchResults = async () => {
      setLoading(true);
      setError(null); // Clear previous errors
      try {
        const response = await fetch(`http://localhost:8000/api/backtest/results/${jobId}`);
        if (!response.ok) {
          const errorText = await response.text();
          let apiErrorMessage = '';
          try {
            const errorJson = JSON.parse(errorText);
            // FastAPI often returns errors in a 'detail' field, which can be a string or an array of objects
            if (errorJson.detail) {
              if (typeof errorJson.detail === 'string') {
                apiErrorMessage = errorJson.detail;
              } else if (Array.isArray(errorJson.detail) && errorJson.detail.length > 0 && errorJson.detail[0].msg) {
                // Example for validation errors: take the first message
                apiErrorMessage = errorJson.detail[0].msg;
              } else {
                apiErrorMessage = JSON.stringify(errorJson.detail); // Fallback for complex detail objects
              }
            } else if (errorJson.message) { // General fallback if 'message' field exists
              apiErrorMessage = errorJson.message;
            }
          } catch (e) {
            // errorText was not JSON or did not contain expected fields. Use raw errorText if it's not too long.
            apiErrorMessage = errorText.length < 100 ? errorText : '';
          }
          const displayError = apiErrorMessage
            ? `サーバーからのエラー: ${apiErrorMessage} (ステータス: ${response.status})`
            : `結果の取得に失敗しました (ステータス: ${response.status})。サーバーで問題が発生したか、指定されたジョブIDの結果が見つからない可能性があります。`;
          throw new Error(displayError);
        }
        const data = await response.json();

        // Assuming 'data.results' holds the KPIs
        setKpiData(data.results || {});

        // Transform equity_curve: timestamp -> date
        const transformedAssetCurve = (data.equity_curve || []).map(point => ({
          date: point.timestamp, // Assuming timestamp is already in a suitable date string format for the graph
          equity: point.equity,
        }));
        setAssetCurveData(transformedAssetCurve);

        // Transform trade_log: backend fields -> frontend fields
        const transformedTradeHistory = (data.trade_log || []).map(trade => ({
          id: trade.order_id,
          date: trade.timestamp, // Assuming timestamp is a suitable date string
          type: trade.action, // 'buy' or 'sell'
          symbol: trade.symbol,
          quantity: trade.quantity,
          price: trade.price,
          profit: trade.realized_pnl,
          commission: trade.commission,
          slippage: trade.slippage,
          // Include other fields if your TradeHistoryTable can display them
        }));
        setTradeHistoryData(transformedTradeHistory);
        setError(null); // Clear error on successful fetch
      } catch (err) {
        console.error("Error fetching backtest results:", err);
        // Check if the error message is one we've constructed, otherwise use the generic network error.
        if (err.message.startsWith("サーバーからのエラー:") || err.message.startsWith("結果の取得に失敗しました")) {
          setError(err.message);
        } else {
          setError("結果の読み込み中に通信エラーが発生しました。ネットワーク状況を確認するか、しばらくしてから再度お試しください。");
        }
        // Clear data on error
        setKpiData(null);
        setAssetCurveData([]);
        setTradeHistoryData([]);
      } finally {
        setLoading(false);
      }
    };

    fetchResults();
  }, [location.state?.jobId]); // Re-run effect if jobId changes

  if (loading) {
    return <div className="backtest-result-page"><p>Loading results...</p></div>;
  }

  if (error) {
    return (
      <div className="backtest-result-page">
        <p className="error-message">Error: {error}</p>
        <Link to="/" className="back-to-settings-link">Back to Settings</Link>
      </div>
    );
  }

  if (!kpiData) {
    // This case handles if jobId was present but data somehow wasn't loaded (e.g. API returns empty)
     return (
      <div className="backtest-result-page">
        <p>No results available for the specified Job ID.</p>
        <Link to="/" className="back-to-settings-link">Back to Settings</Link>
      </div>
    );
  }

  return (
    <div className="backtest-result-page">
      <div className="results-header">
        <h2>Backtest Results</h2>
        <Link to="/" className="back-to-settings-link">Back to Settings</Link>
      </div>
      {kpiData && <KpiSummary kpiData={kpiData} />}
      {assetCurveData.length > 0 && <AssetCurveGraph assetCurveData={assetCurveData} />}
      {tradeHistoryData.length > 0 && <TradeHistoryTable tradeHistoryData={tradeHistoryData} />}
      {assetCurveData.length === 0 && tradeHistoryData.length === 0 && !kpiData && <p>No data to display.</p>}
    </div>
  );
};

export default BacktestResultPage;
