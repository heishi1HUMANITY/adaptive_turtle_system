import React from 'react';

const ExecutionButton = ({ onClick, isExecuting }) => {
  return (
    <button type="button" onClick={onClick} disabled={isExecuting}>
      {isExecuting ? "実行中..." : "バックテストを実行する"}
    </button>
  );
};

export default ExecutionButton;
