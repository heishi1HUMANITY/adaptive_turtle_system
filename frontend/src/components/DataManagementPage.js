import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom'; // Import Link
import './DataManagementPage.css';

function DataManagementPage() {
    const [apiKey, setApiKey] = useState('');
    const [apiKeyError, setApiKeyError] = useState(''); // Error state for API key

    // Load API key from localStorage on component mount
    useEffect(() => {
        const storedApiKey = localStorage.getItem('alphaVantageApiKey');
        if (storedApiKey) {
            setApiKey(storedApiKey);
        }
    }, []);

    const handleApiKeyChange = (e) => {
        setApiKey(e.target.value);
        if (apiKeyError) {
            setApiKeyError(''); // Clear API key error when user types
        }
    };

    // Handle API key save
    const handleSaveApiKey = () => {
        if (!apiKey.trim()) {
            setApiKeyError('APIキーを入力してください。');
            return;
        }
        localStorage.setItem('alphaVantageApiKey', apiKey);
        setApiKeyError(''); // Clear any previous error
        alert('APIキーを保存しました。');
    };

    // Data Collection Form States
    const [isCollecting, setIsCollecting] = useState(false);
    const [collectionError, setCollectionError] = useState(''); // Error state for general collection errors
    const [currencyPair, setCurrencyPair] = useState('USDJPY');
    const [startYear, setStartYear] = useState(new Date().getFullYear());
    const [startMonth, setStartMonth] = useState(1);
    const [endYear, setEndYear] = useState(new Date().getFullYear());
    const [endMonth, setEndMonth] = useState(new Date().getMonth() + 1);

    // Log Display States and Handlers
    const [logMessages, setLogMessages] = useState([]);
    const [logStreamError, setLogStreamError] = useState(''); // Error state for WebSocket
    const ws = useRef(null); // Using useRef for WebSocket instance

    // Clear logs and close WebSocket connection on component unmount
    useEffect(() => {
        return () => {
            if (ws.current) {
                ws.current.close();
            }
        };
    }, []);

    const handleClearLogs = () => {
        setLogMessages([]);
    };

    // Data File List
    const [outputFileList, setOutputFileList] = useState([]);
    const [fileListError, setFileListError] = useState(''); // Error state for file list fetching

    const fetchOutputFileList = async () => {
        setFileListError(''); // Clear previous error
        // Keep existing log message for starting update
        setLogMessages(prevMessages => [...prevMessages, `> ${new Date().toLocaleTimeString()}: ファイルリストを更新中...`]);
        try {
            const response = await fetch('/api/data/files');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            setOutputFileList(data);
            setLogMessages(prevMessages => [...prevMessages, `> ${new Date().toLocaleTimeString()}: ファイルリストを更新しました。`]);
        } catch (error) {
            console.error("Failed to fetch file list:", error);
            const errorMsg = `ファイルリストの取得に失敗しました。 (${error.message})`;
            setFileListError(errorMsg);
            setLogMessages(prevMessages => [...prevMessages, `> ${new Date().toLocaleTimeString()}: ${errorMsg}`]);
            setOutputFileList([]); // Clear list on error
        }
    };

    // Fetch file list on component mount
    useEffect(() => {
        fetchOutputFileList();
    }, []); // Empty dependency array means this runs once on mount


    const handleStartDataCollection = async () => {
        if (isCollecting) return;

        // Clear previous errors
        setApiKeyError('');
        setCollectionError('');
        setLogStreamError('');

        if (!currencyPair) {
            alert('通貨ペアを選択してください。');
            return;
        }
        if (startYear > endYear || (startYear === endYear && startMonth > endMonth)) {
            alert('開始年月は終了年月より前に設定してください。');
            return;
        }

        setIsCollecting(true);
        setLogMessages(prevMessages => [...prevMessages, `> ${new Date().toLocaleTimeString()}: データ収集プロセスを開始します...`]);

        const storedApiKey = localStorage.getItem('alphaVantageApiKey');
        if (!storedApiKey) {
            setApiKeyError('APIキーが設定されていません。設定画面でAPIキーを保存してください。');
            setIsCollecting(false);
            return;
        }

        const collectionParams = {
            api_key: storedApiKey,
            currency_pair: currencyPair,
            timeframe: 'M1', // Assuming M1 is fixed as per UI
            start_date: `${startYear}-${String(startMonth).padStart(2, '0')}-01`,
            end_date: `${endYear}-${String(endMonth).padStart(2, '0')}-01`,
        };

        setLogMessages(prevMessages => [...prevMessages, `> ${new Date().toLocaleTimeString()}: データ収集リクエスト: ${JSON.stringify(Omit(collectionParams, ['api_key']))}`]);

        try {
            const response = await fetch('http://localhost:8000/api/data/collect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(collectionParams),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ message: 'Response parsing failed' }));
                // Check for specific API key error (e.g., 401 Unauthorized or a specific message from backend)
                if (response.status === 401 || (errorData.message && errorData.message.toLowerCase().includes('invalid api key'))) {
                    setApiKeyError('APIキーが不正です。正しいキーを入力してください。');
                } else {
                    setCollectionError(`データ収集の開始に失敗しました。サーバーエラー: ${response.status} ${errorData.message || response.statusText}`);
                }
                throw new Error(`HTTP error! status: ${response.status}, message: ${errorData.message || response.statusText}`);
            }

            const result = await response.json();
            const jobId = result.job_id;
            setLogMessages(prevMessages => [...prevMessages, `> ${new Date().toLocaleTimeString()}: データ収集ジョブ開始 (Job ID: ${jobId})`]);

            // Close existing WebSocket connection if any
            if (ws.current) {
                ws.current.close();
            }

            // Establish WebSocket connection
            const wsUrl = `ws://localhost:8000/api/data/stream_log/${jobId}`;
            ws.current = new WebSocket(wsUrl);

            ws.current.onopen = () => {
                setLogMessages(prevMessages => [...prevMessages, `> ${new Date().toLocaleTimeString()}: WebSocket接続確立 (${wsUrl})`]);
            };

            ws.current.onmessage = (event) => {
                setLogMessages(prevMessages => [...prevMessages, `> ${new Date().toLocaleTimeString()}: ${event.data}`]);
            };

            ws.current.onerror = (error) => {
                console.error("WebSocket error:", error);
                const errorMsg = `ログストリームへの接続中にエラーが発生しました。 (${error.message || '詳細不明'})`;
                setLogStreamError(errorMsg);
                setLogMessages(prevMessages => [...prevMessages, `> ${new Date().toLocaleTimeString()}: ${errorMsg}`]);
                setIsCollecting(false);
            };

            ws.current.onclose = (event) => {
                if (event.wasClean) {
                    setLogMessages(prevMessages => [...prevMessages, `> ${new Date().toLocaleTimeString()}: WebSocket接続が正常に終了しました。`]);
                } else {
                    const errorMsg = `ログストリーム接続が予期せず切断されました。(Code: ${event.code})`;
                    setLogStreamError(errorMsg);
                    setLogMessages(prevMessages => [...prevMessages, `> ${new Date().toLocaleTimeString()}: ${errorMsg}`]);
                }
                fetchOutputFileList();
                setIsCollecting(false);
            };

        } catch (error) {
            // This catch is for the fetch /api/data/collect part
            // Error messages (apiKeyError or collectionError) are already set if response was not ok.
            // If error is not from response.ok check (e.g. network error), set collectionError.
            if (!apiKeyError && !collectionError) { // Avoid overwriting specific error
                 setCollectionError(`データ収集リクエストに失敗しました: ${error.message}`);
            }
            setLogMessages(prevMessages => [...prevMessages, `> ${new Date().toLocaleTimeString()}: データ収集の開始に失敗しました: ${error.message}`]);
            setIsCollecting(false);
        }
    };

    // Helper to omit api_key for logging
    const Omit = (obj, keys) => {
        const newObj = { ...obj };
        keys.forEach(key => delete newObj[key]);
        return newObj;
    };

    return (
        <div className="data-management-page">
            <header>
                <h1>データ管理</h1>
                {/* Updated button to Link */}
                <Link to="/" className="button-like-link">バックテスト設定画面へ戻る</Link>
            </header>

            <section className="api-key-settings">
                <h2>1. APIキー設定 (Alpha Vantage)</h2>
                <div className="form-group">
                    <label htmlFor="apiKeyInput">APIキー:</label>
                    <input
                        type="password"
                        id="apiKeyInput"
                        value={apiKey}
                        onChange={handleApiKeyChange}
                        placeholder="Enter your API key"
                    />
                    <button onClick={handleSaveApiKey}>保存</button>
                </div>
                {apiKeyError && <p className="error-message api-key-error">{apiKeyError}</p>}
                <small>APIキーはブラウザに安全に保存され、外部には送信されません。</small>
            </section>

            <section className="new-data-collection">
                <h2>2. 新規データ収集</h2>
                {collectionError && <p className="error-message collection-error">{collectionError}</p>}
                <div className="form-group">
                    <label htmlFor="currencyPair">通貨ペア:</label>
                    <select id="currencyPair" value={currencyPair} onChange={(e) => setCurrencyPair(e.target.value)} disabled={isCollecting}>
                        <option value="USDJPY">USDJPY</option>
                        <option value="EURUSD">EURUSD</option>
                        <option value="GBPUSD">GBPUSD</option>
                    </select>
                    <label htmlFor="timeframe">時間足:</label>
                    <select id="timeframe" defaultValue="M1" disabled>
                        <option value="M1">1分足</option>
                    </select>
                </div>
                <div className="form-group">
                    <label>取得期間:</label>
                    <input type="number" value={startYear} onChange={(e) => setStartYear(parseInt(e.target.value))} placeholder="YYYY" disabled={isCollecting} />年
                    <input type="number" value={startMonth} onChange={(e) => setStartMonth(parseInt(e.target.value))} placeholder="MM" min="1" max="12" disabled={isCollecting} />月 から
                    <input type="number" value={endYear} onChange={(e) => setEndYear(parseInt(e.target.value))} placeholder="YYYY" disabled={isCollecting} />年
                    <input type="number" value={endMonth} onChange={(e) => setEndMonth(parseInt(e.target.value))} placeholder="MM" min="1" max="12" disabled={isCollecting} />月 まで
                </div>
                <button onClick={handleStartDataCollection} disabled={isCollecting}>
                    {isCollecting ? '収集中...' : 'データ収集を開始'}
                </button>
                {isCollecting && <p className="collecting-message">データ収集中です。完了までお待ちください...</p>}
            </section>

            <section className="collection-status-log">
                <h2>3. 収集ステータス＆ログ</h2>
                {logStreamError && <p className="error-message log-stream-error">{logStreamError}</p>}
                <div className="log-display">
                    {logMessages.map((msg, index) => (
                        <p key={index}>{msg}</p>
                    ))}
                </div>
                <button onClick={handleClearLogs}>実行ログをクリア</button>
            </section>

            <section className="server-data-files">
                <h2>4. サーバー上のデータファイル一覧</h2>
                {fileListError && <p className="error-message file-list-error">{fileListError}</p>}
                <button onClick={fetchOutputFileList} disabled={isCollecting}>更新</button> {/* Refresh button, disable if collecting */}
                <table>
                    <thead>
                        <tr>
                            <th>ファイル名</th>
                            <th>ファイルサイズ</th>
                            <th>作成日時</th>
                        </tr>
                    </thead>
                    <tbody>
                        {outputFileList.length > 0 ? (
                            outputFileList.map((file, index) => (
                                <tr key={index}>
                                    <td>{file.name}</td>
                                    <td>{file.size}</td>
                                    <td>{file.createdAt}</td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan="3">{fileListError ? 'エラーのため表示できません。' : '利用可能なデータファイルはありません。'}</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </section>
        </div>
    );
}

export default DataManagementPage;
