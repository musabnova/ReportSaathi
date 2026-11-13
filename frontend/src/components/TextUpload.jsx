import React from 'react';
import { ClipboardPaste, Trash2 } from 'lucide-react';

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
      <div className="textarea-header-bar">
        <span className="textarea-label">Report Text Content</span>
        <button
          type="button"
          className="sample-btn"
          onClick={handleLoadSample}
        >
          <ClipboardPaste size={14} />
          <span>Paste Sample CBC Report</span>
        </button>
      </div>

      <textarea
        className="report-textarea"
        placeholder="Paste your medical laboratory report text here (e.g., Complete Blood Count, Lipid Profile, Thyroid Panel, Blood Glucose, or Urine Routine)..."
        value={text}
        onChange={(e) => onTextChange(e.target.value)}
        rows={9}
      />

      <div className="textarea-footer">
        <div className="footer-left-info">
          {text.trim().length > 0 && (
            <button
              type="button"
              onClick={onClearText}
              className="clear-text-btn"
            >
              <Trash2 size={13} />
              <span>Clear text</span>
            </button>
          )}
        </div>

        <span className="char-count">{text.length} characters</span>
      </div>
    </div>
  );
}
