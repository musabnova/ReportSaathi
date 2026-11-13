import React from 'react';

/**
 * Text upload component for pasting medical report contents directly.
 * Includes a quick 'Sample Report' loader for testing.
 */
export default function TextUpload({ text, onTextChange, onClearText }) {
  const sampleReportText = `Complete Blood Count (CBC)
Patient: John Doe (Age: 38)
Date: 12-Nov-2026

Test Results:
- Hemoglobin: 9.1 g/dL (Reference Range: 13.0 - 17.0 g/dL)
- White Blood Cell (WBC): 12,500 /mcL (Reference Range: 4,000 - 11,000 /mcL)
- Platelet Count: 210,000 /mcL (Reference Range: 150,000 - 450,000 /mcL)
- Fasting Blood Sugar: 142 mg/dL (Reference Range: 70 - 99 mg/dL)`;

  const handleLoadSample = () => {
    onTextChange(sampleReportText);
  };

  return (
    <div className="textarea-container">
      <textarea
        className="report-textarea"
        placeholder="Paste your lab report text here (e.g. CBC, lipid profile, thyroid panel, blood sugar)..."
        value={text}
        onChange={(e) => onTextChange(e.target.value)}
        rows={8}
      />

      <div className="textarea-footer">
        <button type="button" className="sample-btn" onClick={handleLoadSample}>
          Paste Sample CBC Report
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {text.trim().length > 0 && (
            <button
              type="button"
              onClick={onClearText}
              style={{
                background: 'none',
                border: 'none',
                color: '#64748b',
                cursor: 'pointer',
                fontSize: '0.8rem',
                textDecoration: 'underline',
              }}
            >
              Clear text
            </button>
          )}
          <span className="char-count">{text.length} characters</span>
        </div>
      </div>
    </div>
  );
}

