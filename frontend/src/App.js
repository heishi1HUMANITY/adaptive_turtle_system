import React from 'react';
import './App.css';
import BacktestSettingsForm from './components/BacktestSettingsForm'; // Import the form

function App() {
  return (
    <div className="App">
      <header className="App-header">
        {/* You can keep or remove the header as per overall app design */}
        {/* For now, let's just render the form */}
      </header>
      <main>
        <BacktestSettingsForm />
      </main>
    </div>
  );
}

export default App;
