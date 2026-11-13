import React from 'react';
import { FileText, ArrowRight, CheckCircle2, ShieldCheck, Sparkles, Globe2, HelpCircle } from 'lucide-react';

/**
 * Modern SaaS Hero Section
 * Displays primary value proposition, CTAs, trust signals,
 * and an interactive visual preview of an explained medical lab report.
 */
export default function HeroSection({ onAnalyzeClick, onHowItWorksClick }) {
  return (
    <section id="home" className="hero-section">
      <div className="hero-container">
        {/* Left Column: Headlines & Actions */}
        <div className="hero-content">
          <div className="hero-badge">
            <Sparkles size={14} className="hero-badge-icon" />
            <span>AI-POWERED HEALTH LITERACY</span>
          </div>

          <h1 className="hero-headline">
            Understand Your Medical Reports. <span className="highlight-text">With Confidence.</span>
          </h1>

          <p className="hero-subtitle">
            Upload your laboratory report and receive clear, easy-to-understand explanations powered by AI. Know what your tests mean and what questions to discuss with your doctor.
          </p>

          <div className="hero-cta-group">
            <button
              type="button"
              className="hero-primary-btn"
              onClick={onAnalyzeClick}
            >
              <span>Analyze Your Report</span>
              <ArrowRight size={18} strokeWidth={2.2} />
            </button>

            <button
              type="button"
              className="hero-secondary-btn"
              onClick={onHowItWorksClick}
            >
              <span>How It Works</span>
            </button>
          </div>

          {/* Trust Highlights Checklist */}
          <div className="hero-trust-bar">
            <div className="trust-item">
              <CheckCircle2 size={16} className="trust-check-icon" />
              <span>Simple, Plain-Language Explanations</span>
            </div>
            <div className="trust-item">
              <Globe2 size={16} className="trust-check-icon" />
              <span>English, Hindi & Kannada</span>
            </div>
            <div className="trust-item">
              <ShieldCheck size={16} className="trust-check-icon" />
              <span>Privacy-First & In-Memory Processing</span>
            </div>
            <div className="trust-item">
              <HelpCircle size={16} className="trust-check-icon" />
              <span>Tailored Questions for Your Doctor</span>
            </div>
          </div>
        </div>

        {/* Right Column: Visual Preview of Sample Laboratory Report with Insight Cards */}
        <div className="hero-visual">
          <div className="sample-report-mockup">
            {/* Mockup Header */}
            <div className="mockup-header">
              <div className="mockup-brand">
                <FileText size={18} className="mockup-icon" />
                <span className="mockup-title">Sample Complete Blood Count (CBC)</span>
              </div>
              <span className="mockup-badge">Analyzed with AI</span>
            </div>

            {/* Overall AI Summary Callout */}
            <div className="mockup-summary-callout">
              <div className="summary-callout-badge">
                <Sparkles size={13} />
                <span>Executive Summary</span>
              </div>
              <p className="summary-callout-text">
                Your red blood cell count and platelets are in standard reference ranges. Hemoglobin is slightly below the reference threshold, which is helpful to mention during your next doctor consultation.
              </p>
            </div>

            {/* Test Cards Preview */}
            <div className="mockup-tests-list">
              {/* Test Item 1: Hemoglobin (Low) */}
              <div className="mockup-test-card test-card-attention">
                <div className="mockup-test-top">
                  <div>
                    <h4 className="mockup-test-name">Hemoglobin (Hb)</h4>
                    <span className="mockup-test-values">Reported: <strong>9.1 g/dL</strong> · Ref: 13.0 - 17.0 g/dL</span>
                  </div>
                  <span className="mockup-status-tag status-tag-low">
                    <span className="status-dot-blue" />
                    Low
                  </span>
                </div>
                <p className="mockup-test-meaning">
                  Below the standard reference range. Hemoglobin carries oxygen throughout your body; lower values are commonly discussed regarding iron levels or mild fatigue.
                </p>
              </div>

              {/* Test Item 2: Platelet Count (Normal) */}
              <div className="mockup-test-card test-card-normal">
                <div className="mockup-test-top">
                  <div>
                    <h4 className="mockup-test-name">Platelet Count</h4>
                    <span className="mockup-test-values">Reported: <strong>210,000 /mcL</strong> · Ref: 150,000 - 450,000 /mcL</span>
                  </div>
                  <span className="mockup-status-tag status-tag-normal">
                    <span className="status-dot-green" />
                    Normal
                  </span>
                </div>
                <p className="mockup-test-meaning">
                  Within the expected healthy reference range. Platelets assist in normal blood clotting.
                </p>
              </div>
            </div>

            {/* Mockup Doctor Questions Sneak Peek */}
            <div className="mockup-questions-peek">
              <span className="questions-peek-title">Questions to Ask Your Doctor:</span>
              <p className="questions-peek-item">"Could dietary iron or routine supplements help bring my hemoglobin into range?"</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

