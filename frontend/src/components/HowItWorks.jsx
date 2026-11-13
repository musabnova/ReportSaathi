import React from 'react';
import { UploadCloud, Cpu, Stethoscope } from 'lucide-react';

/**
 * How It Works Section
 * Explains the 3-step pipeline clearly to build patient confidence.
 */
export default function HowItWorks() {
  const steps = [
    {
      step: '01',
      icon: UploadCloud,
      title: 'Upload or Paste Report',
      description:
        'Upload your lab report as a JPG, PNG image or PDF document (up to 5 MB), or paste the text directly into the workspace.',
    },
    {
      step: '02',
      icon: Cpu,
      title: 'AI & OCR Analysis',
      description:
        'Optical Character Recognition digitizes your laboratory values while Gemini analyzes reported measurements against standard reference ranges.',
    },
    {
      step: '03',
      icon: Stethoscope,
      title: 'Discuss with Your Doctor',
      description:
        'Review clear summaries, out-of-range indicators, and suggested questions to prepare for your next medical appointment.',
    },
  ];

  return (
    <section id="how-it-works" className="how-it-works-section">
      <div className="section-container">
        <div className="section-header">
          <span className="section-eyebrow">STEP-BY-STEP PROCESS</span>
          <h2 className="section-heading">How ReportSaathi Works</h2>
          <p className="section-subheading">
            Transform confusing lab results into understandable health insights in seconds.
          </p>
        </div>

        <div className="steps-grid">
          {steps.map((st, idx) => {
            const Icon = st.icon;
            return (
              <div key={idx} className="step-card">
                <div className="step-top-row">
                  <span className="step-number">{st.step}</span>
                  <div className="step-icon-wrapper">
                    <Icon size={22} strokeWidth={2.2} className="step-icon" />
                  </div>
                </div>
                <h3 className="step-title">{st.title}</h3>
                <p className="step-description">{st.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

