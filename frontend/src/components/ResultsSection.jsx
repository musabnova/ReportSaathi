import React, { useState } from 'react';
import StatusBadge from './StatusBadge';
import { 
  Sparkles, 
  HelpCircle, 
  RotateCcw, 
  ChevronDown, 
  ChevronUp, 
  FileSearch, 
  AlertCircle, 
  Activity, 
  CheckCircle2, 
  AlertTriangle 
} from 'lucide-react';

/**
 * Modern Healthcare SaaS Results Dashboard
 * Displays:
 * 1. KPI Metrics Bar (Total Tests, Normal Tests, Out-of-Range Attention Tests)
 * 2. Plain-language Overall Explanation Summary
 * 3. Individual Test Result Cards with Name, Value, Reference Range, Status Badge, and Meaning
 * 4. Questions to Discuss with Your Doctor
 * 5. Non-Lab Document Notice (when no lab tests are found)
 * 6. Collapsible Raw OCR Extracted Text Accordion
 * 7. Action to analyze another report
 */
export default function ResultsSection({ result, onReset }) {
  const [showOcrText, setShowOcrText] = useState(false);

  if (!result) return null;

  const { summary, tests = [], questions_for_doctor = [], extracted_text } = result;

  // Detect non-laboratory document results
  // Gemini returns empty tests and empty questions when input is not a medical lab report.
  const isNonLabDocument = tests.length === 0 && questions_for_doctor.length === 0;

  // Calculate metrics
  const totalTests = tests.length;
  const abnormalTests = tests.filter((t) => {
    const s = (t.status || '').toLowerCase().trim();
    return s === 'high' || s === 'low';
  }).length;
  const normalTests = tests.filter((t) => (t.status || '').toLowerCase().trim() === 'normal').length;

  return (
    <div className="results-container" id="results">
      {/* ── Non-Lab Document Notice ── */}
      {isNonLabDocument ? (
        <div className="no-lab-results-card" role="status">
          <div className="notice-icon-circle">
            <AlertCircle size={28} className="notice-icon-svg" />
          </div>

          <div className="notice-text-content">
            <h3 className="notice-card-title">No Medical Laboratory Results Detected</h3>
            <p className="notice-card-body">
              {summary || 'The provided document or text does not appear to contain recognized clinical laboratory test values.'}
            </p>
            <div className="notice-guidance-box">
              <span className="guidance-label">Helpful Tip:</span>
              <p className="guidance-text">
                Please upload a standard pathology or laboratory report (e.g., Complete Blood Count, Lipid Profile, Liver/Kidney Function Test, Thyroid Panel, Blood Glucose, or Urine Routine) that includes numerical values and laboratory reference ranges.
              </p>
            </div>
          </div>
        </div>
      ) : (
        <>
          {/* ── KPI Metric Statistics Cards ── */}
          <div className="results-metrics-grid">
            {/* Metric 1: Total Tests */}
            <div className="metric-kpi-card">
              <div className="metric-kpi-header">
                <span className="metric-kpi-title">Tests Detected</span>
                <div className="metric-kpi-icon-box kpi-blue">
                  <Activity size={18} />
                </div>
              </div>
              <div className="metric-kpi-value">{totalTests}</div>
              <span className="metric-kpi-subtitle">Extracted from report</span>
            </div>

            {/* Metric 2: Within Reference Range */}
            <div className="metric-kpi-card">
              <div className="metric-kpi-header">
                <span className="metric-kpi-title">Within Range</span>
                <div className="metric-kpi-icon-box kpi-green">
                  <CheckCircle2 size={18} />
                </div>
              </div>
              <div className="metric-kpi-value">{normalTests}</div>
              <span className="metric-kpi-subtitle">Normal values</span>
            </div>

            {/* Metric 3: Out of Range / Attention */}
            <div className="metric-kpi-card">
              <div className="metric-kpi-header">
                <span className="metric-kpi-title">Needs Attention</span>
                <div className={`metric-kpi-icon-box ${abnormalTests > 0 ? 'kpi-amber' : 'kpi-green'}`}>
                  <AlertTriangle size={18} />
                </div>
              </div>
              <div className="metric-kpi-value">{abnormalTests}</div>
              <span className="metric-kpi-subtitle">
                {abnormalTests > 0 ? 'High or Low values flagged' : 'No out-of-range values'}
              </span>
            </div>
          </div>

          {/* ── 1. Executive Summary Card ── */}
          <div className="result-card summary-presentation-card">
            <div className="result-card-header">
              <div className="header-icon-badge">
                <Sparkles size={18} className="header-badge-icon" />
              </div>
              <div>
                <h3 className="result-card-title">Overall Report Explanation</h3>
                <span className="result-card-subtitle">Plain-language executive analysis</span>
              </div>
            </div>
            <p className="summary-paragraph">
              {summary || 'No summary available for this report.'}
            </p>
          </div>

          {/* ── 2. Individual Test Cards Grid ── */}
          {tests.length > 0 && (
            <div className="result-card">
              <div className="result-card-header">
                <div className="header-icon-badge">
                  <Activity size={18} className="header-badge-icon" />
                </div>
                <div>
                  <h3 className="result-card-title">Detailed Test Breakdown ({tests.length})</h3>
                  <span className="result-card-subtitle">Every reported laboratory measurement explained</span>
                </div>
              </div>

              <div className="tests-cards-grid">
                {tests.map((test, index) => (
                  <div key={index} className="test-card-modern">
                    <div className="test-card-header-row">
                      <h4 className="test-name-heading">{test.name || 'Unnamed Test'}</h4>
                      <StatusBadge status={test.status} />
                    </div>

                    <div className="test-stats-row">
                      <div className="test-stat-item">
                        <span className="stat-label">Reported Value:</span>
                        <span className="stat-val stat-val-bold">{test.value || 'N/A'}</span>
                      </div>
                      <div className="test-stat-item">
                        <span className="stat-label">Reference Range:</span>
                        <span className="stat-val">{test.normal_range || 'Not specified'}</span>
                      </div>
                    </div>

                    <div className="test-meaning-box">
                      <span className="meaning-label">Plain Meaning:</span>
                      <p className="meaning-text">{test.meaning || 'Explanation not provided.'}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── 3. Questions for Your Doctor ── */}
          {questions_for_doctor.length > 0 && (
            <div className="result-card questions-presentation-card">
              <div className="result-card-header">
                <div className="header-icon-badge question-badge-icon-box">
                  <HelpCircle size={18} className="question-badge-icon" />
                </div>
                <div>
                  <h3 className="result-card-title">Questions to Discuss with Your Doctor</h3>
                  <span className="result-card-subtitle">Recommended talking points for your next medical consultation</span>
                </div>
              </div>

              <div className="questions-card-list">
                {questions_for_doctor.map((q, idx) => (
                  <div key={idx} className="question-card-item">
                    <span className="question-counter" aria-hidden="true">{idx + 1}</span>
                    <p className="question-text-content">{q}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* ── 4. Collapsible OCR Extracted Text Accordion ── */}
      {extracted_text && (
        <div className="ocr-accordion-wrapper">
          <button
            type="button"
            className="ocr-accordion-toggle-btn"
            onClick={() => setShowOcrText(!showOcrText)}
            aria-expanded={showOcrText}
          >
            <div className="ocr-toggle-left">
              <FileSearch size={17} className="ocr-search-icon" />
              <span>View Raw Extracted Document Text</span>
            </div>
            <div className="ocr-toggle-right">
              <span className="ocr-toggle-state-text">{showOcrText ? 'Hide Text' : 'Show Text'}</span>
              {showOcrText ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </div>
          </button>

          {showOcrText && (
            <div className="ocr-accordion-body">
              <pre className="ocr-raw-display">{extracted_text}</pre>
            </div>
          )}
        </div>
      )}

      {/* ── 5. Action: Explain Another Report ── */}
      <div className="results-action-row">
        <button type="button" className="analyze-another-btn" onClick={onReset}>
          <RotateCcw size={16} strokeWidth={2.2} />
          <span>Analyze Another Report</span>
        </button>
      </div>
    </div>
  );
}
