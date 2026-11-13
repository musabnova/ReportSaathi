import React, { useState, useEffect } from 'react';
import { Loader2, Sparkles, FileText, CheckCircle2 } from 'lucide-react';

/**
 * Modern SaaS Loading Indicator with Step Progression
 * Provides reassuring, real-time contextual feedback while OCR and Gemini process the report.
 */
export default function LoadingSpinner({ isFile = true }) {
  const fileSteps = [
    'Scanning document and digitizing text...',
    'Performing optical character recognition (OCR)...',
    'Analyzing laboratory measurements against reference ranges...',
    'Generating clear, plain-language patient explanations...',
  ];

  const textSteps = [
    'Parsing laboratory values and units...',
    'Analyzing measurements against standard reference ranges...',
    'Generating clear, plain-language patient explanations...',
    'Formulating helpful questions for your doctor...',
  ];

  const steps = isFile ? fileSteps : textSteps;
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentStepIndex((prev) => (prev + 1 < steps.length ? prev + 1 : prev));
    }, 2800);

    return () => clearInterval(timer);
  }, [steps.length]);

  return (
    <div className="loading-card" role="status" aria-live="polite">
      <div className="loading-spinner-circle">
        <Loader2 size={36} className="spinner-icon-animated" strokeWidth={2.4} />
      </div>

      <h3 className="loading-title">Analyzing Your Medical Report</h3>
      <p className="loading-active-step">{steps[currentStepIndex]}</p>

      {/* Progress Dots / Steps */}
      <div className="loading-steps-dots">
        {steps.map((_, index) => (
          <span
            key={index}
            className={`step-dot ${index === currentStepIndex ? 'dot-active' : ''} ${index < currentStepIndex ? 'dot-complete' : ''}`}
            aria-hidden="true"
          />
        ))}
      </div>

      <span className="loading-privacy-reminder">
        <Sparkles size={13} className="privacy-sparkle" />
        Processed securely in memory. No report data is permanently stored.
      </span>
    </div>
  );
}
