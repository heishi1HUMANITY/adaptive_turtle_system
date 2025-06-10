import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom'; // Import Link
import './DataManagementPage.css';

function DataManagementPage() {
    const [apiKey, setApiKey] = useState('');

    // Load API key from localStorage on component mount
    useEffect(() => {
        const storedApiKey = localStorage.getItem('alphaVantageApiKey');
        if (storedApiKey) {
            setApiKey(storedApiKey);
        }
    }, []);

    // Handle API key save
    const handleSaveApiKey = () => {
        localStorage.setItem('alphaVantageApiKey', apiKey);
        alert('APIキーを保存しました。');
    };

    // Data Collection Form States
    const [currencyPair, setCurrencyPair] = useState('USDJPY');
    const [startYear, setStartYear] = useState(new Date().getFullYear());
    const [startMonth, setStartMonth] = useState(1);
    const [endYear, setEndYear] = useState(new Date().getFullYear());
    const [endMonth, setEndMonth] = useState(new Date().getMonth() + 1);

    // Log Display States and Handlers
    const [logMessages, setLogMessages] = useState([]);
    const ws = useRef(null); // Using useRef for WebSocket instance

    useEffect(() => {
        // Mock WebSocket connection
        // In a real scenario, the URL would be something like 'ws://localhost:8000/ws/logs'
        // For now, we simulate messages
        ws.current = {
            send: (message) => console.log("Mock WS Send:", message),
            close: () => console.log("Mock WS Closed"),
        };
        const mockLogMessagesArray = [ // Renamed to avoid conflict
            "データ収集プロセスを開始しました...",
            `通貨ペア: ${currencyPair}, 期間: ${startYear}/${startMonth} - ${endYear}/${endMonth}`,
            "2023年1月のデータを取得中...",
            "-> レートリミット対策のため15秒待機します...",
            "2023年2月のデータを取得中...",
            "データ収集が完了しました。",
        ];
        let messageIndex = 0;
        const intervalId = setInterval(() => {
            if (messageIndex < mockLogMessagesArray.length) {
                const newMessage = `> ${new Date().toLocaleTimeString()}: ${mockLogMessagesArray[messageIndex]}`;
                setLogMessages(prevMessages => [...prevMessages, newMessage]);
                messageIndex++;
            }
        }, 2000);
        return () => {
            clearInterval(intervalId);
            if (ws.current && ws.current.close) {
                 ws.current.close();
            }
        };
    }, [currencyPair, startYear, startMonth, endYear, endMonth]); // Dependencies for mock logs

    const handleClearLogs = () => {
        setLogMessages([]);
    };

    // Data File List
    const [fileList, setFileList] = useState([]);

    const fetchFileList = async () => {
        setLogMessages(prevMessages => [...prevMessages, `> ${new Date().toLocaleTimeString()}: ファイルリストを更新中...`]);
        try {
            // Mocking the API call
            // const response = await fetch('/api/data/files');
            // if (!response.ok) {
            //     throw new Error(`HTTP error! status: ${response.status}`);
            // }
            // const data = await response.json();

            // Mock data:
            const mockData = [
                { name: "USDJPY_M1_20230101_20231231.csv", size: "25.8 MB", createdAt: "2025-06-09 10:30" },
                { name: "EURUSD_M1_20240101_20240608.csv", size: "12.1 MB", createdAt: "2025-06-08 15:00" },
                { name: "GBPUSD_M1_20230501_20231031.csv", size: "15.2 MB", createdAt: "2025-05-15 12:00" },
            ];

            // Simulate API delay
            await new Promise(resolve => setTimeout(resolve, 1000));

            setFileList(mockData);
            setLogMessages(prevMessages => [...prevMessages, `> ${new Date().toLocaleTimeString()}: ファイルリストを更新しました。`]);
        } catch (error) {
            console.error("Failed to fetch file list:", error);
            setLogMessages(prevMessages => [...prevMessages, `> ${new Date().toLocaleTimeString()}: ファイルリストの更新に失敗しました: ${error.message}`]);
            setFileList([]); // Clear list on error or set to a default error state
        }
    };

    // Fetch file list on component mount
    useEffect(() => {
        fetchFileList();
    }, []); // Empty dependency array means this runs once on mount


    const handleStartDataCollection = () => {
        if (!currencyPair) {
            alert('通貨ペアを選択してください。');
            return;
        }
        if (startYear > endYear || (startYear === endYear && startMonth > endMonth)) {
            alert('開始年月は終了年月より前に設定してください。');
            return;
        }
        const collectionParams = {
            apiKey: apiKey, // Not sent to backend per spec, but kept for now
            currencyPair,
            timeframe: 'M1',
            startDate: `${startYear}-${String(startMonth).padStart(2, '0')}-01`,
            endDate: `${endYear}-${String(endMonth).padStart(2, '0')}-01`,
        };
        console.log('Starting data collection with params:', collectionParams);
        setLogMessages(prevMessages => [...prevMessages, `> ${new Date().toLocaleTimeString()}: データ収集リクエスト: ${JSON.stringify(collectionParams)}`]);

        // Placeholder for actual API call to /api/data/collect
        // After successful collection, the backend should ideally trigger an update to the file list,
        // or the frontend could call fetchFileList() again.
        alert('データ収集リクエストを送信しました (ログを確認してください)。');
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
                        onChange={(e) => setApiKey(e.target.value)}
                        placeholder="Enter your API key"
                    />
                    <button onClick={handleSaveApiKey}>保存</button>
                </div>
                <small>APIキーはブラウザに安全に保存され、外部には送信されません。</small>
            </section>

            <section className="new-data-collection">
                <h2>2. 新規データ収集</h2>
                {/* ... (data collection form JSX remains the same) ... */}
                <div className="form-group">
                    <label htmlFor="currencyPair">通貨ペア:</label>
                    <select id="currencyPair" value={currencyPair} onChange={(e) => setCurrencyPair(e.target.value)}>
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
                    <input type="number" value={startYear} onChange={(e) => setStartYear(parseInt(e.target.value))} placeholder="YYYY" />年
                    <input type="number" value={startMonth} onChange={(e) => setStartMonth(parseInt(e.target.value))} placeholder="MM" min="1" max="12" />月 から
                    <input type="number" value={endYear} onChange={(e) => setEndYear(parseInt(e.target.value))} placeholder="YYYY" />年
                    <input type="number" value={endMonth} onChange={(e) => setEndMonth(parseInt(e.target.value))} placeholder="MM" min="1" max="12"/>月 まで
                </div>
                <button onClick={handleStartDataCollection}>データ収集を開始</button>
            </section>

            <section className="collection-status-log">
                <h2>3. 収集ステータス＆ログ</h2>
                <div className="log-display">
                    {logMessages.map((msg, index) => (
                        <p key={index}>{msg}</p>
                    ))}
                </div>
                <button onClick={handleClearLogs}>実行ログをクリア</button>
            </section>

            <section className="server-data-files">
                <h2>4. サーバー上のデータファイル一覧</h2>
                <button onClick={fetchFileList}>更新</button> {/* Refresh button */}
                <table>
                    <thead>
                        <tr>
                            <th>ファイル名</th>
                            <th>ファイルサイズ</th>
                            <th>作成日時</th>
                        </tr>
                    </thead>
                    <tbody>
                        {fileList.length > 0 ? (
                            fileList.map((file, index) => (
                                <tr key={index}>
                                    <td>{file.name}</td>
                                    <td>{file.size}</td>
                                    <td>{file.createdAt}</td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan="3">利用可能なデータファイルはありません。</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </section>
        </div>
    );
}

export default DataManagementPage;
