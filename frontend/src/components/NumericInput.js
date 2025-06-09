import React from 'react';

const NumericInput = ({ label, value, onChange, tooltip, disabled, error, onValidate }) => {
  const handleChange = (e) => {
    const newValue = e.target.value;
    if (onChange) {
      onChange(e); // Propagate the original event or just the value
    }
    if (onValidate) {
      onValidate(newValue);
    }
  };

  return (
    <div>
      <label>
        {label}
        {tooltip && <span title={tooltip}> (?)</span>}
      </label>
      <input
        type="number"
        value={value}
        onChange={handleChange}
        disabled={disabled}
      />
      {error && <p style={{ color: 'red' }}>{error}</p>}
    </div>
  );
};

export default NumericInput;
