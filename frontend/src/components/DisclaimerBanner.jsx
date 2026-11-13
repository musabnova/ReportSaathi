import React from 'react';
import { AlertTriangle } from 'lucide-react';

/**
 * Persistent Medical Disclaimer Banner.
 * Must remain clearly visible to ensure ethical health-literacy usage.
 */
export default function DisclaimerBanner() {
  return (
    <div className="disclaimer-banner" role="alert" aria-live="polite">
      <div className="disclaimer-icon-wrapper" aria-hidden="true">
        <AlertTriangle size={18} className="disclaimer-icon" strokeWidth={2.4} />
      </div>
      <p className="disclaimer-text">
        <strong>Educational Notice:</strong> ReportSaathi provides informational explanations only. It does <strong>not</strong> provide medical diagnoses, clinical assessments, or medicine recommendations. Always consult a qualified doctor regarding your lab results and medical conditions.
      </p>
    </div>
  );
}
