import React from 'react';
import { BookOpenCheck, Globe, Shield, MessageSquareQuote } from 'lucide-react';

/**
 * Trust & Features section explaining core principles:
 * - Simple explanations
 * - Multiple language support
 * - Privacy-conscious in-memory processing
 * - Educational insights & doctor communication
 */
export default function TrustFeatures() {
  const features = [
    {
      icon: BookOpenCheck,
      title: 'Plain-Language Explanations',
      description:
        'Complex clinical values, abbreviations, and units are translated into everyday terminology you can understand without confusing jargon.',
    },
    {
      icon: Globe,
      title: 'Multilingual Accessibility',
      description:
        'Switch seamlessly between English, Hindi (हिंदी), and Kannada (ಕನ್ನಡ) so healthcare information is accessible to your entire family.',
    },
    {
      icon: Shield,
      title: 'Privacy-Conscious Architecture',
      description:
        'Documents and report texts are processed strictly in-memory during analysis. Your medical reports are never permanently stored or shared.',
    },
    {
      icon: MessageSquareQuote,
      title: 'Prepared Doctor Questions',
      description:
        'Receive personalized, non-diagnostic questions to help you have an informed, collaborative conversation with your healthcare provider.',
    },
  ];

  return (
    <section id="features" className="features-section">
      <div className="section-container">
        <div className="section-header">
          <span className="section-eyebrow">DESIGNED FOR HEALTH LITERACY</span>
          <h2 className="section-heading">Designed for Clarity, Built on Trust</h2>
          <p className="section-subheading">
            ReportSaathi is an educational bridge between laboratory reference data and patient understanding.
          </p>
        </div>

        <div className="features-grid">
          {features.map((feat, idx) => {
            const IconComponent = feat.icon;
            return (
              <div key={idx} className="feature-card">
                <div className="feature-icon-wrapper">
                  <IconComponent size={24} strokeWidth={2.2} className="feature-icon" />
                </div>
                <h3 className="feature-title">{feat.title}</h3>
                <p className="feature-description">{feat.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

