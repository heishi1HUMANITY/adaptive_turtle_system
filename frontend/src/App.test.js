import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom'; // Ensure this is imported for matchers
import App from './App';

// Remove any global fetch mocks if they were here, e.g.:
// jest.mock('node-fetch');
// global.fetch = jest.fn();
// beforeEach(() => {
//   fetch.mockClear();
// });


test('renders the BacktestSettingsForm heading', () => {
  render(<App />);
  // Check for the main heading from BacktestSettingsForm
  const headingElement = screen.getByText(/自動売買システム バックテスト/i);
  expect(headingElement).toBeInTheDocument();
});

// If there were other general tests for App that are still relevant, they can remain.
// Otherwise, this single test might be sufficient for the current App.js.
