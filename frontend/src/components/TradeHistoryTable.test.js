import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import TradeHistoryTable from './TradeHistoryTable';

// Mocking for CSV export
global.URL.createObjectURL = jest.fn(() => 'mocked_url');
global.Blob = jest.fn(function(content, options) {
  this.content = content;
  this.options = options;
  return this; // The constructor returns itself
});


describe('TradeHistoryTable', () => {
  const dummyTradeHistoryData = [
    { id: 1, date: '2023-01-01T10:00:00Z', type: 'Buy', symbol: 'AAPL', quantity: 10, price: 150.00, profit: null },
    { id: 2, date: '2023-01-03T14:30:00Z', type: 'Sell', symbol: 'AAPL', quantity: 10, price: 155.00, profit: 50.00 },
    { id: 3, date: '2023-01-04T09:15:00Z', type: 'Buy', symbol: 'MSFT', quantity: 5, price: 250.00, profit: null },
    // Add more for pagination testing - need at least 11 for two pages with itemsPerPage=10
    { id: 4, date: '2023-01-05T10:00:00Z', type: 'Buy', symbol: 'GOOG', quantity: 10, price: 1500.00, profit: null },
    { id: 5, date: '2023-01-06T10:00:00Z', type: 'Sell', symbol: 'GOOG', quantity: 10, price: 1550.00, profit: 500.00 },
    { id: 6, date: '2023-01-07T10:00:00Z', type: 'Buy', symbol: 'TSLA', quantity: 10, price: 700.00, profit: null },
    { id: 7, date: '2023-01-08T10:00:00Z', type: 'Sell', symbol: 'TSLA', quantity: 10, price: 750.00, profit: 500.00 },
    { id: 8, date: '2023-01-09T10:00:00Z', type: 'Buy', symbol: 'NVDA', quantity: 10, price: 200.00, profit: null },
    { id: 9, date: '2023-01-10T10:00:00Z', type: 'Sell', symbol: 'NVDA', quantity: 10, price: 250.00, profit: 500.00 },
    { id: 10, date: '2023-01-11T10:00:00Z', type: 'Buy', symbol: 'AMZN', quantity: 10, price: 3000.00, profit: null },
    { id: 11, date: '2023-01-12T10:00:00Z', type: 'Sell', symbol: 'AMZN', quantity: 10, price: 3050.00, profit: 500.00 },
  ];

  it('renders loading message if no data is provided', () => {
    render(<TradeHistoryTable tradeHistoryData={null} />);
    expect(screen.getByText(/Loading trade history or no data to display.../i)).toBeInTheDocument();
  });

  it('renders table with data', () => {
    render(<TradeHistoryTable tradeHistoryData={dummyTradeHistoryData} />);
    expect(screen.getByText('AAPL')).toBeInTheDocument(); // Check for a known symbol
    expect(screen.getByText('MSFT')).toBeInTheDocument();
    expect(screen.getAllByRole('row').length).toBeGreaterThan(1); // Header + data rows (max 10 per page)
  });

  it('filters data based on search term', () => {
    render(<TradeHistoryTable tradeHistoryData={dummyTradeHistoryData} />);
    const searchInput = screen.getByPlaceholderText('Search...');
    fireEvent.change(searchInput, { target: { value: 'MSFT' } });
    expect(screen.getByText('MSFT')).toBeInTheDocument();
    expect(screen.queryByText('AAPL')).not.toBeInTheDocument();
  });

  it('paginates data', () => {
    render(<TradeHistoryTable tradeHistoryData={dummyTradeHistoryData} />); // 11 items, 10 per page
    expect(screen.getByText('AAPL')).toBeInTheDocument(); // First page
    expect(screen.queryByText('AMZN')).not.toBeInTheDocument(); // AMZN is the 11th item, so on page 2

    const nextPageButton = screen.getByText('Next');
    fireEvent.click(nextPageButton);

    expect(screen.queryByText('AAPL')).not.toBeInTheDocument(); // First item no longer visible
    expect(screen.getByText('AMZN')).toBeInTheDocument(); // 11th item now visible
    expect(screen.getByText(/Page 2 of 2/i)).toBeInTheDocument();
  });

  it('calls sort function when header is clicked', () => {
    render(<TradeHistoryTable tradeHistoryData={dummyTradeHistoryData} />);
    // Check initial order (e.g., by ID or first symbol)
    let rows = screen.getAllByRole('row');
    // queryByText can be useful if the text might not be there
    expect(rows[1].querySelector('td:nth-child(4)')).toHaveTextContent('AAPL');


    const symbolHeader = screen.getByText('Symbol'); // Case sensitive as per component
    fireEvent.click(symbolHeader); // Sort by symbol ascending

    rows = screen.getAllByRole('row');
    // This depends on the actual sorting logic and data. Let's assume AAPL is still first or near first.
    // A more robust test would check the actual order of multiple elements if predictable.
    // For now, we confirm the header click doesn't crash and potentially re-renders.
    // A better assertion would be to check the order of 'AAPL', 'AMZN', 'GOOG', etc.

    // Example: Check if the first data row's symbol cell contains expected text after sort
    // This requires knowing your data and how it sorts.
    // For dummyTradeHistoryData, 'AAPL' is the first alphabetically.
    expect(rows[1].querySelector('td:nth-child(4)')).toHaveTextContent('AAPL');

    fireEvent.click(symbolHeader); // Sort by symbol descending
    rows = screen.getAllByRole('row');
    // Now, TSLA or NVDA or MSFT might be first depending on full dataset.
    // For dummyTradeHistoryData, 'TSLA' would be last alphabetically.
    expect(rows[1].querySelector('td:nth-child(4)')).toHaveTextContent('TSLA');
  });

  it('has an export to CSV button', () => {
    render(<TradeHistoryTable tradeHistoryData={dummyTradeHistoryData} />);
    expect(screen.getByText('Export to CSV')).toBeInTheDocument();
  });

  it('attempts to download a CSV when export button is clicked', () => {
    const mockLink = {
      href: '',
      download: '',
      style: { visibility: '' },
      setAttribute: jest.fn(),
      click: jest.fn(),
    };
    jest.spyOn(document, 'createElement').mockReturnValue(mockLink);
    jest.spyOn(document.body, 'appendChild').mockImplementation(() => {});
    jest.spyOn(document.body, 'removeChild').mockImplementation(() => {});


    render(<TradeHistoryTable tradeHistoryData={dummyTradeHistoryData} />);
    const exportButton = screen.getByText('Export to CSV');
    fireEvent.click(exportButton);

    expect(global.Blob).toHaveBeenCalled();
    expect(global.URL.createObjectURL).toHaveBeenCalled();
    expect(mockLink.setAttribute).toHaveBeenCalledWith('href', 'mocked_url');
    expect(mockLink.setAttribute).toHaveBeenCalledWith('download', 'trade_history.csv');
    expect(mockLink.click).toHaveBeenCalled();
    expect(document.body.appendChild).toHaveBeenCalledWith(mockLink);
    expect(document.body.removeChild).toHaveBeenCalledWith(mockLink);

    // Restore mocks
    jest.restoreAllMocks();
  });

  it('handles empty data for CSV export gracefully', () => {
    const mockLink = {
      href: '',
      download: '',
      style: { visibility: '' },
      setAttribute: jest.fn(),
      click: jest.fn(),
    };
    jest.spyOn(document, 'createElement').mockReturnValue(mockLink);
    jest.spyOn(document.body, 'appendChild').mockImplementation(() => {});
    jest.spyOn(document.body, 'removeChild').mockImplementation(() => {});
    const originalBlob = global.Blob;
    global.Blob = jest.fn();


    render(<TradeHistoryTable tradeHistoryData={[]} />);
    const exportButton = screen.getByText('Export to CSV');
    fireEvent.click(exportButton);

    expect(global.Blob).not.toHaveBeenCalled(); // Should not attempt to create Blob if no data
    expect(mockLink.click).not.toHaveBeenCalled();

    global.Blob = originalBlob; // Restore
    jest.restoreAllMocks();
  });

});
