import React from 'react';

/**
 * Animated medical loading spinner shown while OCR and Gemini analysis are in progress.
 */
export default function LoadingSpinner({ isFile }) {
  return (
    <div className="card loading-box" role="status" aria-live="polite">
      <div className="spinner" aria-hidden="true" />
      <div>
        <p className="loading-text">
          {isFile ? 'Reading and analyzing your report...' : 'Explaining lab tests in plain language...'}
        </p>
        <p className="loading-subtext">
          {isFile ? 'Extracting text with OCR and translating medical jargon' : 'Translating complex medical terminology'}
        </p>
      </div>
    </div>
  );
}

