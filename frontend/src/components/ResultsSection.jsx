import React, { useState } from 'react';
import StatusBadge from './StatusBadge';

/**
 * Results presentation component displaying:
 * 1. Plain-language overall summary (or a non-lab-document notice)
 * 2. Individual test cards with values, reference ranges, status badges, and meanings
 * 3. Suggested questions for the doctor
 * 4. Raw extracted OCR text (collapsible)
 *
 * When Gemini determines the input is NOT a medical laboratory report,
 * it returns tests: [] and questions_for_doctor: []. In that case we
 * show a clear info notice instead of empty sections.
 */
export default function ResultsSection({ result, onReset }) {
  const [showOcrText, setShowOcrText] = useState(false);

  if (!result) return null;

  const { summary, tests = [], questions_for_doctor = [], extracted_text } = result;

  // Detect non-lab-document results:
  // Gemini returns empty tests + empty questions when the input is not a medical report.
  const isNonLabDocument = tests.length === 0 && questions_for_doctor.length === 0;

  return (
    <div className="results-container">

      {/* ── Non-Lab Document Notice ── */}
      {isNonLabDocument ? (
        <div className="no-lab-results-notice" role="status">
          <div className="notice-icon-row">
            {/* Info-circle icon */}
            <svg
              className="notice-icon"
              width="28"
              height="28"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="16" x2="12" y2="12" />
              <line x1="12" y1="8" x2="12.01" y2="8" />
            </svg>
            <h2 className="notice-title">No Laboratory Results Found</h2>
          </div>

          {/* Show Gemini's summary, which explains what was detected */}
          <p className="notice-body">
            {summary || 'The uploaded document does not appear to contain medical laboratory test results.'}
          </p>

          <p className="notice-hint">
            Try uploading a blood test, urine test, or other laboratory report
            that includes test names, values, and reference ranges.
          </p>
        </div>
      ) : (
        <>
          {/* ── 1. Summary Card (shown only when lab results exist) ── */}
          <div className="summary-card">
            <div className="card-header-with-icon">
              <div className="card-header-icon" aria-hidden="true">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                  <polyline points="10 9 9 9 8 9" />
                </svg>
              </div>
              <h2 className="section-title">Report Summary</h2>
            </div>
            <p className="summary-text">{summary || 'No summary available.'}</p>
          </div>

          {/* ── 2. Detected Lab Tests ── */}
          {tests.length > 0 && (
            <div className="card">
              <div className="card-header-with-icon">
                <div className="card-header-icon" aria-hidden="true">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                  </svg>
                </div>
                <h2 className="section-title">Test Results Explained ({tests.length})</h2>
              </div>

              <div className="tests-grid">
                {tests.map((test, index) => (
                  <div key={index} className="test-item-card">
                    <div className="test-card-top">
                      <h3 className="test-name">{test.name || 'Unnamed Test'}</h3>
                      <StatusBadge status={test.status} />
                    </div>

                    <div className="test-metrics-row">
                      <div className="metric-item">
                        <span className="metric-label">Reported Value:</span>
                        <span className="metric-val">{test.value || 'N/A'}</span>
                      </div>
                      <div className="metric-item">
                        <span className="metric-label">Reference Range:</span>
                        <span className="metric-val">{test.normal_range || 'Not specified'}</span>
                      </div>
                    </div>

                    <p className="test-meaning">{test.meaning}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── 3. Questions to Ask Your Doctor ── */}
          {questions_for_doctor.length > 0 && (
            <div className="questions-card">
              <div className="card-header-with-icon">
                <div className="card-header-icon" aria-hidden="true">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10" />
                    <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                    <line x1="12" y1="17" x2="12.01" y2="17" />
                  </svg>
                </div>
                <h2 className="section-title">Questions to Ask Your Doctor</h2>
              </div>

              <ul className="questions-list">
                {questions_for_doctor.map((q, idx) => (
                  <li key={idx} className="question-item">
                    <span className="question-bullet" aria-hidden="true">&#x25C9;</span>
                    <span>{q}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}

      {/* ── 4. Collapsible OCR Extracted Text (always shown if available) ── */}
      {extracted_text && (
        <div className="ocr-accordion">
          <button
            type="button"
            className="ocr-accordion-header"
            onClick={() => setShowOcrText(!showOcrText)}
            aria-expanded={showOcrText}
          >
            <span>View Raw Extracted Document Text</span>
            <span>{showOcrText ? '▲ Hide' : '▼ View'}</span>
          </button>
          {showOcrText && (
            <pre className="ocr-raw-text">{extracted_text}</pre>
          )}
        </div>
      )}

      {/* ── 5. Start New Explanation Button ── */}
      <button type="button" className="reset-btn" onClick={onReset}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="1 4 1 10 7 10" />
          <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
        </svg>
        Explain Another Report
      </button>
    </div>
  );
}
