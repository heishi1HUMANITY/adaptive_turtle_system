import React from 'react';

const ResetButton = ({ onClick, disabled }) => {
  return (
    <button type="button" onClick={onClick} disabled={disabled}>
      パラメータをデフォルト値に戻す
    </button>
  );
};

export default ResetButton;
