import React, { useRef, useState } from 'react';

/**
 * File upload component supporting drag-and-drop, file type validation (JPG, PNG, PDF),
 * size limit checks (< 5 MB), and rich visual previews.
 */
export default function FileUpload({ file, previewUrl, onFileSelected, onFileCleared }) {
  const [isDragActive, setIsDragActive] = useState(false);
  const fileInputRef = useRef(null);

  const MAX_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB
  const ALLOWED_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf'];

  const validateAndSelect = (selectedFile) => {
    if (!selectedFile) return;

    // Check file size
    if (selectedFile.size > MAX_SIZE_BYTES) {
      alert('File size exceeds the 5 MB limit. Please upload a smaller file.');
      return;
    }

    // Check extension / MIME type
    const isAllowed = ALLOWED_TYPES.includes(selectedFile.type) || 
      /\.(jpe?g|png|pdf)$/i.test(selectedFile.name);

    if (!isAllowed) {
      alert('Unsupported file format. Please upload a JPG, PNG, or PDF file.');
      return;
    }

    onFileSelected(selectedFile);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragActive(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragActive(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSelect(e.dataTransfer.files[0]);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const isPdf = file?.type === 'application/pdf' || file?.name?.toLowerCase().endsWith('.pdf');

  return (
    <div>
      {!file ? (
        <div
          className={`dropzone ${isDragActive ? 'drag-active' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              fileInputRef.current?.click();
            }
          }}
        >
          <input
            type="file"
            ref={fileInputRef}
            className="hidden-input"
            accept=".jpg,.jpeg,.png,.pdf"
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                validateAndSelect(e.target.files[0]);
              }
            }}
          />

          <svg
            className="dropzone-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="12" y1="18" x2="12" y2="12" />
            <line x1="9" y1="15" x2="12" y2="12" />
            <line x1="15" y1="15" x2="12" y2="12" />
          </svg>

          <h3 className="dropzone-title">Upload lab report image or PDF</h3>
          <p className="dropzone-subtitle">Drag and drop here, or browse files from your device</p>
          <span className="dropzone-badge">JPG, PNG, PDF up to 5 MB</span>
        </div>
      ) : (
        <div className="file-preview-card">
          <div className="file-preview-left">
            {previewUrl && !isPdf ? (
              <img src={previewUrl} alt="Report preview" className="file-thumbnail" />
            ) : (
              <div className="file-icon-box" aria-hidden="true">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <text x="7" y="18" fontSize="6" fontWeight="bold" fill="currentColor">PDF</text>
                </svg>
              </div>
            )}
            <div className="file-info">
              <p className="file-name" title={file.name}>{file.name}</p>
              <p className="file-size">{formatFileSize(file.size)}</p>
            </div>
          </div>

          <button
            type="button"
            className="remove-btn"
            onClick={onFileCleared}
            title="Remove document"
            aria-label="Remove document"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}

