import React from 'react';
import { Activity, ShieldAlert, HeartHandshake } from 'lucide-react';

/**
 * Polished SaaS Footer
 * Contains branding, navigation, medical disclaimer, and privacy notice.
 */
export default function Footer() {
  const scrollTo = (id) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <footer id="about" className="footer-section">
      <div className="footer-container">
        {/* Top Footer Row */}
        <div className="footer-top-grid">
          {/* Brand Info */}
          <div className="footer-brand-col">
            <div className="footer-logo">
              <div className="brand-logo-icon" aria-hidden="true">
                <Activity size={20} strokeWidth={2.4} />
              </div>
              <span className="brand-title-main">Report<span className="brand-title-accent">Saathi</span></span>
            </div>
            <p className="footer-description">
              An educational health-literacy platform designed to help patients understand complex laboratory reports in plain language.
            </p>
            <div className="footer-tagline">
              <HeartHandshake size={16} className="footer-tagline-icon" />
              <span>Dedicated to accessible, patient-centered health literacy.</span>
            </div>
          </div>

          {/* Quick Navigation Links */}
          <div className="footer-links-col">
            <h4 className="footer-heading">Platform</h4>
            <ul className="footer-links-list">
              <li><button type="button" onClick={() => scrollTo('home')}>Home</button></li>
              <li><button type="button" onClick={() => scrollTo('workspace')}>Report Analysis</button></li>
              <li><button type="button" onClick={() => scrollTo('how-it-works')}>How It Works</button></li>
              <li><button type="button" onClick={() => scrollTo('features')}>Features</button></li>
            </ul>
          </div>

          {/* Privacy & Ethics */}
          <div className="footer-links-col">
            <h4 className="footer-heading">Privacy & Ethics</h4>
            <ul className="footer-links-list">
              <li><span>In-Memory Processing Only</span></li>
              <li><span>Zero Patient Data Storage</span></li>
              <li><span>No Third-Party Sharing</span></li>
              <li><span>Educational Guardrails</span></li>
            </ul>
          </div>
        </div>

        {/* Prominent Educational Disclaimer Box */}
        <div className="footer-disclaimer-box">
          <div className="disclaimer-header">
            <ShieldAlert size={18} className="disclaimer-alert-icon" />
            <h5 className="disclaimer-title">IMPORTANT MEDICAL DISCLAIMER</h5>
          </div>
          <p className="disclaimer-copy">
            ReportSaathi is strictly an informational and educational health-literacy assistant. It does <strong>not</strong> provide medical diagnoses, treatment plans, clinical assessments, or prescription medicine recommendations. Laboratory reference ranges can vary between different clinical laboratories. Always consult a licensed healthcare professional or physician to interpret your clinical laboratory results and discuss any symptoms or health conditions.
          </p>
        </div>

        {/* Bottom Copyright Row */}
        <div className="footer-bottom-row">
          <p className="footer-copyright">
            © {new Date().getFullYear()} ReportSaathi. Built for health literacy and patient empowerment.
          </p>
          <p className="footer-note">
            Educational tool · Not a diagnostic medical device
          </p>
        </div>
      </div>
    </footer>
  );
}

