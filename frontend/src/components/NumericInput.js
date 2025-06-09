import React from 'react';

const NumericInput = ({ label, value, onChange, tooltip, disabled, error, onValidate, id }) => {
  const handleChange = (e) => {
    const newValue = e.target.value;
    if (onChange) {
      onChange(e);
    }
    if (onValidate) {
      onValidate(newValue);
    }
  };

  return (
    <div>
      <label htmlFor={id}>
        {label}
        {tooltip && <span title={tooltip}> (?)</span>}
      </label>
      <input
        type="number"
        id={id} // Corrected line: comment removed
        value={value}
        onChange={handleChange}
        disabled={disabled}
      />
      {error && <p style={{ color: 'red' }}>{error}</p>}
    </div>
  );
};

export default NumericInput;
