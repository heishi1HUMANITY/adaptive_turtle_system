import React from 'react';
import { render, screen, fireEvent, within } from '@testing-library/react'; // Import within
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
    const paginationTestData = [];
    for (let i = 1; i <= 9; i++) {
      paginationTestData.push({ id: i, date: `2023-01-${String(i).padStart(2, '0')}T00:00:00Z`, type: 'Buy', symbol: `SYM${i}`, quantity: 1, price: 100 + i, profit: null });
    }
    paginationTestData.push({ id: 10, date: '2023-01-10T00:00:00Z', type: 'Buy', symbol: 'SYM10_PAGE_ONE_END', quantity: 1, price: 110, profit: null }); // 10th item
    paginationTestData.push({ id: 11, date: '2023-01-11T00:00:00Z', type: 'Sell', symbol: 'ONLY_ON_PAGE_TWO', quantity: 1, price: 111, profit: 10 }); // 11th item
    paginationTestData.push({ id: 12, date: '2023-01-12T00:00:00Z', type: 'Buy', symbol: 'SYM12_PAGE_TWO', quantity: 1, price: 112, profit: null }); // 12th item

    render(<TradeHistoryTable tradeHistoryData={paginationTestData} />);

    // Check page 1
    expect(screen.getByText('SYM1')).toBeInTheDocument(); // First item of page 1
    expect(screen.getByText('SYM10_PAGE_ONE_END')).toBeInTheDocument(); // Last item of page 1
    expect(screen.queryByText('ONLY_ON_PAGE_TWO')).not.toBeInTheDocument();
    expect(screen.getByText(/Page 1 of 2/i)).toBeInTheDocument();


    const nextPageButton = screen.getByRole('button', { name: /next/i });
    act(() => {
      fireEvent.click(nextPageButton);
    });

    // Check page 2
    expect(screen.getByText('ONLY_ON_PAGE_TWO')).toBeInTheDocument();
    expect(screen.getByText('SYM12_PAGE_TWO')).toBeInTheDocument();
    expect(screen.queryByText('SYM1')).not.toBeInTheDocument(); // Item from page 1 should be gone
    expect(screen.queryByText('SYM10_PAGE_ONE_END')).not.toBeInTheDocument(); // Item from page 1 should be gone
    expect(screen.getByText(/Page 2 of 2/i)).toBeInTheDocument();

    const prevPageButton = screen.getByRole('button', { name: /previous/i });
    act(() => {
      fireEvent.click(prevPageButton);
    });

    // Back on page 1
    expect(screen.getByText('SYM1')).toBeInTheDocument();
    expect(screen.queryByText('ONLY_ON_PAGE_TWO')).not.toBeInTheDocument();
    expect(screen.getByText(/Page 1 of 2/i)).toBeInTheDocument();
  });

  it('calls sort function when header is clicked', () => {
    render(<TradeHistoryTable tradeHistoryData={dummyTradeHistoryData} />);

    let rows = screen.getAllByRole('row');
    // rows[0] is the header row. rows[1] is the first data row.
    // The 'Symbol' column is the 4th column (index 3).
    // Initial data order: AAPL, AAPL, MSFT, GOOG, GOOG, TSLA, TSLA, NVDA, NVDA, AMZN (on page 1)

    // Check initial order (AAPL should be in the first data row, 4th cell)
    expect(within(rows[1]).getAllByRole('cell')[3]).toHaveTextContent('AAPL');

    const symbolHeader = screen.getByText('Symbol'); // Get the 'Symbol' header cell

    // Click to sort by Symbol Ascending
    act(() => {
      fireEvent.click(symbolHeader);
    });

    rows = screen.getAllByRole('row'); // Re-query rows after sort
    // After ascending sort, AMZN should be first on page 1 from dummyTradeHistoryData
    // (AAPL, AMZN, GOOG, MSFT, NVDA, TSLA)
    expect(within(rows[1]).getAllByRole('cell')[3]).toHaveTextContent('AAPL'); // Alphabetically, AAPL is first.

    // Click to sort by Symbol Descending
    act(() => {
      fireEvent.click(symbolHeader);
    });

    rows = screen.getAllByRole('row'); // Re-query rows after sort
    // After descending sort, TSLA should be first on page 1 from dummyTradeHistoryData
    expect(within(rows[1]).getAllByRole('cell')[3]).toHaveTextContent('TSLA');
  });

  it('has an export to CSV button', () => {
    render(<TradeHistoryTable tradeHistoryData={dummyTradeHistoryData} />);
    expect(screen.getByText('Export to CSV')).toBeInTheDocument();
  });

  describe('CSV Export Functionality', () => {
    let mockLink;
    let createElementSpy, appendChildSpy, removeChildSpy;
    let createObjectURLSpy, blobSpy, clickSpy;

    beforeEach(() => {
      // Mock document.createElement to return a mock link object
      mockLink = {
        href: '',
        setAttribute: jest.fn(),
        click: jest.fn(), // Mock the click function on the link
        style: { visibility: '' },
      };
      createElementSpy = jest.spyOn(document, 'createElement').mockReturnValue(mockLink);
      clickSpy = jest.spyOn(mockLink, 'click'); // Specifically spy on the mockLink's click method

      appendChildSpy = jest.spyOn(document.body, 'appendChild').mockImplementation(() => {});
      removeChildSpy = jest.spyOn(document.body, 'removeChild').mockImplementation(() => {});

      // Ensure global.URL and global.URL.createObjectURL are defined before spying
      if (typeof global.URL === 'undefined') {
        global.URL = { createObjectURL: jest.fn() };
      } else if (typeof global.URL.createObjectURL === 'undefined') {
        global.URL.createObjectURL = jest.fn();
      }
      // Now it's safe to spy
      createObjectURLSpy = jest.spyOn(global.URL, 'createObjectURL').mockReturnValue('mocked_url_per_test');

      blobSpy = jest.spyOn(global, 'Blob').mockImplementation((content, options) => ({
        content: content,
        type: options ? options.type : '',
      }));
    });

    afterEach(() => {
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
      expect(clickSpy).toHaveBeenCalled(); // Check if the spied click on the link was called
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
