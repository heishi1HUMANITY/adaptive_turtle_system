import React from 'react';

const DateRangePicker = ({ startDate, endDate, onStartDateChange, onEndDateChange, disabled }) => {
  return (
    <div>
      <label>バックテスト期間:</label>
      <input
        type="date"
        value={startDate}
        onChange={(e) => onStartDateChange && onStartDateChange(e.target.value)}
        disabled={disabled}
      />
      <span> から </span>
      <input
        type="date"
        value={endDate}
        onChange={(e) => onEndDateChange && onEndDateChange(e.target.value)}
        disabled={disabled}
      />
      <span> まで</span>
    </div>
  );
};

export default DateRangePicker;
