import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import TradeHistoryTable from './TradeHistoryTable';

import { act } from '@testing-library/react'; // Using act from RTL

// It's generally better to set up and tear down mocks for each test or context (describe block)
// to avoid interference between tests.

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
    // Use getAllByText and check the length or specific elements
    expect(screen.getAllByText('AAPL').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('MSFT')[0]).toBeInTheDocument(); // Check for one MSFT
    expect(screen.getAllByRole('row').length).toBeGreaterThan(1); // Header + data rows (max 10 per page)
  });

  it('filters data based on search term', () => {
    render(<TradeHistoryTable tradeHistoryData={dummyTradeHistoryData} />);
    const searchInput = screen.getByPlaceholderText('Search...');
    fireEvent.change(searchInput, { target: { value: 'MSFT' } });
    expect(screen.getAllByText('MSFT')[0]).toBeInTheDocument();
    expect(screen.queryByText('AAPL')).not.toBeInTheDocument();
  });

  it('paginates data', () => {
    render(<TradeHistoryTable tradeHistoryData={dummyTradeHistoryData} />); // 11 items, 10 per page
    // Check that first page items are present
    expect(screen.getAllByText('AAPL')[0]).toBeInTheDocument();
    expect(screen.queryByText('AMZN')).not.toBeInTheDocument(); // AMZN is the 11th item, so on page 2

    const nextPageButton = screen.getByText('Next');
    fireEvent.click(nextPageButton);

    // After clicking next, AAPL should not be there (assuming it was only on page 1)
    // and AMZN should be there.
    expect(screen.queryByText('AAPL')).not.toBeInTheDocument();
    expect(screen.getAllByText('AMZN')[0]).toBeInTheDocument();
    expect(screen.getByText(/Page 2 of 2/i)).toBeInTheDocument();
  });

  it('calls sort function when header is clicked', () => {
    render(<TradeHistoryTable tradeHistoryData={dummyTradeHistoryData} />);
    // Check initial order (e.g., by ID or first symbol)
    let rows = screen.getAllByRole('row');
    // queryByText can be useful if the text might not be there
    // Ensure we are selecting a cell within the data rows, not header.
    // This checks the symbol in the first cell of the first data row.
    expect(screen.getAllByRole('row')[1].getAllByRole('cell')[3]).toHaveTextContent('AAPL');


    const symbolHeader = screen.getByText('Symbol'); // Case sensitive as per component
    fireEvent.click(symbolHeader); // Sort by symbol ascending

    // After sorting, re-fetch rows and check content.
    // This assertion assumes 'AAPL' is alphabetically first among the symbols.
    expect(screen.getAllByRole('row')[1].getAllByRole('cell')[3]).toHaveTextContent('AAPL');

    fireEvent.click(symbolHeader); // Sort by symbol descending
    // This assertion assumes 'TSLA' is alphabetically last among the symbols on the first page.
    // If pagination changes which items are on the first page post-sort, this might need adjustment.
    // For the given dataset and itemsPerPage=10, TSLA will be on the first page.
    expect(screen.getAllByRole('row')[1].getAllByRole('cell')[3]).toHaveTextContent('TSLA');
  });

  it('has an export to CSV button', () => {
    render(<TradeHistoryTable tradeHistoryData={dummyTradeHistoryData} />);
    expect(screen.getByText('Export to CSV')).toBeInTheDocument();
  });

  describe('CSV Export Functionality', () => {
    let mockLink;
    let createElementSpy;
    let appendChildSpy;
    let removeChildSpy;
    let createObjectURLSpy;
    let blobSpy;

    beforeEach(() => {
      // Setup mocks before each test in this describe block
      mockLink = {
        href: '',
        download: '',
        style: { visibility: '' }, // Ensure style property exists
        setAttribute: jest.fn(),
        click: jest.fn(),
      };
      createElementSpy = jest.spyOn(document, 'createElement').mockReturnValue(mockLink);
      appendChildSpy = jest.spyOn(document.body, 'appendChild').mockImplementation(() => {});
      removeChildSpy = jest.spyOn(document.body, 'removeChild').mockImplementation(() => {});
      createObjectURLSpy = jest.spyOn(URL, 'createObjectURL').mockReturnValue('mocked_url_per_test');
      // Mock Blob constructor
      blobSpy = jest.spyOn(global, 'Blob').mockImplementation((content, options) => ({
        content: content,
        options: options,
        // you can add more blob properties if your code uses them e.g. size, type
      }));
    });

    afterEach(() => {
      // Restore all mocks after each test
      jest.restoreAllMocks();
    });

    it('attempts to download a CSV when export button is clicked with data', () => {
      render(<TradeHistoryTable tradeHistoryData={dummyTradeHistoryData} />);
      const exportButton = screen.getByText('Export to CSV');

      act(() => {
        fireEvent.click(exportButton);
      });

      expect(blobSpy).toHaveBeenCalled();
      expect(createObjectURLSpy).toHaveBeenCalled();
      expect(createElementSpy).toHaveBeenCalledWith('a');
      expect(mockLink.setAttribute).toHaveBeenCalledWith('href', 'mocked_url_per_test');
      expect(mockLink.setAttribute).toHaveBeenCalledWith('download', 'trade_history.csv');
      expect(mockLink.click).toHaveBeenCalled();
      expect(appendChildSpy).toHaveBeenCalledWith(mockLink);
      expect(removeChildSpy).toHaveBeenCalledWith(mockLink);
    });

    it('handles empty data for CSV export gracefully (no Blob creation or download)', () => {
      render(<TradeHistoryTable tradeHistoryData={[]} />); // Empty data
      const exportButton = screen.getByText('Export to CSV');

      act(() => {
        fireEvent.click(exportButton);
      });

      expect(blobSpy).not.toHaveBeenCalled();
      expect(createObjectURLSpy).not.toHaveBeenCalled();
      expect(mockLink.click).not.toHaveBeenCalled();
    });
  });
});
