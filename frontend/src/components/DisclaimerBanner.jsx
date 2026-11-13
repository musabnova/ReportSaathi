import React from 'react';

/**
 * Persistent Medical Disclaimer Banner.
 * Must remain clearly visible to ensure ethical health-literacy usage.
 */
export default function DisclaimerBanner() {
  return (
    <div className="disclaimer-banner" role="alert" aria-live="polite">
      <div className="disclaimer-icon" aria-hidden="true">
        {/* Warning / Medical Cross SVG */}
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      </div>
      <p className="disclaimer-text">
        <strong>Educational Disclaimer:</strong> ReportSaathi is an educational health-literacy tool, not a medical device. It does <strong>not</strong> provide medical diagnoses, treatment plans, or medicine prescriptions. Always discuss your lab results and health concerns directly with a qualified doctor.
      </p>
    </div>
  );
}

