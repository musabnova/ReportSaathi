import React from 'react';
import { AlertCircle, X } from 'lucide-react';

/**
 * Modern SaaS Error Alert Component
 * Displays user-friendly error messages with dismiss action and helpful troubleshooting tips.
 */
export default function ErrorAlert({ message, onDismiss }) {
  if (!message) return null;

  return (
    <div className="error-alert-card" role="alert">
      <div className="error-icon-box" aria-hidden="true">
        <AlertCircle size={20} className="error-icon" strokeWidth={2.2} />
      </div>

      <div className="error-content">
        <h4 className="error-title">Analysis Unsuccessful</h4>
        <p className="error-body">{message}</p>
        <span className="error-tip">
          Tip: Ensure your file is under 5 MB, well-lit, and contains visible text. You can also paste the report text directly using the &quot;Paste Report Text&quot; tab.
        </span>
      </div>

      {onDismiss && (
        <button
          type="button"
          className="error-dismiss-btn"
          onClick={onDismiss}
          aria-label="Dismiss error notification"
        >
          <X size={16} strokeWidth={2.4} />
        </button>
      )}
    </div>
  );
}
