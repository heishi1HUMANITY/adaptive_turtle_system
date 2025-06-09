import { render, screen, waitFor } from '@testing-library/react';
import App from './App';

// Mock the fetch function
global.fetch = jest.fn(() =>
  Promise.resolve({
    json: () => Promise.resolve({ status: 'ok' }),
  })
);

beforeEach(() => {
  fetch.mockClear();
});

test('renders App component without crashing', () => {
  render(<App />);
  // Check if a known element from App.js is present
  const linkElement = screen.getByText(/learn react/i);
  expect(linkElement).toBeInTheDocument();
});

test('displays API Status text', async () => {
  render(<App />);
  // Wait for the "API Status: ok" text to appear
  // It might take a moment due to the async fetch call
  const statusText = await screen.findByText(/API Status:/i);
  expect(statusText).toBeInTheDocument();
});

test('fetches and displays API status message', async () => {
  render(<App />);
  // Check that fetch was called
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(fetch).toHaveBeenCalledWith('http://localhost:8000/api/health');

  // Wait for the component to update with the fetched status
  const statusMessage = await screen.findByText(/API Status: ok/i);
  expect(statusMessage).toBeInTheDocument();
});
