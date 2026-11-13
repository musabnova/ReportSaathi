import React, { useRef, useState } from 'react';
import { UploadCloud, FileText, X, AlertCircle, CheckCircle } from 'lucide-react';

/**
 * Modern Healthcare SaaS File Upload Component
 * Features large dropzone, explicit "Browse Files" button, drag-and-drop feedback,
 * validation for JPG, PNG, PDF up to 5 MB, and rich preview card.
 */
export default function FileUpload({ file, previewUrl, onFileSelected, onFileCleared }) {
  const [isDragActive, setIsDragActive] = useState(false);
  const [validationError, setValidationError] = useState(null);
  const fileInputRef = useRef(null);

  const MAX_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB
  const ALLOWED_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf'];

  const validateAndSelect = (selectedFile) => {
    if (!selectedFile) return;
    setValidationError(null);

    // Validate size
    if (selectedFile.size > MAX_SIZE_BYTES) {
      setValidationError('File size exceeds 5 MB. Please upload a smaller document.');
      return;
    }

    // Validate type / extension
    const isAllowed = ALLOWED_TYPES.includes(selectedFile.type) || 
      /\.(jpe?g|png|pdf)$/i.test(selectedFile.name);

    if (!isAllowed) {
      setValidationError('Unsupported file format. Please upload a JPG, PNG, or PDF file.');
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
    <div className="upload-wrapper">
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

          <div className="dropzone-icon-circle">
            <UploadCloud size={32} className="dropzone-cloud-icon" strokeWidth={1.8} />
          </div>

          <h3 className="dropzone-title">Drag and drop your medical report here</h3>
          <p className="dropzone-subtitle">or choose a document from your device to begin analysis</p>

          <button
            type="button"
            className="dropzone-browse-btn"
            onClick={(e) => {
              e.stopPropagation();
              fileInputRef.current?.click();
            }}
          >
            Browse Files
          </button>

          <div className="dropzone-meta-tags">
            <span className="meta-tag">Supported: PDF, JPG, PNG</span>
            <span className="meta-dot">·</span>
            <span className="meta-tag">Max: 5 MB</span>
            <span className="meta-dot">·</span>
            <span className="meta-tag">In-Memory OCR</span>
          </div>
        </div>
      ) : (
        <div className="file-preview-card">
          <div className="file-preview-left">
            {previewUrl && !isPdf ? (
              <img src={previewUrl} alt="Report preview thumbnail" className="file-thumbnail" />
            ) : (
              <div className="file-icon-box" aria-hidden="true">
                <FileText size={28} className="file-icon-doc" />
                <span className="file-type-badge">{isPdf ? 'PDF' : 'IMG'}</span>
              </div>
            )}
            <div className="file-details">
              <div className="file-name-row">
                <p className="file-name" title={file.name}>{file.name}</p>
                <CheckCircle size={15} className="file-verified-icon" />
              </div>
              <p className="file-size-info">
                <span>{formatFileSize(file.size)}</span>
                <span className="meta-dot">·</span>
                <span>Ready for analysis</span>
              </p>
            </div>
          </div>

          <button
            type="button"
            className="remove-file-btn"
            onClick={onFileCleared}
            title="Remove document and select another"
            aria-label="Remove document"
          >
            <X size={18} strokeWidth={2.4} />
          </button>
        </div>
      )}

      {/* Inline Validation Error Message */}
      {validationError && (
        <div className="upload-validation-error">
          <AlertCircle size={16} />
          <span>{validationError}</span>
        </div>
      )}
    </div>
  );
}
