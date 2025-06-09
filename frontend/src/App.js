import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import './App.css';
import BacktestSettingsForm from './components/BacktestSettingsForm';
import BacktestResultPage from './components/BacktestResultPage'; // Import the new results page
import LoadingScreen from './components/LoadingScreen'; // Import the LoadingScreen component

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
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
