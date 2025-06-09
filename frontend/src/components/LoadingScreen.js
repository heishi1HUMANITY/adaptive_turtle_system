import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './LoadingScreen.css'; // We'll create this CSS file later for styling

const LoadingScreen = () => {
  const { jobId } = useParams();
  const navigate = useNavigate();

  const [status, setStatus] = useState('loading'); // e.g., loading, running, completed, failed
  const [error, setError] = useState(null);
  // const [progress, setProgress] = useState(0); // For future use

  useEffect(() => {
    if (!jobId) {
      setError('Job ID is missing.');
      setStatus('failed');
      return;
    }

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/backtest/status/${jobId}`);
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`Failed to fetch job status: ${response.status} ${errorText || 'Unknown server error'}`);
        }
        const data = await response.json();

        setStatus(data.job_status); // Assuming backend returns { job_id: "...", job_status: "...", message: "..." }
        // setProgress(data.progress || 0); // If backend provides progress

        if (data.job_status === 'completed') {
          clearInterval(pollInterval);
          navigate('/results', { state: { jobId: jobId } });
        } else if (data.job_status === 'failed') {
          clearInterval(pollInterval);
          setError(data.message || 'The backtest process failed.');
        }
        // If status is 'running' or 'pending', polling continues
      } catch (err) {
        console.error('Polling error:', err);
        setError("ステータスの確認中に通信エラーが発生しました。ネットワーク状況を確認するか、しばらくしてから再度試してください。");
        setStatus('failed'); // Set status to failed on fetch error to stop polling
        clearInterval(pollInterval);
      }
    }, 3000); // Poll every 3 seconds

    // Cleanup function to clear the interval when the component unmounts or jobId changes
    return () => {
      clearInterval(pollInterval);
    };
  }, [jobId, navigate]); // Dependencies for useEffect

  return (
    <div className="loading-screen">
      <h1>バックテストを実行しています...</h1>
      <p>(計算には数分かかる場合があります)</p>

      <div className="progress-placeholder">
        [Loading Animation/Progress Bar]
      </div>

      {status === 'running' && <p>Status: Running...</p>}
      {status === 'pending' && <p>Status: Pending...</p>}
      {status === 'loading' && <p>Status: Initializing...</p>}


      {error && (
        <div className="error-message">
          <p>エラーが発生しました：</p>
          <p>{error}</p>
        </div>
      )}

      <div className="actions">
        <button disabled>処理をキャンセル</button>
      </div>
    </div>
  );
};

export default LoadingScreen;
