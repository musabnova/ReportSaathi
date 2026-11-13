import React from 'react';

/**
 * User-friendly error alert with categorized messages.
 */
export default function ErrorAlert({ message, onDismiss }) {
  if (!message) return null;

  return (
    <div className="error-alert" role="alert">
      <div className="error-icon" aria-hidden="true">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      </div>
      <div style={{ flex: 1 }}>
        <h4 className="error-title">Notice</h4>
        <p className="error-message">{message}</p>
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          style={{
            background: 'none',
            border: 'none',
            color: '#991b1b',
            cursor: 'pointer',
            fontSize: '1.1rem',
            padding: '2px 6px',
          }}
          aria-label="Dismiss error"
        >
          &times;
        </button>
      )}
    </div>
  );
}

