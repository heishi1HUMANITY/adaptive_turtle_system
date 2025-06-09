import React, { useState, useMemo } from 'react';
import './TradeHistoryTable.css';

const TradeHistoryTable = ({ tradeHistoryData }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'ascending' });
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10; // Or make this configurable

  const tableHeaders = useMemo(() => {
    if (!tradeHistoryData || tradeHistoryData.length === 0) return [];
    // Assuming all objects have the same keys, use the first item to get headers
    return Object.keys(tradeHistoryData[0]);
  }, [tradeHistoryData]);

  const filteredData = useMemo(() => {
    if (!tradeHistoryData) return [];
    let data = [...tradeHistoryData];
    if (searchTerm) {
      data = data.filter(item =>
        Object.values(item).some(val =>
          String(val).toLowerCase().includes(searchTerm.toLowerCase())
        )
      );
    }
    return data;
  }, [tradeHistoryData, searchTerm]);

  const sortedData = useMemo(() => {
    let data = [...filteredData];
    if (sortConfig.key) {
      data.sort((a, b) => {
        if (a[sortConfig.key] < b[sortConfig.key]) {
          return sortConfig.direction === 'ascending' ? -1 : 1;
        }
        if (a[sortConfig.key] > b[sortConfig.key]) {
          return sortConfig.direction === 'ascending' ? 1 : -1;
        }
        return 0;
      });
    }
    return data;
  }, [filteredData, sortConfig]);

  const paginatedData = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return sortedData.slice(startIndex, startIndex + itemsPerPage);
  }, [sortedData, currentPage, itemsPerPage]);

  const requestSort = (key) => {
    let direction = 'ascending';
    if (sortConfig.key === key && sortConfig.direction === 'ascending') {
      direction = 'descending';
    }
    setSortConfig({ key, direction });
    setCurrentPage(1); // Reset to first page on sort
  };

  const exportToCSV = () => {
    if (sortedData.length === 0) return;
    const headers = tableHeaders;
    const csvContent = [
      headers.join(','),
      ...sortedData.map(row => headers.map(header => JSON.stringify(row[header])).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    if (link.download !== undefined) {
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', 'trade_history.csv');
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  if (!tradeHistoryData || tradeHistoryData.length === 0) {
    return <div>Loading trade history or no data to display...</div>;
  }

  const totalPages = Math.ceil(sortedData.length / itemsPerPage);

  return (
    <div className="trade-history-table-container">
      <div className="table-controls">
        <input
          type="text"
          placeholder="Search..."
          value={searchTerm}
          onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
          className="search-input"
        />
        <button onClick={exportToCSV} className="export-button">Export to CSV</button>
      </div>
      <table className="trade-table">
        <thead>
          <tr>
            {tableHeaders.map(header => (
              <th key={header} onClick={() => requestSort(header)} className="sortable-header">
                {header.charAt(0).toUpperCase() + header.slice(1)}
                {sortConfig.key === header ? (sortConfig.direction === 'ascending' ? ' 🔼' : ' 🔽') : ''}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {paginatedData.map((trade, index) => ( // Assuming trade has a unique 'id' or use index as key
            <tr key={trade.id || index}>
              {tableHeaders.map(header => (
                <td key={header}>{trade[header]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="pagination-controls">
        <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1}>
          Previous
        </button>
        <span>Page {currentPage} of {totalPages > 0 ? totalPages : 1}</span>
        <button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages || totalPages === 0}>
          Next
        </button>
      </div>
    </div>
  );
};

export default TradeHistoryTable;
