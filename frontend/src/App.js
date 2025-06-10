import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import './App.css';
import BacktestSettingsForm from './components/BacktestSettingsForm';
import BacktestResultPage from './components/BacktestResultPage'; // Import the new results page
import LoadingScreen from './components/LoadingScreen'; // Import the LoadingScreen component
import DataManagementPage from './components/DataManagementPage'; // Import DataManagementPage

function App() {
  return (
    <Router>
      <div className="App">
        <nav className="App-nav">
          <ul>
            <li>
              <Link to="/">Settings</Link>
            </li>
            <li>
              <Link to="/results">Results</Link>
            </li>
            <li>
              <Link to="/data-management">Data Management</Link> {/* Link to Data Management */}
            </li>
          </ul>
        </nav>
        <header className="App-header">
          <h1>Backtesting Platform</h1>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<BacktestSettingsForm />} />
            <Route path="/results" element={<BacktestResultPage />} />
            <Route path="/loading/:jobId" element={<LoadingScreen />} /> {/* Added route for LoadingScreen */}
            <Route path="/data-management" element={<DataManagementPage />} /> {/* Route for Data Management */}
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
