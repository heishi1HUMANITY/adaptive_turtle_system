import React from 'react';

const FileUpload = ({ onFileSelect, disabled }) => {
  const handleFileChange = (event) => {
    if (event.target.files && event.target.files[0]) {
      if (onFileSelect) {
        onFileSelect(event.target.files[0]);
      }
    }
  };

  return (
    <div>
      <label>データファイル:</label>
      <input type="file" onChange={handleFileChange} disabled={disabled} />
    </div>
  );
};

export default FileUpload;
