import { render, screen } from '@testing-library/react';
import App from './App';

// Mock the fetch function
global.fetch = jest.fn();

beforeEach(() => {
  // Reset the mock before each test
  global.fetch.mockImplementation(() =>
    Promise.resolve({
      ok: true, // Simulate a successful response
      json: () => Promise.resolve({ status: 'ok' }),
    })
  );
  fetch.mockClear(); // Clear call history
});

test('renders App component and shows initial API status text', () => {
  render(<App />);
  // Check for the static text "API Status:"
  // This appears before the fetch call completes.
  const initialStatusText = screen.getByText(/API Status:/i);
  expect(initialStatusText).toBeInTheDocument();
});

test('fetches API status and displays it', async () => {
  render(<App />);

  // Check that fetch was called correctly
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(fetch).toHaveBeenCalledWith('http://localhost:8000/api/health');

  // Wait for the component to update with the fetched status "ok"
  // findByText returns a Promise, so it waits for the element to appear
  const statusMessage = await screen.findByText(/API Status: ok/i);
  expect(statusMessage).toBeInTheDocument();
});

test('handles API fetch error', async () => {
  // Override the mock for this specific test to simulate an error
  global.fetch.mockImplementationOnce(() =>
    Promise.reject(new Error('API is down'))
  );

  // Suppress console.error for this test as we expect an error
  const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

  render(<App />);

  // Check that fetch was called
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(fetch).toHaveBeenCalledWith('http://localhost:8000/api/health');

  // The text "API Status:" should still be there, but not "ok"
  const initialStatusText = screen.getByText(/API Status:/i);
  expect(initialStatusText).toBeInTheDocument();

  // Ensure "API Status: ok" does NOT appear
  // queryByText is used because it returns null if not found, instead of throwing.
  const statusOkMessage = screen.queryByText(/API Status: ok/i);
  expect(statusOkMessage).not.toBeInTheDocument();

  // Check that our error was logged (optional, but good practice)
  // await waitFor(() => expect(consoleErrorSpy).toHaveBeenCalled()); // This might be too fast

  consoleErrorSpy.mockRestore(); // Restore original console.error
});
